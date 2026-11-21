
from pathlib import Path
from collections import Counter
import joblib
import numpy as np

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
MODEL = ROOT / "models" / "sign_model.joblib"

if not MODEL.is_file():
    raise SystemExit("Model not found.")

model = joblib.load(MODEL)

if isinstance(model, dict):
    model = model.get("model", model)

if not hasattr(model, "predict"):
    raise SystemExit("Unsupported model format.")

files = sorted(DATA.glob("*.npz"))

if not files:
    raise SystemExit("No training data found.")

print("\n=== SIGNBRIDGE RECOGNITION DIAGNOSTIC ===")

print("\nModel classes:")
print(", ".join(map(str, model.classes_)))

print("\n=== SAVED TRAINING DATA ===")

total = 0
all_errors = []

for file in files:
    label = file.stem.upper()

    with np.load(file) as data:
        features = data["features"]

    count = len(features)
    total += count

    print(f"\n{label}: {count} frames")

    if features.ndim != 2:
        print("  ERROR: Invalid data shape")
        continue

    expected = getattr(model, "n_features_in_", None)

    if expected and features.shape[1] != expected:
        print(
            f"  ERROR: Model expects {expected} "
            f"features; data contains {features.shape[1]}"
        )
        continue

    if label not in model.classes_:
        print("  WARNING: Label missing from trained model")
        continue

    predictions = model.predict(features)
    agreement = np.mean(predictions == label) * 100

    mistakes = Counter(
        prediction
        for prediction in predictions
        if prediction != label
    )

    print(f"  Saved-data agreement: {agreement:.1f}%")

    if mistakes:
        print("  Most frequent confusions:")
        for wrong, number in mistakes.most_common(3):
            print(f"    {wrong}: {number} frames")

    all_errors.append((agreement, label))

print(f"\nTotal saved frames: {total}")

print("\n=== SIGNS NEEDING ATTENTION ===")

for agreement, label in sorted(all_errors)[:10]:
    print(f"{label}: {agreement:.1f}%")

print(
    "\nIMPORTANT: These figures are measured on "
    "stored training data, not unseen recordings. "
    "They are NOT independent accuracy estimates."
)
