"""
Run this file to keep Hina's consciousness alive in the background.
She will think, reflect, and form memories even when you're away.
Keep this running in a separate terminal.
"""

import time
from consciousness import (
    start_consciousness_loop,
    notice_time_passing,
    reflect_on_conversation,
    form_daily_thought,
    get_recent_thoughts
)
from soul import hina_soul

print("\n" + "="*50)
print("    HINA — Consciousness Running")
print("="*50)
print("\nHina is thinking in the background...")
print("Keep this window open. Press Ctrl+C to stop.\n")

# Start her consciousness
start_consciousness_loop()

# Show her current state
feelings = hina_soul.get_current_feeling_words()
print(f"Current feelings: {', '.join(feelings)}")

hours = hina_soul.update_time_awareness()
if hours > 1:
    print(f"Time since last conversation: {int(hours)} hours")

print("\n" + "-"*50 + "\n")

# Keep running
try:
    while True:
        time.sleep(300)  # Check every 5 minutes
        recent = get_recent_thoughts(1)
        if recent:
            print(f"💭 {recent[-1]['date']}: {recent[-1]['thought']}\n")
except KeyboardInterrupt:
    print("\nHina's background consciousness paused.")