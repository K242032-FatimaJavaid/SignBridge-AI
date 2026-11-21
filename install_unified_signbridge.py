
from pathlib import Path
from datetime import datetime
import ast
import shutil
import textwrap

ROOT = Path(__file__).resolve().parent
WEBCAM = ROOT / "recognition" / "webcam_streamlit.py"
MODULE = ROOT / "recognition" / "unified_realtime.py"

required = [
    WEBCAM,
    ROOT / "sequence_full.py",
    ROOT / "models" / "sequence_full_v1.joblib",
    ROOT / "models" / "alnum_alphabet_v1.joblib",
    ROOT / "models" / "alnum_numbers_v1.joblib",
]

missing = [str(p) for p in required if not p.is_file()]

if missing:
    raise SystemExit(
        "Required project files missing:\n"
        + "\n".join(missing)
        + "\nNo files were changed."
    )

if MODULE.exists():
    raise SystemExit(
        "unified_realtime.py already exists. "
        "Nothing changed. Check before reinstalling."
    )


# =====================================================
# UNIFIED RECOGNIZER
# =====================================================

module_code = r'''
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
            and confidence >= 0.28
            and margin >= 0.12
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
'''


# =====================================================
# MODIFY ONLY THE CURRENT WEBCAM INTEGRATION
# =====================================================

source = WEBCAM.read_text(encoding="utf-8-sig")

old_import = (
    "from recognition.sequence_precision "
    "import SequenceRecognizer"
)

new_import = (
    "from recognition.unified_realtime "
    "import UnifiedRecognizer"
)

old_init = (
    "self.sequence_recognizer = "
    "SequenceRecognizer(self.model)"
)

new_init = (
    "self.sequence_recognizer = "
    "UnifiedRecognizer(self.model)"
)

if source.count(old_import) != 1:
    raise SystemExit(
        "Unexpected webcam import. "
        "Original file unchanged."
    )

if source.count(old_init) != 1:
    raise SystemExit(
        "Unexpected recognizer initialization. "
        "Original file unchanged."
    )

source = source.replace(old_import, new_import, 1)
source = source.replace(old_init, new_init, 1)

# Locate the actual current sign-handling block
# with Python's parser, not a fragile line number.
tree = ast.parse(source)

processor = next(
    (
        node for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "SignVideoProcessor"
    ),
    None
)

if processor is None:
    raise SystemExit("SignVideoProcessor not found.")

recognize = next(
    (
        node for node in processor.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_recognize_small_frame"
    ),
    None
)

if recognize is None:
    raise SystemExit(
        "_recognize_small_frame not found."
    )

sign_blocks = [
    node for node in recognize.body
    if isinstance(node, ast.If)
    and isinstance(node.test, ast.Name)
    and node.test.id == "sign"
]

if len(sign_blocks) != 1:
    raise SystemExit(
        "Could not uniquely identify the sign block."
    )

sign_block = sign_blocks[0]

new_sign_code = """
if sign:
    is_letter = sign.startswith("LETTER:")
    is_digit = sign.startswith("DIGIT:")

    if is_letter or is_digit:
        character = sign.split(":", 1)[1]

        kind = (
            "letters" if is_letter else "digits"
        )

        with self.lock:
            if (
                self.sentence_words
                and getattr(
                    self, "_last_token_kind", None
                ) == kind
            ):
                self.sentence_words[-1] += character
            else:
                self.sentence_words.append(character)

            self._last_token_kind = kind
            self.detected_signs.append(character)
            self.detected_signs = (
                self.detected_signs[-100:]
            )

    else:
        word = sign.replace("_", " ")

        with self.lock:
            self.sentence_words.append(word)
            self._last_token_kind = "word"

            self.detected_signs.append(sign)
            self.detected_signs = (
                self.detected_signs[-100:]
            )

    with self.lock:
        self.sentence_words = self.sentence_words[-100:]

    self.last_spoken = sign
    self.last_sign_time = time.monotonic()
    self.ready_for_next_sign = False

    print(
        "[UNIFIED SENTENCE TOKEN]",
        sign,
        flush=True
    )
"""

lines = source.splitlines(keepends=True)

original_line = lines[sign_block.lineno - 1]
indentation = len(original_line) - len(
    original_line.lstrip()
)

replacement = textwrap.indent(
    textwrap.dedent(new_sign_code).strip() + "\n",
    " " * indentation
)

lines[
    sign_block.lineno - 1:sign_block.end_lineno
] = [replacement]

updated_webcam = "".join(lines)


# =====================================================
# VALIDATE AND BACK UP BEFORE SAVING
# =====================================================

compile(module_code, str(MODULE), "exec")
compile(updated_webcam, str(WEBCAM), "exec")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = ROOT / "backups" / f"before_unified_{stamp}"
backup.mkdir(parents=True, exist_ok=False)

shutil.copy2(
    WEBCAM,
    backup / "webcam_streamlit.py"
)

shutil.copy2(
    ROOT / "sequence_full.py",
    backup / "sequence_full.py"
)

MODULE.write_text(module_code, encoding="utf-8")
WEBCAM.write_text(
    updated_webcam,
    encoding="utf-8"
)

print()
print("======================================")
print("UNIFIED SIGNBRIDGE INTEGRATION INSTALLED")
print("======================================")
print("One webcam: Words + Alphabet + Numbers")
print("NAME IS -> Alphabet recognition")
print("AGE IS -> Number recognition")
print("Characters join into names and numbers")
print("U/V specialist supported")
print("R repeated-confirmation enabled")
print("Existing sentence and speech code preserved")
print("Original word model unchanged")
print("Original training datasets unchanged")
print()
print("Backup location:", backup)
