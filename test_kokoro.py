from kokoro_onnx import Kokoro
import sounddevice as sd

print("Loading Kokoro...")
kokoro = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")
print("Kokoro ready!")

samples, rate = kokoro.create(
    "Hello, I am Hina.",
    voice="af_bella",
    speed=1.0,
    lang="en-us"
)

print("Generated samples")
sd.play(samples, rate)
sd.wait()
print("Voice works!")