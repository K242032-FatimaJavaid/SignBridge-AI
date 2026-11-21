
from pathlib import Path
from datetime import datetime
import ast
import re
import shutil
import joblib

ROOT = Path(__file__).resolve().parent

webcam = ROOT / "recognition/webcam_streamlit.py"
realtime = ROOT / "recognition/sequence_realtime.py"
precision = ROOT / "recognition/sequence_precision.py"
app = ROOT / "app.py"

new_model = ROOT / "models/sequence_extended_v1.joblib"

NEW_SIGNS = [
    "GOODBYE",
    "STOP",
    "YOU_ARE_WELCOME",
    "WHAT",
    "FRIEND",
    "CLAP",
]

files = [webcam, realtime, precision, app]

for path in files + [new_model]:
    if not path.is_file():
        raise SystemExit(
            f"Missing: {path}\nNo changes made."
        )

# Check the model before activating it.
model = joblib.load(new_model)
classes = set(str(x) for x in model.classes_)

if not set(NEW_SIGNS).issubset(classes):
    raise SystemExit(
        "New model is missing one or more "
        "new signs. No changes made."
    )

changes = {}

# 1. Activate expanded model in the SAME webcam.
source = webcam.read_text(encoding="utf-8-sig")

old = (
    'MODEL_PATH = ROOT / "models" / '
    '"sequence_full_v1.joblib"'
)
new = (
    'MODEL_PATH = ROOT / "models" / '
    '"sequence_extended_v1.joblib"'
)

if source.count(old) != 1:
    raise SystemExit(
        "Webcam model setting differs from expected. "
        "Nothing changed."
    )

changes[webcam] = source.replace(old, new, 1)


# 2. Lower ONLY CLAP's automatic confirmation.
source = realtime.read_text(encoding="utf-8-sig")

old = '''        if not confirmed:
            return self.last_label, None, False

        # Additional verification ONLY for MY.'''

new = '''        # SIGNBRIDGE_CLAP_AUTO_V1
        # CLAP has lower calibrated probabilities.
        # Require repeated, clearly separated votes.
        if predicted == "CLAP":
            strong_clap_votes = sum(
                prob >= 0.35 and gap >= 0.20
                for prob, gap in supporting
            )

            confirmed = (
                len(supporting) >= 3
                and peak >= 0.43
                and average >= 0.38
                and strong_clap_votes >= 3
            )

        if not confirmed:
            return self.last_label, None, False

        # Additional verification ONLY for MY.'''

if source.count(old) != 1:
    raise SystemExit(
        "Automatic confirmation block differs "
        "from expected. Nothing changed."
    )

changes[realtime] = source.replace(old, new, 1)


# 3. Lower ONLY CLAP's precise-mode threshold.
source = precision.read_text(encoding="utf-8-sig")

old = '''            if confidence < 0.60 or margin < 0.15:'''

new = '''            # SIGNBRIDGE_CLAP_PRECISE_V1
            if label == "CLAP":
                rejected = (
                    confidence < 0.35
                    or margin < 0.20
                )
            else:
                rejected = (
                    confidence < 0.60
                    or margin < 0.15
                )

            if rejected:'''

if source.count(old) != 1:
    raise SystemExit(
        "Precise confirmation block differs "
        "from expected. Nothing changed."
    )

changes[precision] = source.replace(old, new, 1)


# 4. Update the dashboard vocabulary count.
source = app.read_text(encoding="utf-8-sig")

pattern = (
    r"(?m)^TRAINED_SIGNS\s*=\s*"
    r"(\[[^\r\n]*\])"
)

matches = list(re.finditer(pattern, source))

if len(matches) != 1:
    raise SystemExit(
        "Dashboard vocabulary definition differs "
        "from expected. Nothing changed."
    )

match = matches[0]

labels = list(
    ast.literal_eval(match.group(1))
)

for label in NEW_SIGNS:
    if label not in labels:
        labels.append(label)

if not set(labels).issubset(classes):
    raise SystemExit(
        "Dashboard contains signs not present "
        "in the trained model. Nothing changed."
    )

replacement = "TRAINED_SIGNS = " + repr(labels)

changes[app] = (
    source[:match.start()]
    + replacement
    + source[match.end():]
)


# 5. Compile everything before modifying files.
for path, updated in changes.items():
    compile(updated, str(path), "exec")

# 6. Back up all affected files.
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

backup = (
    ROOT / "backups" /
    f"before_25_words_{stamp}"
)

for path in changes:
    relative = path.relative_to(ROOT)
    destination = backup / relative
    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )
    shutil.copy2(path, destination)

# 7. Install, with automatic rollback on failure.
try:
    for path, updated in changes.items():
        path.write_text(
            updated,
            encoding="utf-8"
        )
except Exception:
    for path in changes:
        relative = path.relative_to(ROOT)
        shutil.copy2(backup / relative, path)
    raise

print()
print("================================")
print("25-WORD INTEGRATION COMPLETE")
print("================================")
print("Words:", len(labels))
print("Letters:", 26)
print("Digits:", 10)
print("Total:", len(labels) + 36)
print()
print("Expanded model activated.")
print("CLAP confirmation adjusted.")
print("STOP/HELP thresholds preserved.")
print("Single webcam preserved.")
print("Alphabet and numbers preserved.")
print("Sentence and speech code preserved.")
print("Backup:", backup)

if "TOTAL_VOCABULARY" not in changes[app]:
    print(
        "NOTE: Dashboard count formula not found. "
        "Check the displayed statistic."
    )
