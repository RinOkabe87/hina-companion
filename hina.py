"""
Hina - main entry point.

Run the voice conversation directly in the console.
"""

import re
import traceback

from avatar_ui import set_dialogue, start_avatar_ui, stop_avatar_ui
from brain import think, hina_first_words, save_session
from voice import speak
from listen import listen
from soul import hina_soul
from consciousness import start_consciousness_loop, stop_consciousness_loop

_saved = False

GOODBYE_PATTERN = re.compile(r"\b(goodbye|bye|goodnight|good night)\b", re.IGNORECASE)

MAX_CONSECUTIVE_ERRORS = 5


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def save_once():
    """Save the session exactly once, even if called from several places."""
    global _saved
    if _saved:
        return
    _saved = True
    try:
        print("Saving memory...")
        save_session()
    except Exception:
        print("❌ Could not save session:")
        traceback.print_exc()


def start_vision():
    try:
        from perception import hina_eyes
        hina_eyes.start()
        print("👁️ Hina can see you\n")
    except Exception as e:
        print(f"(Vision unavailable: {e})\n")


def stop_vision():
    try:
        from perception import hina_eyes
        if hasattr(hina_eyes, "stop"):
            hina_eyes.stop()
    except Exception as error:
        print(f"(Vision shutdown warning: {error})")


def shutdown():
    """Save memory and release vision resources when Hina exits."""
    save_once()
    stop_consciousness_loop()
    stop_vision()
    stop_avatar_ui()
    print("Hina is sleeping...")


# --------------------------------------------------------------------------
# Conversation loop
# --------------------------------------------------------------------------

def run():
    try:
        start_avatar_ui()
    except OSError as e:
        print(f"(Avatar UI unavailable: {e})")

    start_vision()

    print("\n" + "=" * 50)
    print("           H I N A")
    print("=" * 50 + "\n")

    first = hina_first_words()
    set_dialogue("Hina", first)
    print(f"Hina: {first}\n")
    speak(first)

    print("(say 'goodbye' to stop)\n")
    print("-" * 50 + "\n")

    errors_in_a_row = 0
    consciousness_started = False

    while True:
        try:
            user_text = listen()

            if not user_text or len(user_text.strip()) < 2:
                print("(didn't catch that)\n")
                continue

            print(f"You: {user_text}")
            set_dialogue("You", user_text)

            if GOODBYE_PATTERN.search(user_text):
                farewell = think(
                    user_text,
                    response_hint="They are leaving; say a warm, brief goodbye."
                )
                set_dialogue("Hina", farewell)
                print(f"\nHina: {farewell}\n")
                speak(farewell)
                save_once()
                break

            response = think(user_text)

            set_dialogue("Hina", response)
            print(f"\nHina: {response}\n")
            speak(response)
            if not consciousness_started:
                start_consciousness_loop()
                consciousness_started = True

            feelings = hina_soul.get_current_feeling_words()
            if feelings:
                print(f"  ✦ {', '.join(feelings)}\n")

            errors_in_a_row = 0

        except Exception:
            # One bad turn should not kill the whole conversation.
            errors_in_a_row += 1
            print(f"❌ Error during conversation turn ({errors_in_a_row}/{MAX_CONSECUTIVE_ERRORS}):")
            traceback.print_exc()
            if errors_in_a_row >= MAX_CONSECUTIVE_ERRORS:
                print("Too many errors in a row, stopping.")
                break


def main():
    try:
        run()
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        shutdown()


if __name__ == "__main__":
    main()