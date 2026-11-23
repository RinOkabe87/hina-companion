import sqlite3
import chromadb
import json
from datetime import datetime
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# ─────────────────────────────────────
# SQLITE — Fast profile storage
# ─────────────────────────────────────

PROJECT_DIR = Path(__file__).resolve().parent
DB_PATH = str(PROJECT_DIR / "hina_memory.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            summary TEXT,
            emotional_tone TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS message_search
        USING fts5(content)
    """)
    conn.commit()
    return conn


def save_message(role, content):
    """Persist each conversation turn locally and index it for later recall."""
    if role not in ("user", "assistant"):
        raise ValueError(f"Unsupported message role: {role}")

    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO messages (role, content, created_at) VALUES (?, ?, ?)",
            (role, content, datetime.now().isoformat())
        )
        conn.execute(
            "INSERT INTO message_search (rowid, content) VALUES (?, ?)",
            (cursor.lastrowid, content)
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_messages(limit=20):
    """Return recent saved messages in conversation order."""
    conn = get_db()
    try:
        results = conn.execute("""
            SELECT role, content FROM (
                SELECT id, role, content
                FROM messages
                ORDER BY id DESC
                LIMIT ?
            )
            ORDER BY id
        """, (limit,)).fetchall()
        return [{"role": role, "content": content} for role, content in results]
    finally:
        conn.close()


def search_messages(query, limit=3):
    """Find older transcript messages related to the current conversation."""
    terms = re.findall(r"\w+", query.lower())
    if not terms:
        return []

    match_query = " OR ".join(f'"{term}"' for term in dict.fromkeys(terms))
    conn = get_db()
    try:
        results = conn.execute("""
            SELECT messages.role, messages.content
            FROM message_search
            JOIN messages ON messages.id = message_search.rowid
            WHERE message_search MATCH ?
              AND messages.id < (SELECT MAX(id) FROM messages)
            ORDER BY bm25(message_search), messages.id DESC
            LIMIT ?
        """, (match_query, limit)).fetchall()
        return [{"role": role, "content": content} for role, content in results]
    finally:
        conn.close()


def save_profile(key, value):
    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO profile (key, value, updated_at)
        VALUES (?, ?, ?)
    """, (key, str(value), datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_profile(key):
    conn = get_db()
    result = conn.execute(
        "SELECT value FROM profile WHERE key = ?", (key,)
    ).fetchone()
    conn.close()
    return result[0] if result else None

def get_all_profile():
    conn = get_db()
    results = conn.execute("SELECT key, value FROM profile").fetchall()
    conn.close()
    return {row[0]: row[1] for row in results}

def save_conversation_summary(summary, emotional_tone="neutral"):
    conn = get_db()
    conn.execute("""
        INSERT INTO conversations (date, summary, emotional_tone, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        datetime.now().strftime("%B %d, %Y"),
        summary,
        emotional_tone,
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()

def get_recent_conversations(limit=3):
    conn = get_db()
    results = conn.execute("""
        SELECT date, summary, emotional_tone 
        FROM conversations 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return results

def is_first_meeting():
    conn = get_db()
    try:
        profile_count = conn.execute("SELECT COUNT(*) FROM profile").fetchone()[0]
        message_count = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE role = 'user'"
        ).fetchone()[0]
        conversation_count = conn.execute(
            "SELECT COUNT(*) FROM conversations"
        ).fetchone()[0]
        return profile_count == 0 and message_count == 0 and conversation_count == 0
    finally:
        conn.close()

# ─────────────────────────────────────
# CHROMADB — Deep semantic memory
# ─────────────────────────────────────

chroma_client = chromadb.PersistentClient(
    path=str(PROJECT_DIR / "hina_chroma")
)

memory_collection = chroma_client.get_or_create_collection(
    name="hina_memories",
    metadata={"hnsw:space": "cosine"}
)

def save_deep_memory(content, memory_type="general", emotion="neutral"):
    """Save a meaningful memory that can be searched semantically"""
    memory_id = f"mem_{datetime.now().timestamp()}"
    memory_collection.add(
        documents=[content],
        metadatas=[{
            "type": memory_type,
            "emotion": emotion,
            "date": datetime.now().strftime("%B %d, %Y"),
            "timestamp": datetime.now().isoformat()
        }],
        ids=[memory_id]
    )

def search_memories(query, limit=3):
    """Find memories related to current conversation"""
    try:
        count = memory_collection.count()
        if count == 0:
            return []
        results = memory_collection.query(
            query_texts=[query],
            n_results=min(limit, count)
        )
        if results and results['documents']:
            return results['documents'][0]
        return []
    except Exception:
        logger.exception("Could not search Hina's semantic memories")
        return []

def get_memories_summary():
    """Build full context for Hina's brain"""
    profile = get_all_profile()
    recent_convs = get_recent_conversations(3)
    summary = ""

    if profile:
        summary += "What I know about this person:\n"
        for key, value in profile.items():
            summary += f"  - {key}: {value}\n"
        summary += "\n"

    if recent_convs:
        summary += "Recent conversations:\n"
        for date, conv_summary, tone in recent_convs:
            summary += f"  - {date} ({tone}): {conv_summary}\n"
        summary += "\n"

    if summary:
        return summary
    return (
        "This is our first conversation."
        if is_first_meeting()
        else "We have spoken before. Search the saved conversation history for details."
    )