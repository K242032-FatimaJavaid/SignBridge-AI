
import threading
import time
from collections import deque
from pathlib import Path

import joblib
import numpy as np

from recognition.features import hands_present
from recognition.sequence_precision import SequenceRecognizer
from sequence_full import LENGTH, extract_features, temporal_features


ROOT = Path(__file__).resolve().parents[1]


def load_model(filename):
    path = ROOT / "models" / filename
    if not path.is_file():
        raise FileNotFoundError(path)

    saved = joblib.load(path)
    return saved["model"] if isinstance(saved, dict) else saved


class UnifiedRecognizer:
    def __init__(self, word_model):
        self.word_model = word_model
        self.words = SequenceRecognizer(word_model)

        self.alphabet = load_model(
            "alnum_alphabet_v1.joblib"
        )
        self.numbers = load_model(
            "alnum_numbers_v1.joblib"
        )

        uv_path = (
            ROOT / "models" /
            "alphabet_uv_specialist_v1.joblib"
        )

        self.uv_model = (
            load_model("alphabet_uv_specialist_v1.joblib")
            if uv_path.is_file()
            else None
        )

        self.lock = threading.RLock()

        self.mode = "words"
        self.recent_words = deque(maxlen=3)

        self.absent_since = None
        self.end_sent = False
        self.after_characters = False

        self.char_window = deque(maxlen=LENGTH)
        self.char_votes = deque(maxlen=4)
        self.char_ready = False
        self.char_accepted = False
        self.char_samples = 0

        self.last_character = None
        self.last_status = "READY FOR SIGN"

        print(
            "[UNIFIED] Word, alphabet and number "
            "models loaded.",
            flush=True
        )

    def arm(self):
        # Preserve the existing precision button.
        with self.lock:
            self._reset_to_words()
            return self.words.arm()

    def use_automatic(self):
        with self.lock:
            self._reset_to_words()
            return self.words.use_automatic()

    def _reset_to_words(self):
        self.mode = "words"
        self.words = SequenceRecognizer(self.word_model)
        self.recent_words.clear()
        self.char_window.clear()
        self.char_votes.clear()
        self.char_ready = False
        self.char_accepted = False
        self.char_samples = 0
        self.after_characters = False
        self.absent_since = None
        self.end_sent = False

    def _start_characters(self, mode):
        self.mode = mode
        self.char_window.clear()
        self.char_votes.clear()
        self.char_ready = False
        self.char_accepted = False
        self.char_samples = 0
        self.last_character = None
        self.after_characters = False

        print(
            f"[UNIFIED] Entered {mode} recognition",
            flush=True
        )

    def _classify_character(self):
        model = (
            self.alphabet
            if self.mode == "alphabet"
            else self.numbers
        )

        clip = np.asarray(
            self.char_window,
            dtype=np.float32
        )

        vector = temporal_features(clip)
        sample = vector.reshape(1, -1)

        probabilities = model.predict_proba(sample)[0]
        ranking = np.argsort(probabilities)[::-1]

        best = int(ranking[0])
        second = int(ranking[1])

        label = str(model.classes_[best])
        confidence = float(probabilities[best])
        margin = confidence - float(
            probabilities[second]
        )

        valid = (
            label != "OTHER"
            and confidence >= (
                0.22 if self.mode == "alphabet" else 0.28
            )
            and margin >= (
                0.06 if self.mode == "alphabet" else 0.12
            )
        )

        # R has repeatedly ranked first with a
        # lower confidence, so use repeated votes.
        if self.mode == "alphabet" and label == "R":
            valid = (
                confidence >= 0.18
                and margin >= 0.01
            )

        # U and V were confused by the main model.
        # Use the specialist only in that case.
        elif (
            self.mode == "alphabet"
            and self.uv_model is not None
            and label in ("U", "V")
        ):
            top_three = {
                str(model.classes_[i])
                for i in ranking[:3]
            }

            if {"U", "V"}.issubset(top_three):
                uv_probs = self.uv_model.predict_proba(
                    sample
                )[0]

                uv_best = int(np.argmax(uv_probs))

                label = str(
                    self.uv_model.classes_[uv_best]
                )
                confidence = float(uv_probs[uv_best])
                valid = confidence >= 0.65

        self.char_votes.append(
            label if valid else None
        )

        required_votes = (
            3
            if self.mode == "alphabet" and label == "R"
            else 2
        )

        recent = list(self.char_votes)[-required_votes:]

        confirmed = (
            valid
            and len(recent) == required_votes
            and all(v == label for v in recent)
        )

        if not confirmed:
            return (
                f"POSSIBLE {label} ({confidence:.2f})",
                None
            )

        self.char_accepted = True
        self.last_character = label

        kind = (
            "LETTER"
            if self.mode == "alphabet"
            else "DIGIT"
        )

        token = f"{kind}:{label}"

        print(
            "[UNIFIED CONFIRMED]",
            token,
            f"confidence={confidence:.2f}",
            flush=True
        )

        return f"CONFIRMED {kind} {label}", token

    def update(self, result):
        with self.lock:
            return self._update_locked(result)

    def _update_locked(self, result):
        now = time.monotonic()
        visible = hands_present(result)

        if visible:
            self.absent_since = None
            self.end_sent = False

            if self.after_characters:
                self.after_characters = False

        else:
            if self.absent_since is None:
                self.absent_since = now

        # -----------------------------------------
        # WORD RECOGNITION
        # -----------------------------------------
        if self.mode == "words":

            # After fingerspelling, give the user a
            # longer pause to either continue with
            # words or finish the whole sentence.
            if self.after_characters and not visible:
                elapsed = now - self.absent_since

                if elapsed >= 1.65 and not self.end_sent:
                    self.end_sent = True
                    self.after_characters = False
                    self.recent_words.clear()

                    return (
                        "SENTENCE COMPLETE",
                        None,
                        True
                    )

                return "READY FOR WORDS", None, False

            label, sign, ended = self.words.update(
                result
            )

            if ended:
                self.recent_words.clear()

            if sign:
                self.recent_words.append(sign)

                last_two = list(self.recent_words)[-2:]

                if last_two == ["NAME", "IS"]:
                    self._start_characters("alphabet")
                    return (
                        "SPELL NAME - REMOVE HAND FIRST",
                        sign,
                        ended
                    )

                if last_two == ["AGE", "IS"]:
                    self._start_characters("numbers")
                    return (
                        "SIGN AGE - REMOVE HAND FIRST",
                        sign,
                        ended
                    )

            return label, sign, ended

        # -----------------------------------------
        # ALPHABET / NUMBER RECOGNITION
        # -----------------------------------------
        if not visible:
            elapsed = now - self.absent_since

            # Short release separates characters.
            if elapsed >= 0.25:
                self.char_ready = True
                self.char_accepted = False
                self.char_window.clear()
                self.char_votes.clear()
                self.char_samples = 0

            # A longer pause returns to words
            # automatically, without a UI switch.
            if elapsed >= 0.95:
                self.mode = "words"
                self.words = SequenceRecognizer(
                    self.word_model
                )

                self.recent_words.clear()
                self.after_characters = True

                self.char_window.clear()
                self.char_votes.clear()

                print(
                    "[UNIFIED] Returned to words",
                    flush=True
                )

                return "READY FOR WORDS", None, False

            return "READY FOR NEXT CHARACTER", None, False

        # After NAME IS or AGE IS, require a short
        # hand release before collecting characters.
        if not self.char_ready:
            return (
                "REMOVE HAND BRIEFLY TO START",
                None,
                False
            )

        # A held character is recorded only once.
        if self.char_accepted:
            return (
                f"CONFIRMED {self.last_character} "
                "- RELEASE HAND",
                None,
                False
            )

        self.char_window.append(
            extract_features(result)
        )

        self.char_samples += 1

        if len(self.char_window) < LENGTH:
            return (
                f"READING CHARACTER "
                f"{len(self.char_window)}/{LENGTH}",
                None,
                False
            )

        # Keep the 24-frame sequence format used
        # by alnum_manager.py during training.
        if (self.char_samples - LENGTH) % 3 != 0:
            return self.last_status, None, False

        label, token = self._classify_character()
        self.last_status = label

        return label, token, False
