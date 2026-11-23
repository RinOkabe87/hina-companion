from brain import think, hina_first_words
from voice import speak
from listen import listen

print("\n" + "="*40)
print("         H I N A")
print("="*40 + "\n")

# Her first words in her real voice
first = hina_first_words()
print(f"Hina: {first}")
speak(first)

print("\n(say 'goodbye' to stop)\n")

while True:
    user_text = listen()

    if not user_text or len(user_text.strip()) < 2:
        print("(didn't catch that)\n")
        continue

    print(f"You: {user_text}")

    if any(w in user_text.lower() for w in ["goodbye", "bye", "goodnight"]):
        farewell = think("Say a warm goodbye. 1 sentence only.")
        print(f"\nHina: {farewell}")
        speak(farewell)
        break

    response = think(user_text)
    print(f"\nHina: {response}\n")
    speak(response)