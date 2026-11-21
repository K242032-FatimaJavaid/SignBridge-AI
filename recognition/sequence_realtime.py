
import time
from collections import deque

import numpy as np

from recognition.features import hands_present
from sequence_full import (
    extract_features,
    temporal_features,
    LENGTH,
)


class SequenceRecognizer:
    def __init__(self, model):
        self.model = model
        self.window = deque(maxlen=LENGTH)
        self.votes = deque(maxlen=2)

        self.frames_since_prediction = 0
        self.missing_frames = 0
        self.active_sign = None
        self.last_label = "READY FOR SIGN"
        self._no_hand_since = None
        self._sentence_end_sent = False

        self._evidence = deque(maxlen=8)
        self._last_emit_at = 0.0

        # Only used to disambiguate MY versus HELP.
        self._my_help_trace = deque(maxlen=12)
        self._my_pending_since = None

        self._class_index = {
            str(label): index
            for index, label in enumerate(model.classes_)
        }

    def update(self, result):
        now = time.monotonic()

        # Reset recognition after hands leave the frame.
        if not hands_present(result):
            self.missing_frames += 1

            if self._no_hand_since is None:
                self._no_hand_since = now
            self.last_label = "READY FOR SIGN"

            if self.missing_frames == 3:
                self.window.clear()
                self.votes.clear()
                self._evidence.clear()
                self._my_help_trace.clear()
                self._my_pending_since = None
                self.frames_since_prediction = 0
                self.active_sign = None

            if (
                not self._sentence_end_sent
                and now - self._no_hand_since >= 1.0
            ):
                self._sentence_end_sent = True
                print(
                    "[AUTO SENTENCE END]",
                    flush=True
                )
                return self.last_label, None, True

            return self.last_label, None, False

        self.missing_frames = 0
        self._no_hand_since = None
        self._sentence_end_sent = False

        self.window.append(extract_features(result))

        if len(self.window) < LENGTH:
            self.last_label = "READING SIGN..."
            return self.last_label, None, False

        self.frames_since_prediction += 1

        if self.frames_since_prediction < 2:
            return self.last_label, None, False

        self.frames_since_prediction = 0

        clip = np.asarray(
            self.window,
            dtype=np.float32
        )

        vector = temporal_features(clip)

        probabilities = self.model.predict_proba(
            vector.reshape(1, -1)
        )[0]

        ranking = np.argsort(probabilities)[::-1]

        best = int(ranking[0])
        second = int(ranking[1])

        predicted = str(self.model.classes_[best])
        confidence = float(probabilities[best])
        runner_up = float(probabilities[second])
        margin = confidence - runner_up

        # Track HELP and MY, including when either is
        # the runner-up rather than the top prediction.
        my_index = self._class_index.get("MY")
        help_index = self._class_index.get("HELP")

        my_probability = (
            float(probabilities[my_index])
            if my_index is not None else 0.0
        )

        help_probability = (
            float(probabilities[help_index])
            if help_index is not None else 0.0
        )

        self._my_help_trace.append(
            (predicted, my_probability, help_probability)
        )

        # If HELP becomes plausible, cancel a pending
        # MY decision so it is not emitted prematurely.
        if help_probability >= 0.28:
            self._my_pending_since = None

        # Preserve rejection of weak and OTHER gestures.
        if predicted == "OTHER":
            self._evidence.append((None, 0.0, 0.0))
            self.last_label = "GESTURE IGNORED"
            return self.last_label, None, False

        minimum_conf = 0.20 if predicted == "FRIEND" else 0.27
        minimum_margin = 0.06 if predicted == "FRIEND" else 0.08

        if confidence < minimum_conf or margin < minimum_margin:
            self._evidence.append((None, 0.0, 0.0))
            self.last_label = "READING SIGN..."
            return self.last_label, None, False

        self._evidence.append(
            (predicted, confidence, margin)
        )

        self.last_label = (
            f"POSSIBLE {predicted} ({confidence:.2f})"
        )

        recent = list(self._evidence)[-7:]

        supporting = [
            (prob, gap)
            for label, prob, gap in recent
            if label == predicted
        ]

        if len(supporting) < 3:
            return self.last_label, None, False

        scores = [prob for prob, _ in supporting]
        gaps = [gap for _, gap in supporting]

        peak = max(scores)
        average = sum(scores) / len(scores)

        reliable_readings = sum(
            prob >= 0.30 for prob in scores
        )

        separated_readings = sum(
            gap >= 0.12 for gap in gaps
        )

        # Original confirmation requirements.
        confirmed = (
            len(supporting) >= 3
            and peak >= 0.58
            and average >= 0.36
            and reliable_readings >= 2
            and separated_readings >= 2
        )

        # SIGNBRIDGE_CLAP_AUTO_V1
        # CLAP has lower calibrated probabilities.
        # Require repeated, clearly separated votes.
        if predicted == "CLAP":
            strong_clap_votes = sum(
                prob >= 0.28 and gap >= 0.15
                for prob, gap in supporting
            )

            confirmed = (
                len(supporting) >= 3
                and peak >= 0.35
                and average >= 0.30
                and strong_clap_votes >= 2
            )

        # SIGNBRIDGE_FRIEND_AUTO_V1
        if predicted == "FRIEND":
            confirmed = (
                len(supporting) >= 3
                and peak >= 0.26
                and average >= 0.22
                and sum(p >= 0.23 for p in scores) >= 2
                and sum(g >= 0.06 for g in gaps) >= 2
            )

        # SIGNBRIDGE_STOP_CONFIRM_V1
        # Moderate STOP threshold with repeated evidence.
        if predicted == "STOP":
            confirmed = (
                len(supporting) >= 3
                and peak >= 0.48
                and average >= 0.39
                and sum(p >= 0.37 for p in scores) >= 2
                and sum(g >= 0.13 for g in gaps) >= 2
            )

        if not confirmed:
            return self.last_label, None, False

        # Additional verification ONLY for MY.
        # Allow HELP to emerge before accepting MY.
        if predicted == "MY":
            if self._my_pending_since is None:
                self._my_pending_since = now
                self.last_label = "CHECKING MY / HELP..."
                return self.last_label, None, False

            if now - self._my_pending_since < 0.75:
                self.last_label = "CHECKING MY / HELP..."
                return self.last_label, None, False

            trace = list(self._my_help_trace)[-8:]

            my_votes = sum(
                label == "MY"
                for label, _, _ in trace
            )

            average_my = sum(
                my_prob
                for _, my_prob, _ in trace
            ) / len(trace)

            highest_help = max(
                help_prob
                for _, _, help_prob in trace
            )

            # Reject MY when the recent sequence is
            # unstable or HELP is a serious contender.
            if (
                my_votes < 5
                or average_my < 0.42
                or highest_help >= 0.28
            ):
                self._my_pending_since = None
                self.last_label = "MY / HELP UNCERTAIN"
                return self.last_label, None, False

        # Existing duplicate prevention.
        if predicted == self.active_sign:
            return self.last_label, None, False

        if now - self._last_emit_at < 0.65:
            return self.last_label, None, False

        self.active_sign = predicted
        self._last_emit_at = now
        self._my_pending_since = None
        self._evidence.clear()

        self.last_label = f"CONFIRMED {predicted}"

        print(
            "[AUTO CONFIRMED]",
            predicted,
            f"peak={peak:.2f}",
            f"average={average:.2f}",
            f"votes={len(supporting)}",
            flush=True
        )

        return self.last_label, predicted, False
