from pydub import AudioSegment

print("Preparing Hina's voice...")

audio = AudioSegment.from_mp3("hina_voice.mp3")
audio = audio.set_frame_rate(22050)
audio = audio.set_channels(1)

if len(audio) > 60000:
    audio = audio[:60000]

audio.export("hina_voice.wav", format="wav")
print(f"✅ Done! Duration: {len(audio)/1000:.1f} seconds")