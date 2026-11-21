
"""SignBridge AI - Live ASL recognition with Windows automatic speech."""

from pathlib import Path
from collections import deque
import threading
import time
import queue
import subprocess
import base64

import av
import cv2
import joblib
import mediapipe as mp
import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase

from recognition.features import vectorize_hands, hands_present


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "sign_model.joblib"

CONFIDENCE_THRESHOLD = 0.70
STABLE_FRAMES = 8
SPEECH_COOLDOWN = 3.0
NO_HAND_RESET_FRAMES = 5


@st.cache_resource
def load_sign_model():
    """Load the trained sign recognition model."""
    return joblib.load(MODEL_PATH)


def windows_speak(text):
    """Speak text using Windows built-in speech synthesis."""

    encoded_text = base64.b64encode(
        text.encode("utf-8")
    ).decode("ascii")

    script = f"""
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {{
    $bytes = [Convert]::FromBase64String('{encoded_text}')
    $message = [System.Text.Encoding]::UTF8.GetString($bytes)
    $speaker.Speak($message)
}}
finally {{
    $speaker.Dispose()
}}
"""

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script
        ],
        capture_output=True,
        text=True,
        timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or "Windows speech failed."
        )


class SignVideoProcessor(VideoProcessorBase):

    def __init__(self):
        self.model = load_sign_model()

        self.hands = mp.solutions.hands.Hands(
            max_num_hands=2,
            min_detection_confidence=0.6
        )

        self.recent_predictions = deque(maxlen=STABLE_FRAMES)

        self.last_spoken = None
        self.last_speech_time = 0.0
        self.ready_for_next_sign = True
        self.no_hand_frames = 0

        self.lock = threading.Lock()
        self.detected_signs = []

        # Speech queue and background thread
        self.speech_queue = queue.Queue(maxsize=3)
        self.stop_event = threading.Event()

        self.speaker = threading.Thread(
            target=self.speech_worker,
            daemon=True
        )
        self.speaker.start()

    def speech_worker(self):
        """Speak recognized signs without freezing the webcam."""

        while not self.stop_event.is_set():

            try:
                sign = self.speech_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                if sign is None:
                    break

                windows_speak(sign.replace("_", " "))
                print("Spoken:", sign)

            except Exception as exc:
                print("Speech error:", exc)

            finally:
                self.speech_queue.task_done()

    def recv(self, frame):
        """Process each webcam frame and recognize signs."""

        image = frame.to_ndarray(format="bgr24")
        image = cv2.flip(image, 1)

        result = self.hands.process(
            cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        )

        label = "NO HAND"
        predicted_sign = None
        hand_detected = hands_present(result)

        # Recognize a sign when a hand is present
        if hand_detected:

            probabilities = self.model.predict_proba(
                [vectorize_hands(result)]
            )[0]

            idx = probabilities.argmax()
            confidence = float(probabilities[idx])

            if confidence >= CONFIDENCE_THRESHOLD:
                predicted_sign = str(self.model.classes_[idx])
                label = f"{predicted_sign} ({confidence:.2f})"
            else:
                label = "UNCERTAIN"

        # Reset only after several consecutive no-hand frames
        if not hand_detected:

            self.no_hand_frames += 1
            self.recent_predictions.clear()

            if self.no_hand_frames >= NO_HAND_RESET_FRAMES:
                self.ready_for_next_sign = True

        else:

            self.no_hand_frames = 0
            self.recent_predictions.append(predicted_sign)

        # Require several consecutive matching predictions
        stable = (
            len(self.recent_predictions) == STABLE_FRAMES
            and predicted_sign is not None
            and all(
                sign == predicted_sign
                for sign in self.recent_predictions
            )
        )

        now = time.monotonic()

        # Accept a stable sign and send it to speech
        if (
            stable
            and self.ready_for_next_sign
            and now - self.last_speech_time >= SPEECH_COOLDOWN
        ):

            self.last_spoken = predicted_sign
            self.last_speech_time = now
            self.ready_for_next_sign = False

            with self.lock:
                self.detected_signs.append(predicted_sign)
                self.detected_signs = self.detected_signs[-30:]

            try:
                self.speech_queue.put_nowait(predicted_sign)
            except queue.Full:
                print("Speech queue full:", predicted_sign)

            print("Detected:", predicted_sign)

        # Display the current prediction
        cv2.putText(
            image,
            label,
            (20, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

        # Display the last accepted sign
        if self.last_spoken:

            cv2.putText(
                image,
                f"Last detected: {self.last_spoken}",
                (20, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 0),
                2
            )

        # Show whether another sign can be accepted
        if self.ready_for_next_sign:
            status = "Ready for sign"
        else:
            status = "Remove hand to reset"

        cv2.putText(
            image,
            status,
            (20, image.shape[0] - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        return av.VideoFrame.from_ndarray(
            image,
            format="bgr24"
        )

    def get_detected_signs(self):
        """Retrieve and clear the pending recognition history."""

        with self.lock:
            signs = self.detected_signs.copy()
            self.detected_signs.clear()

        return signs

    def close(self):
        """Release webcam recognition resources."""

        self.stop_event.set()

        try:
            self.speech_queue.put_nowait(None)
        except queue.Full:
            pass

        self.hands.close()


def show_webcam():
    """Display live ASL recognition inside Streamlit."""

    st.subheader("📷 Live ASL Recognition")

    if not MODEL_PATH.exists():
        st.error(
            "Trained sign model not found. "
            "Run python -m recognition.train first."
        )
        return

    st.info(
        "Click START to enable your webcam. "
        "Show HELLO, YES, NO, HELP, or THANK YOU. "
        "Hold the sign steady until recognized, "
        "then remove your hand completely before repeating."
    )

    ctx = webrtc_streamer(
        key="signbridge-webcam",
        video_processor_factory=SignVideoProcessor,
        media_stream_constraints={
            "video": True,
            "audio": False
        },
        async_processing=True,
    )

    if ctx.state.playing:

        st.success(
            "Webcam active! Recognized signs will be spoken automatically."
        )

        st.caption(
            "Speech plays through the speakers of the Windows "
            "computer running SignBridge AI."
        )

        if st.button("📋 Show Recognition History"):

            processor = ctx.video_processor

            if processor:
                signs = processor.get_detected_signs()

                if signs:
                    st.write(
                        "Recognized signs:",
                        ", ".join(
                            sign.replace("_", " ")
                            for sign in signs
                        )
                    )
                else:
                    st.info("No new signs recorded yet.")

    else:
        st.info("Start the webcam to begin recognizing signs.")
