
from pathlib import Path
from datetime import datetime
import ast
import shutil
import textwrap

ROOT = Path(__file__).resolve().parent
FILE = ROOT / "recognition" / "sequence_realtime.py"

if not FILE.is_file():
    raise SystemExit("Sequence recognizer not found.")

original = FILE.read_text(encoding="utf-8")

if "SIGNBRIDGE_EVIDENCE_V2" in original:
    raise SystemExit("This upgrade is already installed.")

tree = ast.parse(original)

target_class = next(
    (
        node for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "SequenceRecognizer"
    ),
    None,
)

if target_class is None:
    raise SystemExit("SequenceRecognizer class not found.")

method = next(
    (
        node for node in target_class.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "update"
    ),
    None,
)

if method is None:
    raise SystemExit("update() method not found.")

# Replace only the automatic prediction method.
new_method = """
def update(self, result):
    # SIGNBRIDGE_EVIDENCE_V2
    #
    # Keep the 24-frame sequence model.
    # Use temporal evidence instead of demanding
    # two consecutive high-confidence predictions.

    if not hasattr(self, "_evidence"):
        self._evidence = deque(maxlen=8)
        self._last_emit_at = 0.0

    now = time.monotonic()

    # -------------------------------
    # NO HAND: reset sign boundaries
    # -------------------------------
    if not hands_present(result):
        self.missing_frames += 1
        self.last_label = "READY FOR SIGN"

        # Allow a repeated sign after a real pause.
        if self.missing_frames == 3:
            self.window.clear()
            self.votes.clear()
            self._evidence.clear()
            self.frames_since_prediction = 0
            self.active_sign = None

        # About one second without visible hands
        # marks the end of the current sentence.
        if self.missing_frames == 12:
            return self.last_label, None, True

        return self.last_label, None, False

    self.missing_frames = 0

    # Clear stale evidence if a new recording
    # window was started by another mode.
    if len(self.window) == 0:
        self._evidence.clear()

    features = extract_features(result)
    self.window.append(features)

    if len(self.window) < LENGTH:
        self.last_label = "READING SIGN..."
        return self.last_label, None, False

    # Predict every second sampled frame.
    # The 4K video pipeline remains unchanged.
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

    # -------------------------------
    # Reject unsupported/weak frames
    # -------------------------------
    if predicted == "OTHER":
        self._evidence.append((None, 0.0, 0.0))
        self.last_label = "GESTURE IGNORED"
        return self.last_label, None, False

    if confidence < 0.27 or margin < 0.08:
        self._evidence.append((None, 0.0, 0.0))
        self.last_label = "READING SIGN..."
        return self.last_label, None, False

    # Save the top prediction of this window.
    self._evidence.append(
        (predicted, confidence, margin)
    )

    self.last_label = (
        f"{predicted} ({confidence:.2f})"
    )

    # -------------------------------
    # Combine recent predictions
    # -------------------------------
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

    # Require multiple supporting readings,
    # including at least one strong prediction.
    confirmed = (
        len(supporting) >= 3
        and peak >= 0.58
        and average >= 0.36
        and reliable_readings >= 2
        and separated_readings >= 2
    )

    if not confirmed:
        return self.last_label, None, False

    # -------------------------------
    # Prevent duplicate words
    # -------------------------------
    if predicted == self.active_sign:
        return self.last_label, None, False

    if now - self._last_emit_at < 0.65:
        return self.last_label, None, False

    self.active_sign = predicted
    self._last_emit_at = now
    self._evidence.clear()

    print(
        "[AUTO CONFIRMED]",
        predicted,
        f"peak={peak:.2f}",
        f"average={average:.2f}",
        f"votes={len(supporting)}",
        flush=True
    )

    return self.last_label, predicted, False
"""

new_method = (
    textwrap.indent(
        textwrap.dedent(new_method).strip("\n"),
        "    "
    )
    + "\n"
)

lines = original.splitlines(keepends=True)

lines[method.lineno - 1:method.end_lineno] = [
    new_method
]

updated = "".join(lines)

# New logic uses monotonic time.
if not any(
    isinstance(node, ast.Import)
    and any(alias.name == "time" for alias in node.names)
    for node in tree.body
):
    updated = "import time\n" + updated

# Do not silently overwrite anything if syntax fails.
compile(updated, str(FILE), "exec")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

backup = FILE.with_name(
    f"sequence_before_evidence_{stamp}.py"
)

shutil.copy2(FILE, backup)
FILE.write_text(updated, encoding="utf-8")

print()
print("======================================")
print("AUTOMATIC RECOGNITION UPGRADED")
print("======================================")
print("Evidence-based sign confirmation enabled.")
print("HELP and WANT can use supporting predictions.")
print("Other gestures still require rejection checks.")
print("Repeated held signs are suppressed.")
print("Sentence pause increased.")
print("Original 19-sign model unchanged.")
print("4K webcam and interface unchanged.")
print("Precise Mode retained.")
print()
print("Backup:", backup)
```

## Step 2 — Apply and verify

Run these commands:

```powershell
python fix_automatic_recognition.py
python -m py_compile recognition\sequence_realtime.py
python -m py_compile recognition\sequence_precision.py
python -m py_compile recognition\webcam_streamlit.py
```

If all three compilation checks pass, start your application:

```powershell
python -m streamlit run app.py
```

## Step 3 — Test automatic sentence recognition

Select **Automatic Mode** in ASL → Speech. You shouldn't have to press *Record One Sign*.

Perform the following sequence, allowing the recognizer to capture each movement:

<box border radius="lg" padding={3} gap={2}>
  <row align="center" justify="center" gap={2}>
    {#each ["I","WANT","WATER"] as word,i}
      <box background="surface-secondary" radius="md" padding={{x:3,y:2}} align="center">
        <text weight="medium">{word}</text>
      </box>
      {#if i<2}
        <icon name="arrow-right" color="tertiary"/>
      {/if}
    {/each}
  </row>
  <divider color="subtle"/>
  <text color="secondary" weight="medium" size="xs">Expected sentence</text>
  <title size="lg" textAlign="center">I WANT WATER</title>
</box>

Then test HELP separately, followed by MY and PLEASE to check that the fix hasn't harmed previously working signs.

When a sign is confirmed, you should see terminal output like:

```text
[AUTO CONFIRMED] WANT peak=0.69 average=0.43 votes=4
Sequence recognized: WANT
```

Those numbers are illustrative; your actual results will differ.

### What this fixes—and what it doesn't

This specifically addresses the **short bursts of correct predictions** visible in your logs. It does not retrain the classifier or guarantee that every overlapping 24-frame window will correctly represent a complete sign.

The evidence thresholds are provisional and still need testing against all 19 signs, particularly for false positives. Your existing model is preserved, and the script creates a backup of the original recognizer.

If this approach works reliably, we can later improve movement-boundary detection further. For now, **test automatic recognition with the video visible and check whether HELP and WANT enter the sentence consistently without repeated or incorrect words.**