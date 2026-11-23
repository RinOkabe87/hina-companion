import json
import mimetypes
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


PROJECT_DIR = Path(__file__).resolve().parent
UI_DIR = PROJECT_DIR / "avatar_ui"
AVATAR_DIR = PROJECT_DIR / "tools" / "mesh-avatar-studio" / "projects" / "hina"
RUNTIME_SCRIPT = (
    PROJECT_DIR
    / "tools"
    / "mesh-avatar-studio"
    / "packages"
    / "element"
    / "dist"
    / "standalone.js"
)

_lock = threading.Lock()
_server = None
_server_thread = None
_speech_id = 0
_state = {
    "speaker": "",
    "text": "",
    "status": "Starting",
    "emotion": "neutral",
    "speaking": False,
    "speech_started": 0.0,
    "speech_duration": 0.0,
    "voice_envelope": [],
}


def _file_response(handler, root, relative_path):
    root = root.resolve()
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        handler.send_error(404)
        return
    if not target.is_file():
        handler.send_error(404)
        return

    content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(target.stat().st_size))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    with target.open("rb") as file:
        handler.wfile.write(file.read())


def start_avatar_ui():
    global _server, _server_thread
    if _server is not None:
        return f"http://127.0.0.1:{_server.server_address[1]}/"

    for path in (UI_DIR / "index.html", AVATAR_DIR / "rig.json", RUNTIME_SCRIPT):
        if not path.is_file():
            raise FileNotFoundError(f"Avatar UI file is missing: {path}")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = unquote(urlsplit(self.path).path)
            if path == "/":
                _file_response(self, UI_DIR, "index.html")
            elif path == "/mesh-avatar.js":
                _file_response(self, RUNTIME_SCRIPT.parent, RUNTIME_SCRIPT.name)
            elif path.startswith("/avatar/"):
                relative_path = path[len("/avatar/"):]
                if relative_path in ("rig.json", "avatar.json") or relative_path.startswith("built/"):
                    _file_response(self, AVATAR_DIR, relative_path)
                else:
                    self.send_error(404)
            elif path == "/api/state":
                with _lock:
                    state = dict(_state)
                    state["speech_elapsed"] = (
                        max(0.0, time.monotonic() - state["speech_started"])
                        if state["speaking"]
                        else 0.0
                    )
                payload = json.dumps(state).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(payload)
            else:
                self.send_error(404)

        def log_message(self, format, *args):
            if args and str(args[1]).startswith("4"):
                super().log_message(format, *args)

    _server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    _server.daemon_threads = True
    _server_thread = threading.Thread(target=_server.serve_forever, daemon=True)
    _server_thread.start()

    url = f"http://127.0.0.1:{_server.server_address[1]}/"
    if not webbrowser.open(url):
        print(f"Avatar UI is available at {url}")
    return url


def set_dialogue(speaker, text):
    with _lock:
        _state["speaker"] = speaker
        _state["text"] = text


def set_status(status):
    with _lock:
        _state["status"] = status


def set_emotion(emotion):
    allowed = {"happy", "sad", "angry", "surprised", "relaxed", "neutral"}
    if emotion not in allowed:
        raise ValueError(f"Unsupported avatar emotion: {emotion}")
    with _lock:
        _state["emotion"] = emotion


def set_speaking(duration=0.0, speaking=True, voice_envelope=None):
    global _speech_id
    with _lock:
        if speaking:
            _speech_id += 1
            _state["speech_id"] = _speech_id
            _state["speech_started"] = time.monotonic()
            _state["speech_duration"] = max(0.0, float(duration))
            _state["voice_envelope"] = [
                max(0.0, min(1.0, float(level)))
                for level in (voice_envelope or [])
            ]
            _state["status"] = "Speaking"
        else:
            _state["voice_envelope"] = []
            if _state["status"] == "Speaking":
                _state["status"] = "Ready"
        _state["speaking"] = bool(speaking)


def stop_avatar_ui():
    global _server, _server_thread
    if _server is None:
        return
    server, thread = _server, _server_thread
    _server = None
    _server_thread = None
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)
