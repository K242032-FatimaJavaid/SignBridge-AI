
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).resolve().parent
WEBCAM = ROOT / "recognition" / "webcam_streamlit.py"
PRECISION = ROOT / "recognition" / "sequence_precision.py"
BASE = ROOT / "recognition" / "sequence_realtime.py"

if not WEBCAM.is_file() or not BASE.is_file():
    raise SystemExit("Required recognition files are missing.")

if PRECISION.exists():
    raise SystemExit(
        "sequence_precision.py already exists. "
        "No changes made."
    )

original = WEBCAM.read_text(encoding="utf-8")

old_import = (
    "from recognition.sequence_realtime "
    "import SequenceRecognizer"
)

new_import = (
    "from recognition.sequence_precision "
    "import SequenceRecognizer"
)

if original.count(old_import) != 1:
    raise SystemExit(
        "Expected sequence recognizer import not found. "
        "No changes made."
    )

anchor = '    st.markdown("### Live Recognition History")'

if original.count(anchor) != 1:
    raise SystemExit(
        "Live recognition results section not found. "
        "No changes made."
    )

precision_code = '''
"""Optional complete-clip recognition for SignBridge AI."""

import threading
import time

import numpy as np

from recognition.sequence_realtime import (
    SequenceRecognizer as BaseRecognizer
)
from recognition.features import hands_present
from sequence_full import (
    LENGTH,
    extract_features,
    temporal_features,
)


class SequenceRecognizer(BaseRecognizer):
    def __init__(self, model):
        super().__init__(model)

        self._capture_lock = threading.Lock()
        self._precise_mode = False
        self._recording = False
        self._capture_start_at = 0.0
        self._capture_frames = []

    def arm(self):
        """Prepare one complete sign recording."""
        with self._capture_lock:
            self._precise_mode = True
            self._recording = True
            self._capture_start_at = (
                time.monotonic() + 1.5
            )
            self._capture_frames = []

            self.window.clear()
            self.votes.clear()
            self.active_sign = None
            self.missing_frames = 0
            self.last_label = "GET READY..."

    def use_automatic(self):
        """Return to the existing sliding-window recognizer."""
        with self._capture_lock:
            self._precise_mode = False
            self._recording = False
            self._capture_frames = []

            self.window.clear()
            self.votes.clear()
            self.active_sign = None
            self.missing_frames = 0
            self.frames_since_prediction = 0
            self.last_label = "READY FOR SIGN"

    def update(self, result):
        with self._capture_lock:
            if not self._precise_mode:
                return super().update(result)

            if not self._recording:
                return self.last_label, None, False

            if time.monotonic() < self._capture_start_at:
                self.last_label = "GET READY..."
                return self.last_label, None, False

            # Same landmark extraction as standalone test.
            features = extract_features(result)
            self._capture_frames.append(features)

            self.last_label = "READING SIGN..."

            if len(self._capture_frames) < LENGTH:
                return self.last_label, None, False

            clip = np.asarray(
                self._capture_frames[:LENGTH],
                dtype=np.float32
            )

            self._recording = False
            self._capture_frames = []

            # Reject clips with insufficient hand detection.
            visible = np.count_nonzero(
                np.any(
                    clip[:, [65, 131]] > 0.5,
                    axis=1
                )
            )

            if visible < 18:
                self.last_label = "HAND NOT DETECTED"
                print(
                    "[PRECISION] Too few visible-hand frames",
                    flush=True
                )
                return self.last_label, None, False

            vector = temporal_features(clip)

            probabilities = self.model.predict_proba(
                vector.reshape(1, -1)
            )[0]

            ranking = np.argsort(probabilities)[::-1]

            best = int(ranking[0])
            second = int(ranking[1])

            label = str(self.model.classes_[best])
            confidence = float(probabilities[best])
            margin = float(
                probabilities[best]
                - probabilities[second]
            )

            top = [
                (
                    str(self.model.classes_[i]),
                    round(float(probabilities[i]), 3)
                )
                for i in ranking[:3]
            ]

            print(
                "[PRECISION]",
                "Top predictions:", top,
                "Margin:", round(margin, 3),
                flush=True
            )

            if confidence < 0.60 or margin < 0.15:
                self.last_label = "UNCERTAIN"
                return self.last_label, None, False

            if label == "OTHER":
                self.last_label = "GESTURE IGNORED"
                return self.last_label, None, False

            self.last_label = (
                f"{label} ({confidence:.2f})"
            )

            return self.last_label, label, False
'''

controls = '''
    st.markdown("### Recognition Controls")

    capture_col, auto_col = st.columns(2)

    with capture_col:
        if st.button(
            "Record One Sign",
            key="precise_sign_capture",
            use_container_width=True
        ):
            processor.sequence_recognizer.arm()
            st.info(
                "Get ready, then perform one complete "
                "sign for approximately two seconds."
            )

    with auto_col:
        if st.button(
            "Automatic Mode",
            key="return_auto_recognition",
            use_container_width=True
        ):
            processor.sequence_recognizer.use_automatic()
            st.success("Automatic recognition restored.")

    st.caption(
        "Precise mode captures one complete sign "
        "per button press. Use Finish Sentence "
        "when your sentence is complete."
    )

'''

updated = original.replace(
    old_import, new_import, 1
)

updated = updated.replace(
    anchor,
    controls + anchor,
    1
)

# Check both Python files before saving.
compile(precision_code, str(PRECISION), "exec")
compile(updated, str(WEBCAM), "exec")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

backup = WEBCAM.with_name(
    f"webcam_before_precise_mode_{stamp}.py"
)

shutil.copy2(WEBCAM, backup)

try:
    PRECISION.write_text(
        precision_code,
        encoding="utf-8"
    )
    WEBCAM.write_text(
        updated,
        encoding="utf-8"
    )
except Exception:
    shutil.copy2(backup, WEBCAM)
    PRECISION.unlink(missing_ok=True)
    raise

print("=================================")
print("PRECISE SIGN CAPTURE INSTALLED")
print("=================================")
print("Existing automatic recognition retained.")
print("Complete 24-frame capture mode added.")
print("19-sign model unchanged.")
print("Camera and video UI unchanged.")
print("Backup:", backup)
