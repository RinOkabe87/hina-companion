import sys
import math
import random
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal, QObject
from PyQt6.QtGui import (
    QPainter, QPixmap, QColor, QFont, QPen,
    QRadialGradient, QLinearGradient, QBrush, QPainterPath
)

class HinaSignals(QObject):
    speaking = pyqtSignal(bool)
    emotion_changed = pyqtSignal(str)
    thinking = pyqtSignal()
    listening = pyqtSignal()

signals = HinaSignals()

class HinaAvatar(QWidget):
    def __init__(self):
        super().__init__()

        # Window setup — frameless, always on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 600)

        # Position — right side of screen
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 420, screen.height() - 650)

        # Load Hina's face
        self.face_pixmap = QPixmap("D:\\hina\\hina_face.jpg")
        if self.face_pixmap.isNull():
            print("⚠️ hina_face.jpg not found")
        else:
            # Scale to fit nicely
            self.face_pixmap = self.face_pixmap.scaled(
                380, 500,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

        # Animation state
        self.blink_state = 0        # 0=open, 1=closing, 2=closed, 3=opening
        self.blink_progress = 0.0
        self.mouth_open = 0.0       # 0.0 to 1.0
        self.is_speaking = False
        self.is_thinking = False
        self.is_listening = False
        self.current_emotion = "neutral"
        self.glow_pulse = 0.0
        self.idle_sway = 0.0
        self.status_text = "Hina"
        self.mouth_anim = 0.0
        self.drag_pos = None

        # Timers
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self._update_animation)
        self.anim_timer.start(33)  # ~30fps

        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self._trigger_blink)
        self.blink_timer.start(random.randint(2000, 5000))

        # Connect signals
        signals.speaking.connect(self._on_speaking)
        signals.emotion_changed.connect(self._on_emotion)
        signals.thinking.connect(self._on_thinking)
        signals.listening.connect(self._on_listening)

        print("🌸 Hina's face is ready")

    def _update_animation(self):
        t = self.anim_timer.interval()

        # Idle sway
        import time
        self.idle_sway = math.sin(time.time() * 0.5) * 3

        # Glow pulse
        self.glow_pulse = (math.sin(time.time() * 1.5) + 1) / 2

        # Speaking mouth animation
        if self.is_speaking:
            import time
            self.mouth_anim = (math.sin(time.time() * 8) + 1) / 2
        else:
            self.mouth_anim = max(0.0, self.mouth_anim - 0.1)

        # Blink animation
        if self.blink_state == 1:
            self.blink_progress = min(1.0, self.blink_progress + 0.2)
            if self.blink_progress >= 1.0:
                self.blink_state = 2
                QTimer.singleShot(80, lambda: self._set_blink(3))
        elif self.blink_state == 3:
            self.blink_progress = max(0.0, self.blink_progress - 0.2)
            if self.blink_progress <= 0.0:
                self.blink_state = 0

        self.update()

    def _trigger_blink(self):
        if self.blink_state == 0:
            self.blink_state = 1
        # Random next blink
        self.blink_timer.setInterval(random.randint(2000, 6000))

    def _set_blink(self, state):
        self.blink_state = state

    def _on_speaking(self, speaking):
        self.is_speaking = speaking
        self.is_thinking = False
        self.is_listening = False
        self.status_text = "speaking..." if speaking else "Hina"

    def _on_thinking(self):
        self.is_thinking = True
        self.is_speaking = False
        self.is_listening = False
        self.status_text = "thinking..."

    def _on_listening(self):
        self.is_listening = True
        self.is_speaking = False
        self.is_thinking = False
        self.status_text = "listening..."

    def _on_emotion(self, emotion):
        self.current_emotion = emotion

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w, h = self.width(), self.height()

        # ── Background glow ──
        emotion_colors = {
            "neutral": QColor(120, 80, 200),
            "happy": QColor(200, 150, 80),
            "sad": QColor(80, 120, 200),
            "curious": QColor(80, 200, 180),
            "tired": QColor(100, 100, 150),
        }
        glow_color = emotion_colors.get(
            self.current_emotion,
            QColor(120, 80, 200)
        )
        glow_color.setAlpha(int(30 + self.glow_pulse * 20))

        grad = QRadialGradient(w//2, h//2, w//2)
        grad.setColorAt(0, glow_color)
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillRect(0, 0, w, h, QBrush(grad))

        # ── Draw face image ──
        if not self.face_pixmap.isNull():
            # Apply idle sway
            painter.save()
            painter.translate(w//2, h//2)
            painter.translate(self.idle_sway, 0)
            painter.translate(-self.face_pixmap.width()//2,
                             -self.face_pixmap.height()//2)
            painter.drawPixmap(0, 0, self.face_pixmap)
            painter.restore()

        # ── Blink overlay ──
        if self.blink_progress > 0:
            # Draw black rectangle over eye area
            eye_y = int(h * 0.28)
            eye_h = int(h * 0.08)
            blink_h = int(eye_h * self.blink_progress)
            painter.fillRect(
                50, eye_y,
                w - 100, blink_h,
                QColor(20, 15, 30, int(200 * self.blink_progress))
            )

        # ── Speaking mouth pulse ──
        if self.mouth_anim > 0.05:
            mouth_y = int(h * 0.58)
            mouth_x = int(w * 0.35)
            mouth_w = int(w * 0.30)
            mouth_h = int(15 * self.mouth_anim)

            painter.setBrush(QColor(220, 100, 120, int(180 * self.mouth_anim)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(mouth_x, mouth_y, mouth_w, mouth_h)

        # ── Status bar ──
        bar_h = 50
        bar_color = QColor(15, 10, 25, 200)
        painter.fillRect(0, h - bar_h, w, bar_h, bar_color)

        # Status text
        painter.setPen(QColor(200, 170, 255))
        font = QFont("Segoe UI", 11)
        painter.setFont(font)
        painter.drawText(0, h - bar_h, w, bar_h,
                        Qt.AlignmentFlag.AlignCenter,
                        self.status_text)

        # ── Listening pulse ring ──
        if self.is_listening:
            import time
            pulse = (math.sin(time.time() * 3) + 1) / 2
            pen = QPen(QColor(100, 200, 255, int(100 + pulse * 100)))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            margin = int(10 + pulse * 5)
            painter.drawRoundedRect(
                margin, margin,
                w - margin*2, h - margin*2 - bar_h,
                20, 20
            )

        # ── Thinking dots ──
        if self.is_thinking:
            import time
            for i in range(3):
                phase = (time.time() * 2 + i * 0.5) % 1.0
                dot_y = int(h * 0.85 + math.sin(phase * math.pi) * 5)
                dot_x = w//2 - 20 + i * 20
                alpha = int(100 + phase * 155)
                painter.setBrush(QColor(200, 170, 255, alpha))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(dot_x - 5, dot_y - 5, 10, 10)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self.drag_pos:
            self.move(event.globalPosition().toPoint() - self.drag_pos)

    def mouseReleaseEvent(self, event):
        self.drag_pos = None

    def mouseDoubleClickEvent(self, event):
        """Double click to hide/show"""
        if self.isVisible():
            self.hide()


def create_avatar_app():
    app = QApplication.instance() or QApplication(sys.argv)
    avatar = HinaAvatar()
    avatar.show()
    return app, avatar