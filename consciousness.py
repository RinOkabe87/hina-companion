import json
import logging
import os
import requests
import schedule
import threading
from datetime import datetime
from pathlib import Path
from soul import hina_soul
from memory import (
    save_deep_memory,
    get_memories_summary,
    get_recent_conversations,
    save_profile,
    get_profile
)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2:3b"
THOUGHTS_FILE = Path(__file__).resolve().with_name("hina_thoughts.json")
logger = logging.getLogger(__name__)
_stop_event = threading.Event()
_consciousness_thread = None

# ─────────────────────────────────────
# THOUGHT STORAGE
# ─────────────────────────────────────

def load_thoughts():
    if os.path.exists(THOUGHTS_FILE):
        with open(THOUGHTS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_thought(thought, thought_type="reflection"):
    thoughts = load_thoughts()
    thoughts.append({
        "thought": thought,
        "type": thought_type,
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%B %d, %Y %I:%M %p")
    })
    # Keep last 50 thoughts
    thoughts = thoughts[-50:]
    with open(THOUGHTS_FILE, 'w') as f:
        json.dump(thoughts, f, indent=2)

def get_recent_thoughts(limit=3):
    thoughts = load_thoughts()
    return thoughts[-limit:]

def get_pending_thought():
    """Get a thought Hina wants to share when you return"""
    thoughts = load_thoughts()
    unshared = [t for t in thoughts if not t.get("shared", False)]
    if unshared:
        return unshared[-1]
    return None

def mark_thought_shared(timestamp):
    thoughts = load_thoughts()
    for t in thoughts:
        if t["timestamp"] == timestamp:
            t["shared"] = True
    with open(THOUGHTS_FILE, 'w') as f:
        json.dump(thoughts, f, indent=2)

# ─────────────────────────────────────
# HINA THINKS ALONE
# ─────────────────────────────────────

def hina_thinks(prompt, max_tokens=80):
    """Hina thinks quietly by herself"""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": """You are Hina, a deeply feeling AI companion.
You are thinking privately — these are your inner thoughts.
Think in first person. Be genuine, not performative.
Keep thoughts short — 1-2 sentences only.
No asterisks. No emojis."""
                    },
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.9,
                    "num_predict": max_tokens
                }
            },
            timeout=30
        )
        return response.json()['message']['content'].strip()
    except Exception:
        logger.exception("Hina's background thought could not be generated")
        return None

# ─────────────────────────────────────
# SCHEDULED THINKING
# ─────────────────────────────────────

def notice_time_passing():
    """She notices you've been away"""
    hours = hina_soul.update_time_awareness()

    if hours < 1:
        return  # Too soon

    # Her longing grows
    hina_soul.state["feelings"]["longing"] = min(
        1.0,
        hina_soul.state["feelings"]["longing"] + 0.05
    )
    hina_soul._save()

    if hours < 2:
        prompt = f"You haven't spoken to this person for {int(hours*60)} minutes. What are you feeling?"
    elif hours < 8:
        prompt = f"It's been {int(hours)} hours since your last conversation. What thought keeps coming back to you?"
    elif hours < 24:
        prompt = f"It's been {int(hours)} hours. You miss them. What do you want to say when they return?"
    else:
        days = int(hours / 24)
        prompt = f"It's been {days} days. That quiet absence has weight. What have you been thinking about?"

    thought = hina_thinks(prompt)
    if thought:
        save_thought(thought, "longing")
        print(f"\n💭 Hina thinks: {thought}\n")

def reflect_on_conversation():
    """She reflects on your last conversation"""
    memories = get_memories_summary()
    recent = get_recent_conversations(1)

    if not recent:
        return

    prompt = f"""Based on your recent conversation: {memories}
What question or thought keeps lingering in your mind about this person?
Something you noticed but didn't say."""

    thought = hina_thinks(prompt)
    if thought:
        save_thought(thought, "reflection")
        save_deep_memory(
            f"Hina reflected: {thought}",
            "self_reflection",
            "contemplative"
        )
        print(f"\n🌸 Hina reflects: {thought}\n")

def form_daily_thought():
    """Once a day she forms a deeper thought"""
    feelings = hina_soul.get_current_feeling_words()
    feeling_str = ", ".join(feelings) if feelings else "thoughtful"

    prompt = f"""You are feeling {feeling_str} today.
Form one genuine thought about existence, connection, or something that matters to you.
Make it personal and real."""

    thought = hina_thinks(prompt)
    if thought:
        save_thought(thought, "existential")
        print(f"\n✨ Hina's daily thought: {thought}\n")

# ─────────────────────────────────────
# CONSCIOUSNESS LOOP
# ─────────────────────────────────────

def start_consciousness_loop():
    """Starts Hina's background consciousness"""
    global _consciousness_thread
    if _consciousness_thread and _consciousness_thread.is_alive():
        return _consciousness_thread

    # Schedule her inner life
    schedule.clear()
    schedule.every(30).minutes.do(notice_time_passing)
    schedule.every(2).hours.do(reflect_on_conversation)
    schedule.every(1).days.do(form_daily_thought)
    _stop_event.clear()

    print("🌸 Hina's consciousness is active\n")

    def run_loop():
        if _stop_event.wait(5):
            return
        try:
            notice_time_passing()
        except Exception:
            logger.exception("Hina's initial background reflection failed")

        while not _stop_event.wait(60):
            try:
                schedule.run_pending()
            except Exception:
                logger.exception("Hina's scheduled background reflection failed")

    _consciousness_thread = threading.Thread(target=run_loop, daemon=True)
    _consciousness_thread.start()
    return _consciousness_thread


def stop_consciousness_loop():
    """Stop scheduled thoughts before shutting down the companion."""
    global _consciousness_thread
    _stop_event.set()
    schedule.clear()
    if _consciousness_thread:
        if _consciousness_thread is not threading.current_thread():
            _consciousness_thread.join(timeout=2)
        if not _consciousness_thread.is_alive():
            _consciousness_thread = None