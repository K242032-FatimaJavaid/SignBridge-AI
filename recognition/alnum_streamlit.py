
import time
import threading
from collections import deque
from pathlib import Path

import av
import cv2
import joblib
import mediapipe as mp
import numpy as np
import streamlit as st

from streamlit_webrtc import VideoProcessorBase, webrtc_streamer

from recognition.features import hands_present
from sequence_full import LENGTH, extract_features, temporal_features


ROOT = Path(__file__).resolve().parents[1]


@st.cache_resource
def load_character_models(mode):
    path = ROOT / "models" / f"alnum_{mode}_v1.joblib"

    saved = joblib.load(path)
    model = saved["model"]

    specialist = None

    if mode == "alphabet":
        specialist_path = (
            ROOT / "models" / "alphabet_uv_specialist_v1.joblib"
        )

        if specialist_path.exists():
            specialist = joblib.load(specialist_path)["model"]

    return model, specialist


class CharacterProcessor(VideoProcessorBase):
    def __init__(self, mode, model, specialist=None):
        self.mode = mode
        self.model = model
        self.specialist = specialist

        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=0,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        )

        self.lock = threading.Lock()
        self.characters = []
        self.history = []

        self.window = deque(maxlen=LENGTH)
        self.votes = deque(maxlen=3)

        self.sample_count = 0
        self.last_sample = 0.0
        self.no_hand_since = None

        self.active = False
        self.status = "READY FOR SIGN"

    def get_snapshot(self):
        with self.lock:
            return {
                "text": "".join(self.characters),
                "history": self.history.copy(),
                "status": self.status,
            }

    def add_space(self):
        with self.lock:
            if self.characters and self.characters[-1] != " ":
                self.characters.append(" ")

    def undo(self):
        with self.lock:
            if self.characters:
                self.characters.pop()

    def clear_text(self):
        with self.lock:
            self.characters.clear()
            self.history.clear()

    def set_status(self, status):
        with self.lock:
            self.status = status

    def classify_window(self):
        features = temporal_features(
            np.asarray(self.window, dtype=np.float32)
        )

        sample = features.reshape(1, -1)

        probabilities = self.model.predict_proba(sample)[0]
        ranking = np.argsort(probabilities)[::-1]

        first = int(ranking[0])
        second = int(ranking[1])

        label = str(self.model.classes_[first])
        confidence = float(probabilities[first])
        margin = confidence - float(probabilities[second])

        valid = (
            label != "OTHER"
            and confidence >= 0.28
            and margin >= 0.12
        )

        # R needs repeated confirmation because its
        # main-model confidence is consistently low.
        if self.mode == "alphabet" and label == "R":
            valid = (
                confidence >= 0.18
                and margin >= 0.01
            )

        # Apply the U/V specialist when both letters
        # are plausible in the main alphabet model.
        elif (
            self.mode == "alphabet"
            and self.specialist is not None
            and label in ("U", "V")
            and {"U", "V"}.issubset({
                str(self.model.classes_[i])
                for i in ranking[:3]
            })
        ):
            uv_probs = self.specialist.predict_proba(sample)[0]
            uv_index = int(np.argmax(uv_probs))

            label = str(self.specialist.classes_[uv_index])
            confidence = float(uv_probs[uv_index])

            valid = confidence >= 0.65

        self.votes.append(label if valid else None)

        required = (
            3 if self.mode == "alphabet" and label == "R"
            else 2
        )

        recent = list(self.votes)[-required:]

        confirmed = (
            not self.active
            and valid
            and len(recent) == required
            and all(item == label for item in recent)
        )

        if not confirmed:
            self.set_status(
                f"POSSIBLE {label} ({confidence:.2f})"
                if valid else "UNCERTAIN - HOLD SIGN"
            )
            return

        with self.lock:
            self.characters.append(label)
            self.history.append(label)
            self.status = f"CONFIRMED {label}"

        self.active = True

        print(
            "[CHARACTER CONFIRMED]",
            self.mode,
            label,
            f"confidence={confidence:.2f}",
            flush=True,
        )

    def process_sample(self, frame, now):
        small = cv2.resize(frame, (640, 360))

        rgb = cv2.cvtColor(
            small,
            cv2.COLOR_BGR2RGB,
        )

        result = self.hands.process(rgb)

        if not hands_present(result):
            if self.no_hand_since is None:
                self.no_hand_since = now

            if now - self.no_hand_since >= 0.40:
                self.window.clear()
                self.votes.clear()
                self.active = False
                self.sample_count = 0
                self.set_status("READY FOR NEXT SIGN")

            return

        self.no_hand_since = None

        if self.active:
            return

        self.window.append(extract_features(result))
        self.sample_count += 1

        if len(self.window) < LENGTH:
            self.set_status(
                f"READING SIGN {len(self.window)}/{LENGTH}"
            )
            return

        # Evaluate a full 24-frame sequence, then
        # use several later readings for confirmation.
        if (self.sample_count - LENGTH) % 4 == 0:
            self.classify_window()

    def recv(self, frame):
        image = frame.to_ndarray(format="bgr24")

        # Match the mirrored video used during
        # your original alnum_manager collection.
        image = cv2.flip(image, 1)

        now = time.monotonic()

        # Sample landmarks at approximately 12 FPS
        # while preserving the live video stream.
        if now - self.last_sample >= 1.0 / 12.0:
            self.last_sample = now
            self.process_sample(image, now)

        with self.lock:
            status = self.status
            text = "".join(self.characters)

        cv2.rectangle(
            image, (10, 10),
            (min(image.shape[1] - 10, 650), 100),
            (22, 30, 43), -1,
        )

        cv2.putText(
            image,
            f"{self.mode.upper()} MODE",
            (22, 43),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 220, 220),
            2,
        )

        cv2.putText(
            image,
            status[:42],
            (22, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
        )

        cv2.putText(
            image,
            "TEXT: " + text[-35:],
            (22, image.shape[0] - 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
        )

        return av.VideoFrame.from_ndarray(
            image, format="bgr24"
        )

    def close(self):
        self.hands.close()


@st.fragment(run_every=1)
def character_results(ctx):
    processor = ctx.video_processor

    if processor is None:
        st.info("Waiting for the webcam...")
        return

    data = processor.get_snapshot()

    st.markdown("### Recognized text")
    st.code(data["text"] or "Waiting for characters...")

    st.caption(data["status"])

    a, b, c = st.columns(3)

    with a:
        if st.button("Add Space", key="alnum_space"):
            processor.add_space()
            st.rerun(scope="fragment")

    with b:
        if st.button("Undo", key="alnum_undo"):
            processor.undo()
            st.rerun(scope="fragment")

    with c:
        if st.button("Clear", key="alnum_clear"):
            processor.clear_text()
            st.rerun(scope="fragment")

    if st.button(
        "Speak Recognized Text",
        key="alnum_speak",
        use_container_width=True,
    ):
        text = processor.get_snapshot()["text"].strip()

        if text:
            try:
                from recognition.webcam_streamlit import windows_speak
                windows_speak(text)
                st.success("Text spoken.")
            except Exception as exc:
                st.error(f"Speech error: {exc}")
        else:
            st.warning("No characters recognized yet.")


def show_alnum(mode):
    names = {
        "alphabet": "Alphabet A-Z",
        "numbers": "Numbers 0-9",
    }

    st.subheader(names[mode])
    st.caption(
        "Perform one character at a time. Hold the "
        "complete sign until confirmed, then remove "
        "your hand briefly before the next character."
    )

    if mode == "alphabet":
        st.info(
            "The U/V specialist is used when U and V "
            "compete. R requires additional confirmation. "
            "J and Z require their full movements."
        )

    path = ROOT / "models" / f"alnum_{mode}_v1.joblib"

    if not path.is_file():
        st.error(
            f"Model not found: {path.name}. "
            f"Train it first using alnum_manager.py."
        )
        return

    try:
        model, specialist = load_character_models(mode)
    except Exception as exc:
        st.error(f"Could not load character model: {exc}")
        return

    ctx = webrtc_streamer(
        key=f"signbridge-{mode}-webcam",
        video_processor_factory=lambda: CharacterProcessor(
            mode, model, specialist
        ),
        media_stream_constraints={
            "video": {
                "width": {"ideal": 1280},
                "height": {"ideal": 720},
                "frameRate": {"ideal": 30},
            },
            "audio": False,
        },
        async_processing=True,
    )

    if ctx.state.playing:
        character_results(ctx)
