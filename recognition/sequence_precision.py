
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

            # SIGNBRIDGE_CLAP_PRECISE_V1
            if label == "CLAP":
                rejected = (
                    confidence < 0.35
                    or margin < 0.20
                )
            elif label == "FRIEND":
                rejected = (
                    confidence < 0.38
                    or margin < 0.10
                )
            else:
                rejected = (
                    confidence < 0.60
                    or margin < 0.15
                )

            # STOP-specific precise threshold
            if label == "STOP":
                rejected = (
                    confidence < 0.45
                    or margin < 0.13
                )

            if rejected:
                self.last_label = "UNCERTAIN"
                return self.last_label, None, False

            if label == "OTHER":
                self.last_label = "GESTURE IGNORED"
                return self.last_label, None, False

            self.last_label = (
                f"{label} ({confidence:.2f})"
            )

            return self.last_label, label, False
