import cv2
import logging
import numpy as np
from datetime import datetime
import threading
import time

logger = logging.getLogger(__name__)

# MediaPipe new API
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class HinaPerception:
    def __init__(self):
        self.cap = None
        self.is_running = False
        self.current_emotion = "neutral"
        self.face_present = False
        self.smile_detected = False
        self.tiredness_level = 0.0
        self.last_observation = "present"
        self._thread = None

        # Use basic OpenCV face detection instead
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.smile_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_smile.xml'
        )

        print("👁️ Hina's eyes ready")

    def start(self):
        if self.is_running:
            return
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            cap.release()
            raise RuntimeError("Camera device 0 could not be opened")
        self.cap = cap
        self.is_running = True
        self._thread = threading.Thread(
            target=self._perception_loop,
            args=(cap,),
            daemon=True
        )
        self._thread.start()

    def stop(self):
        self.is_running = False
        cap, self.cap = self.cap, None
        if cap is not None:
            cap.release()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=2)

    def _perception_loop(self, cap):
        while self.is_running:
            try:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(
                    gray, 1.1, 4
                )

                if len(faces) > 0:
                    self.face_present = True
                    x, y, w, h = faces[0]
                    face_gray = gray[y:y+h, x:x+w]

                    # Smile detection
                    smiles = self.smile_cascade.detectMultiScale(
                        face_gray, 1.8, 20
                    )
                    self.smile_detected = len(smiles) > 0

                    if self.smile_detected:
                        self.current_emotion = "happy"
                    else:
                        self.current_emotion = "neutral"
                else:
                    self.face_present = False
                    self.current_emotion = "absent"

                self._update_observation()
                time.sleep(0.3)

            except Exception:
                logger.exception("Hina's camera perception stopped after an error")
                self.is_running = False
                self.cap = None
                cap.release()
                break

    def _update_observation(self):
        if not self.face_present:
            self.last_observation = "stepped away"
            return
        if self.current_emotion == "happy":
            self.last_observation = "smiling"
        else:
            self.last_observation = "present and calm"

    def get_perception_context(self):
        if not self.face_present:
            return "The person stepped away from the camera."
        context = f"I can see them — they look {self.last_observation}."
        if self.current_emotion == "happy":
            context += " Seeing them smile makes me feel warm."
        return context

    def get_emotion(self):
        return self.current_emotion

    def is_person_present(self):
        return self.face_present

hina_eyes = HinaPerception()