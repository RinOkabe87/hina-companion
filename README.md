# Hina

Hina is a local voice companion built with Python, Ollama, Kokoro ONNX, and
Whisper. Conversation text and companion state are stored locally. The current
avatar UI uses the Mesh Avatar Studio image-based rig; it is not a full 3D VRM
avatar.

## Features

- Local LLM responses through Ollama.
- Microphone input transcribed locally with Faster-Whisper.
- Kokoro ONNX speech output with live speaking and emotion state in the avatar UI.
- SQLite transcript/profile storage and Chroma semantic memory.
- Optional local webcam perception.

## Requirements

- Windows 10 or later.
- Python 3.11.
- Node.js and npm for building the avatar runtime.
- Ollama with the `llama3.2:3b` model.
- A microphone and speakers for voice interaction; a webcam is optional.

## Setup

Clone this repository with its avatar-runtime submodule:

```powershell
git clone --recurse-submodules https://github.com/<your-account>/hina-companion.git
Set-Location hina-companion
```

Create the Python environment and install the pinned dependencies:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Install Ollama, start it, and download the configured model:

```powershell
ollama pull llama3.2:3b
```

Download the Kokoro ONNX model and voice pack from their official distribution
and place them in the repository root as `kokoro-v1.0.onnx` and
`voices-v1.0.bin`. These large model files are intentionally not stored in Git.

Build the avatar runtime:

```powershell
Push-Location tools\mesh-avatar-studio
npm ci
npm run build:element
Pop-Location
```

The private Hina avatar project (source image and generated image assets) is
intentionally excluded. To restore the avatar locally, place that project at
`tools\mesh-avatar-studio\projects\hina`. The voice conversation can still run
without those private avatar assets; the avatar UI will report that its assets
are unavailable.

## Run

Ensure Ollama is running, activate the virtual environment, then launch:

```powershell
.\run_hina.ps1
```

The launcher uses `.venv` when present and falls back to `venv` for existing
local installations. Hina opens the avatar UI in a browser and uses the
microphone. Say "goodbye" to end the conversation.

## Tests

Run the focused companion tests with:

```powershell
.\.venv\Scripts\python.exe -m unittest test_companion -v
```

## Local data and privacy

Conversation transcripts, semantic memories, evolving companion state, model
caches, and downloaded weights remain on the local machine and are ignored by
Git. Microphone audio is processed for transcription and is not saved by the
companion. Camera frames are processed locally and are not saved.

The avatar runtime is included as a Git submodule from
[Mesh Avatar Studio](https://github.com/shinshin86/mesh-avatar-studio).
