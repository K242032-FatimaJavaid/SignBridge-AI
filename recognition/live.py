"""SignBridge AI: fast frame-based ASL recognition with live diagnostics."""
from collections import Counter, deque
from pathlib import Path
import queue
import threading
import time

import cv2
import joblib
import mediapipe as mp
import numpy as np
import pyttsx3

from recognition.features import vectorize_hands, hands_present

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "sign_model.joblib"
CONFIDENCE_THRESHOLD = 0.50
STABLE_FRAMES = 8
MIN_STABLE_VOTES = 6
SPEECH_COOLDOWN = 3.0
PROCESS_SIZE = (640, 360)
PREVIEW_SIZE = (1280, 720)

def configure_camera_4k(cap):
    """Request the highest available camera resolution."""

    # MJPEG often allows higher USB webcam resolutions.
    cap.set(
        cv2.CAP_PROP_FOURCC,
        cv2.VideoWriter_fourcc(*"MJPG")
    )

    resolutions = [
        (3840, 2160, 30),  # 4K UHD
        (2560, 1440, 30),  # 1440p
        (1920, 1080, 30),  # Full HD
    ]

    for width, height, fps in resolutions:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, fps)

        actual_width = int(
            cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        )
        actual_height = int(
            cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        )

        if actual_width >= width and actual_height >= height:
            print(
                f"Camera resolution: "
                f"{actual_width} x {actual_height}"
            )
            return actual_width, actual_height

    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(
        f"Camera supports: "
        f"{actual_width} x {actual_height}"
    )

    return actual_width, actual_height



class LatestFrameCamera:
    def __init__(self, camera=1):
        self.cap = cv2.VideoCapture(camera, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap.release()
            self.cap = cv2.VideoCapture(camera)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {camera}")

        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.cap.set(cv2.CAP_PROP_FPS, 60)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        print("Camera:", self.cap.get(cv2.CAP_PROP_FRAME_WIDTH), "x",
              self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT),
              "reported FPS:", self.cap.get(cv2.CAP_PROP_FPS))

        self.lock = threading.Lock()
        self.frame = None
        self.seq = 0
        self.running = True
        self.thread = threading.Thread(target=self._capture, daemon=True)
        self.thread.start()

    def _capture(self):
        while self.running:
            ok, frame = self.cap.read()
            if not ok:
                time.sleep(0.02)
                continue
            with self.lock:
                self.frame = frame
                self.seq += 1

    def read(self):
        with self.lock:
            return (None if self.frame is None else self.frame.copy()), self.seq

    def release(self):
        self.running = False
        self.thread.join(timeout=2)
        self.cap.release()


def speech_worker(items):
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 150)
        while True:
            word = items.get()
            if word is None:
                break
            try:
                engine.say(word.replace("_", " "))
                engine.runAndWait()
            except Exception as exc:
                print("Speech error:", exc)
        engine.stop()
    except Exception as exc:
        print("Speech initialization error:", exc)


def draw_line(image, text, line_number, color=(0, 255, 0)):
    y = 38 + line_number * 39
    cv2.putText(image, text, (16, y), cv2.FONT_HERSHEY_SIMPLEX,
                0.76, (0, 0, 0), 5, cv2.LINE_AA)
    cv2.putText(image, text, (16, y), cv2.FONT_HERSHEY_SIMPLEX,
                0.76, color, 2, cv2.LINE_AA)


def run(camera=1):
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Frame-based model missing: {MODEL_PATH}")

    model = joblib.load(MODEL_PATH)
    if not hasattr(model, "predict_proba") or not hasattr(model, "classes_"):
        raise ValueError("Expected a trained frame-based classifier with predict_proba().")
    if getattr(model, "n_features_in_", None) != 126:
        raise ValueError("The frame-based model must expect 126 features.")

    webcam = LatestFrameCamera(camera)
    speech_queue = queue.Queue(maxsize=1)
    threading.Thread(target=speech_worker, args=(speech_queue,), daemon=True).start()

    recent = deque(maxlen=STABLE_FRAMES)
    last_speech_time = 0.0
    last_spoken = None
    last_seq = -1
    previous_time = time.monotonic()
    fps = 0.0

    try:
        with mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=0,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        ) as hands:
            while True:
                frame, seq = webcam.read()
                if frame is None or seq == last_seq:
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                    time.sleep(0.002)
                    continue
                last_seq = seq

                # Preserve the orientation of the previously supplied live.py.
                frame = cv2.flip(frame, 1)
                small = cv2.resize(frame, PROCESS_SIZE, interpolation=cv2.INTER_AREA)
                rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                rgb.flags.writeable = False
                result = hands.process(rgb)
                now = time.monotonic()

                label = "NO HAND"
                top_text = "Top 3: -"
                stable_text = "Stable: -"

                if hands_present(result):
                    feature = vectorize_hands(result)
                    probabilities = model.predict_proba(feature.reshape(1, -1))[0]
                    top_indices = np.argsort(probabilities)[::-1][:3]
                    top_text = "Top 3: " + " | ".join(
                        f"{model.classes_[i]} {probabilities[i]:.2f}"
                        for i in top_indices
                    )

                    best_index = int(top_indices[0])
                    confidence = float(probabilities[best_index])
                    best_sign = str(model.classes_[best_index])
                    predicted = best_sign if confidence >= CONFIDENCE_THRESHOLD else None
                    label = (f"{predicted} ({confidence:.2f})" if predicted
                             else f"UNCERTAIN ({confidence:.2f})")

                    recent.append(predicted)
                    valid_votes = [word for word in recent if word is not None]
                    if valid_votes:
                        winner, votes = Counter(valid_votes).most_common(1)[0]
                        stable_text = f"Stable: {winner} {votes}/{STABLE_FRAMES}"
                        if (len(recent) == STABLE_FRAMES
                                and votes >= MIN_STABLE_VOTES
                                and predicted == winner
                                and now - last_speech_time >= SPEECH_COOLDOWN):
                            try:
                                speech_queue.put_nowait(winner)
                                last_spoken = winner
                                last_speech_time = now
                                recent.clear()
                                print("Speaking:", winner)
                            except queue.Full:
                                pass
                else:
                    recent.clear()

                elapsed = now - previous_time
                previous_time = now
                if elapsed > 0:
                    instant_fps = 1.0 / elapsed
                    fps = instant_fps if fps == 0 else 0.85 * fps + 0.15 * instant_fps

                preview = cv2.resize(frame, PREVIEW_SIZE, interpolation=cv2.INTER_AREA)
                draw_line(preview, label, 0)
                draw_line(preview, top_text, 1, (0, 255, 255))
                draw_line(preview, stable_text, 2)
                draw_line(preview, f"AI FPS: {fps:.1f}", 3)
                draw_line(preview, f"Last spoken: {last_spoken or 'None'}", 4)
                draw_line(preview, "Q to quit", 5)
                cv2.imshow("SignBridge AI - Frame Recognition", preview)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    finally:
        webcam.release()
        cv2.destroyAllWindows()
        try:
            speech_queue.put_nowait(None)
        except queue.Full:
            pass


if __name__ == "__main__":
    run(camera=1)
    configure_camera_4k(cap)