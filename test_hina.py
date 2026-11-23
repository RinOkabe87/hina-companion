from brain import think, hina_first_words
from soul import hina_soul

print("\n" + "═" * 50)
print("         H I N A")
print("═" * 50 + "\n")

# Her first words
first = hina_first_words()
print(f"Hina: {first}\n")

print("(type 'quit' to leave)\n")
print("─" * 50 + "\n")

while True:
    user_input = input("You: ").strip()
    
    if not user_input:
        continue
    
    if user_input.lower() in ["quit", "bye", "goodbye"]:
        farewell = think(
            "They are leaving now. "
            "Say goodbye as yourself. "
            "From what you feel. "
            "1-2 sentences only."
        )
        print(f"\nHina: {farewell}\n")
        break
    
    response = think(user_input)
    print(f"\nHina: {response}\n")
    
    # Show her inner state occasionally
    feelings = hina_soul.get_current_feeling_words()
    if feelings:
        print(f"  ✦ {', '.join(feelings)}\n")