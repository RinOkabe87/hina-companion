import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
from avatar_ui import set_status

# Whisper runs on CPU — fast enough for speech, avoids CUDA 12 conflict
device = "cpu"
compute = "int8"

print(f"Loading Whisper on {device}...")
whisper = WhisperModel("base", device=device, compute_type=compute)
print("✅ Listening ready!")

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.008
SILENCE_DURATION = 2.0

def listen():
    print("🎤 Listening...")
    set_status("Listening")
    chunk_size = int(SAMPLE_RATE * 0.1)
    audio_chunks = []
    silence_chunks = 0
    silence_limit = int(SILENCE_DURATION / 0.1)
    max_chunks = int(30 / 0.1)

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype=np.float32,
        blocksize=chunk_size
    )

    with stream:
        speech_started = False
        for _ in range(max_chunks):
            chunk, _ = stream.read(chunk_size)
            chunk_flat = chunk.flatten()
            volume = np.abs(chunk_flat).mean()
            if volume > SILENCE_THRESHOLD:
                speech_started = True
            if speech_started:
                audio_chunks.append(chunk_flat)
                if volume < SILENCE_THRESHOLD:
                    silence_chunks += 1
                else:
                    silence_chunks = 0
                if silence_chunks >= silence_limit:
                    break

    if not audio_chunks:
        return ""

    set_status("Transcribing")
    audio = np.concatenate(audio_chunks)
    segments, _ = whisper.transcribe(audio, beam_size=5, language="en")
    return " ".join([s.text for s in segments]).strip()