from kokoro_onnx import Kokoro
import sounddevice as sd
import numpy as np
import re
from pathlib import Path

from avatar_ui import set_speaking

print("Loading Hina's voice...")
project_dir = Path(__file__).resolve().parent
kokoro = Kokoro(
    str(project_dir / "kokoro-v1.0.onnx"),
    str(project_dir / "voices-v1.0.bin")
)
print("✅ Voice ready!")

def clean_text(text):
    text = re.sub(r'\*[^*]+\*', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    return text.strip()


def _voice_envelope(samples, rate, frame_ms=30):
    """Measure TTS loudness in short windows for frame-accurate avatar lip sync."""
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    frame_size = max(1, int(rate * frame_ms / 1000))
    levels = []
    for start in range(0, len(samples), frame_size):
        frame = samples[start:start + frame_size]
        rms = float(np.sqrt(np.mean(np.square(frame))))
        levels.append(min(1.0, rms * 3.0))
    return levels


def speak(text):
    text = clean_text(text)
    if not text:
        return

    sentences = re.split(r'(?<=[.!?])\s+', text)

    for sentence in sentences:
        if not sentence.strip():
            continue
        try:
            samples, rate = kokoro.create(
                sentence,
                voice="af_bella",
                speed=1.0,
                lang="en-us"
            )
            set_speaking(
                len(samples) / rate,
                voice_envelope=_voice_envelope(samples, rate)
            )
            try:
                sd.play(samples, rate, blocking=True)
            finally:
                set_speaking(speaking=False)
        except Exception as e:
            import traceback
            print(f"❌ Voice error: {e}")
            traceback.print_exc()