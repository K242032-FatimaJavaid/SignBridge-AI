
from pathlib import Path
from datetime import datetime
import ast
import shutil

ROOT = Path(__file__).resolve().parent

WEBCAM = ROOT / "recognition" / "webcam_streamlit.py"
RUNTIME = ROOT / "recognition" / "sequence_realtime.py"
MODEL = ROOT / "models" / "sequence_full_v1.joblib"
TRAINING = ROOT / "sequence_full.py"

for path in (WEBCAM, MODEL, TRAINING):
    if not path.is_file():
        raise SystemExit(f"Required file missing: {path}")

original = WEBCAM.read_text(encoding="utf-8")

if "SequenceRecognizer" in original:
    raise SystemExit("Sequence integration already present.")

# The upgrade retains the previously optimized webcam.
if "def _recognize_small_frame(self, frame):" not in original:
    raise SystemExit(
        "Optimized webcam method not found. "
        "No changes made. Your current webcam file "
        "needs a different integration patch."
    )

# Build the new real-time sequence recognition component.
runtime_code = '''
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

    def update(self, result):
        """
        Return:
        (display_label, confirmed_sign, sentence_finished)
        """

        if not hands_present(result):
            self.missing_frames += 1
            self.last_label = "NO HAND"

            if self.missing_frames == 3:
                self.window.clear()
                self.votes.clear()
                self.frames_since_prediction = 0
                self.active_sign = None
                return "NO HAND", None, True

            return "NO HAND", None, False

        self.missing_frames = 0

        features = extract_features(result)
        self.window.append(features)

        if len(self.window) < LENGTH:
            self.last_label = (
                f"ANALYZING {len(self.window)}/{LENGTH}"
            )
            return self.last_label, None, False

        # Predict periodically, not on every camera frame.
        self.frames_since_prediction += 1

        if self.frames_since_prediction < 3:
            return self.last_label, None, False

        self.frames_since_prediction = 0

        clip = np.asarray(
            self.window, dtype=np.float32
        )

        vector = temporal_features(clip)

        probabilities = self.model.predict_proba(
            vector.reshape(1, -1)
        )[0]

        ranking = np.argsort(probabilities)[::-1]

        best = int(ranking[0])
        confidence = float(probabilities[best])

        second = (
            float(probabilities[ranking[1]])
            if len(ranking) > 1 else 0.0
        )

        margin = confidence - second
        predicted = str(self.model.classes_[best])

        # Use the same acceptance thresholds as the pilot.
        if confidence < 0.60 or margin < 0.15:
            self.votes.clear()
            self.last_label = "UNCERTAIN"
            return self.last_label, None, False

        if predicted == "OTHER":
            self.votes.clear()
            self.last_label = "OTHER - IGNORED"
            return self.last_label, None, False

        self.last_label = f"{predicted} ({confidence:.2f})"
        self.votes.append(predicted)

        stable = (
            len(self.votes) == 2
            and self.votes[0] == self.votes[1]
        )

        # Avoid repeatedly adding a sign while it is held.
        if stable and predicted != self.active_sign:
            self.active_sign = predicted
            return self.last_label, predicted, False

        return self.last_label, None, False
'''

# Validate the new component.
compile(runtime_code, str(RUNTIME), "exec")

updated = original

old_model = (
    'MODEL_PATH = ROOT / "models" / "sign_model.joblib"'
)
new_model = (
    'MODEL_PATH = ROOT / "models" / '
    '"sequence_full_v1.joblib"'
)

if updated.count(old_model) != 1:
    raise SystemExit("Unexpected model path in webcam module.")

updated = updated.replace(old_model, new_model, 1)

old_import = (
    "from recognition.features import "
    "vectorize_hands, hands_present"
)

if updated.count(old_import) != 1:
    raise SystemExit("Unexpected webcam feature imports.")

updated = updated.replace(
    old_import,
    old_import
    + "\nfrom recognition.sequence_realtime "
    + "import SequenceRecognizer",
    1
)

old_init = "        self.model = load_sign_model()"

if updated.count(old_init) != 1:
    raise SystemExit("Could not locate model initialization.")

updated = updated.replace(
    old_init,
    old_init
    + "\n        self.sequence_recognizer = "
    + "SequenceRecognizer(self.model)",
    1
)

# Replace only the AI inference method.
# Preserve the camera preview, video label renderer,
# existing speech threads and Streamlit interface.
new_method = '''
    def _recognize_small_frame(self, frame):
        if self.stop_event.is_set():
            return

        small = frame.reformat(
            width=640,
            height=360,
            format="bgr24"
        )

        image = small.to_ndarray()
        image = cv2.flip(image, 1)

        rgb = cv2.cvtColor(
            image, cv2.COLOR_BGR2RGB
        )
        rgb.flags.writeable = False

        result = self.hands.process(rgb)

        label, sign, sentence_ended = (
            self.sequence_recognizer.update(result)
        )

        with self.lock:
            self.current_label = label
            self.source_resolution = (
                frame.width, frame.height
            )

        if sign:
            with self.lock:
                busy = self.sentence_pending

                if not busy:
                    self.detected_signs.append(sign)
                    self.detected_signs = (
                        self.detected_signs[-100:]
                    )

                    self.sentence_words.append(
                        sign.replace("_", " ")
                    )
                    self.sentence_words = (
                        self.sentence_words[-100:]
                    )

            if not busy:
                self.last_spoken = sign
                self.last_sign_time = time.monotonic()
                self.ready_for_next_sign = False
                print("Sequence recognized:", sign)

        if sentence_ended:
            self.ready_for_next_sign = True
            self.finish_sentence()
'''

tree = ast.parse(updated)

processor = next(
    (
        node for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "SignVideoProcessor"
    ),
    None
)

if processor is None:
    raise SystemExit("SignVideoProcessor class not found.")

method = next(
    (
        node for node in processor.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_recognize_small_frame"
    ),
    None
)

if method is None:
    raise SystemExit("Recognition method not found.")

lines = updated.splitlines(keepends=True)

lines[method.lineno - 1:method.end_lineno] = [
    new_method.lstrip("\n").rstrip() + "\n"
]

updated = "".join(lines)

# Confirm both modules compile before saving.
compile(updated, str(WEBCAM), "exec")

if RUNTIME.exists():
    raise SystemExit(
        "sequence_realtime.py already exists. "
        "No files changed."
    )

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

backup = WEBCAM.with_name(
    f"webcam_before_19_signs_{timestamp}.py"
)

shutil.copy2(WEBCAM, backup)

RUNTIME.write_text(runtime_code, encoding="utf-8")
WEBCAM.write_text(updated, encoding="utf-8")

print()
print("=====================================")
print("19-SIGN INTEGRATION INSTALLED")
print("=====================================")
print("New model: sequence_full_v1.joblib")
print("24-frame movement recognition enabled.")
print("Original frame-based model preserved.")
print("4K webcam processing code preserved.")
print("Sentence and speech code preserved.")
print("Backup:", backup)
print()
print("Next: python -m streamlit run app.py")
