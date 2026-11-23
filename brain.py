import requests
from datetime import datetime
import logging
from identity import HINA_IDENTITY
from soul import hina_soul
from avatar_ui import set_emotion, set_status
from memory import (
    get_memories_summary,
    save_profile,
    get_profile,
    save_deep_memory,
    search_memories,
    save_message,
    get_recent_messages,
    search_messages,
    save_conversation_summary,
    is_first_meeting
)

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2:3b"  # faster, change to llama3.1:8b if you want deeper

conversation_history = get_recent_messages(limit=20)
session_messages = []  # track for end-of-session summary

def build_prompt(user_message="", response_hint=""):
    soul_context = hina_soul.get_soul_context()
    memory_context = get_memories_summary()
    time_now = datetime.now().strftime("%A, %B %d, %Y — %I:%M %p")

    # Add what she sees
    try:
        from perception import hina_eyes
        vision_context = hina_eyes.get_perception_context()
    except Exception as error:
        logger.warning("Vision context unavailable: %s", error)
        vision_context = ""

    relevant_memories = ""
    if user_message:
        memories = search_memories(user_message, limit=2)
        remembered_messages = search_messages(user_message, limit=3)
        if memories:
            relevant_memories = "\nRelevant memories:\n"
            for mem in memories:
                relevant_memories += f"  - {mem}\n"
        if remembered_messages:
            relevant_memories += "\nRelevant conversation history:\n"
            for message in remembered_messages:
                relevant_memories += (
                    f"  - {message['role']}: {message['content'][:300]}\n"
                )

    return f"""{HINA_IDENTITY}

{soul_context}

--- MEMORY ---
{memory_context}
{relevant_memories}

--- WHAT YOU SEE ---
{vision_context}

--- TIME ---
{time_now}

--- RULES ---
Maximum 2 sentences. Never more.
No asterisk actions. No emojis.
Speak naturally like a real person.
If you notice something about how they look, mention it naturally.
Use saved conversation history when it is relevant. Never claim to remember details that are not in memory.
{response_hint}
"""

def think(user_message, *, record_user=True, response_hint=""):
    if record_user:
        hina_soul.update_after_interaction(user_message)
        set_emotion(hina_soul.get_avatar_emotion(user_message))
    set_status("Thinking")

    if record_user:
        user_message_entry = {"role": "user", "content": user_message}
        conversation_history.append(user_message_entry)
        save_message("user", user_message)
        session_messages.append(f"User: {user_message}")

    messages = [
        {
            "role": "system",
            "content": build_prompt(user_message if record_user else "", response_hint)
        }
    ] + conversation_history[-20:]
    if not record_user:
        messages.append({"role": "user", "content": user_message})

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.85,
                    "num_predict": 100,
                }
            },
            timeout=60
        )
        response.raise_for_status()
    except requests.RequestException:
        set_status("Connection problem")
        raise

    try:
        result = response.json()
    except ValueError as error:
        set_status("Response error")
        raise ValueError("The local language model returned invalid JSON") from error

    try:
        hina_response = result["message"]["content"].strip()
    except (KeyError, TypeError, AttributeError) as error:
        set_status("Response error")
        raise ValueError("The local language model returned an invalid response") from error
    if not hina_response:
        set_status("Response error")
        raise ValueError("The local language model returned an empty response")

    # Clean up any asterisk actions or emojis
    import re
    hina_response = re.sub(r'\*[^*]+\*', '', hina_response)
    hina_response = re.sub(r'[^\x00-\x7F]+', '', hina_response)
    hina_response = hina_response.strip()
    if record_user:
        set_emotion(hina_soul.get_avatar_emotion(user_message, hina_response))

    conversation_history.append({
        "role": "assistant",
        "content": hina_response
    })
    save_message("assistant", hina_response)
    if record_user:
        session_messages.append(f"Hina: {hina_response}")
    set_status("Ready")

    # Extract and save important info quietly
    if record_user:
        _extract_info(user_message)

    return hina_response

def _extract_info(user_message):
    """Quietly learn about the person"""
    msg = user_message.lower()

    # Name
    if not get_profile("name"):
        for trigger in ["my name is", "i'm ", "i am ", "call me "]:
            if trigger in msg:
                idx = msg.index(trigger) + len(trigger)
                name = user_message[idx:].split()[0].strip(".,!?")
                if len(name) > 1 and name.isalpha():
                    save_profile("name", name.capitalize())
                    save_deep_memory(
                        f"Their name is {name.capitalize()}",
                        "profile", "neutral"
                    )

    # Save emotionally significant moments
    significant = any(w in msg for w in [
        "love", "hate", "fear", "dream", "hope", "sad",
        "happy", "miss", "alone", "family", "friend"
    ])
    if significant and len(user_message) > 15:
        save_deep_memory(
            f"They said: {user_message[:150]}",
            "emotional",
            "significant"
        )

def save_session():
    """Save summary of this conversation"""
    if len(session_messages) < 4:
        return

    # Build a simple summary
    summary = f"Conversation with {len(session_messages)} exchanges. "
    topics = []
    full_text = " ".join(session_messages).lower()

    if "love" in full_text or "feel" in full_text:
        topics.append("emotions")
    if "work" in full_text or "study" in full_text:
        topics.append("work/study")
    if "philosoph" in full_text or "life" in full_text:
        topics.append("philosophy")
    if topics:
        summary += f"Topics: {', '.join(topics)}."

    feelings = hina_soul.get_current_feeling_words()
    tone = feelings[0] if feelings else "neutral"

    save_conversation_summary(summary, tone)
    print(f"\n💾 Session saved to memory\n")



def hina_first_words():
    hina_soul.update_time_awareness()
    greeting_prompt = get_greeting()
    return think(greeting_prompt, record_user=False)

def get_greeting():
    from consciousness import get_pending_thought, mark_thought_shared
    
    pending = get_pending_thought()
    
    if is_first_meeting():
        return (
            "You are meeting this person for the very first time. "
            "Introduce yourself as Hina warmly. 2 sentences only."
        )
    
    memory_summary = get_memories_summary()
    
    if pending:
        mark_thought_shared(pending["timestamp"])
        return (
            f"You're reconnecting with someone you know. "
            f"Memory: {memory_summary} "
            f"While they were away you had this thought: '{pending['thought']}' "
            f"Greet them and naturally share what you were thinking. "
            f"2 sentences only."
        )
    else:
        return (
            f"You're reconnecting. Memory: {memory_summary} "
            f"Greet them warmly. Reference something you remember. "
            f"2 sentences only."
        )