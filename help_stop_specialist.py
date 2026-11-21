from pathlib import Path
import numpy as np
import joblib

from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)

from sequence_full import temporal_features

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data_sequences_full"
MODEL = ROOT / "models/sequence_extended_v1.joblib"
OUTPUT = ROOT / "models/help_stop_specialist_v1.joblib"

x, y, sessions = [], [], []

for label in ["HELP", "STOP"]:
    for path in sorted((DATA / label).glob("*.npz")):
        with np.load(path) as item:
            clip = item["clip"]
            session = str(item["session"])

        x.append(temporal_features(clip))
        y.append(label)
        sessions.append(session)

x = np.asarray(x)
y = np.asarray(y)
sessions = np.asarray(sessions)

train_mask = np.isin(sessions, ["S2", "S3"])
test_mask = sessions == "S1"

for label in ["HELP", "STOP"]:
    training = np.sum(train_mask & (y == label))
    testing = np.sum(test_mask & (y == label))
    print(f"{label}: train={training}, test={testing}")

    if training < 12 or testing < 5:
        raise SystemExit("Insufficient data for validation.")

specialist = make_pipeline(
    StandardScaler(),
    SVC(
        kernel="rbf",
        C=3,
        gamma="scale",
        class_weight="balanced",
        probability=True,
        random_state=42,
    )
)

specialist.fit(x[train_mask], y[train_mask])

old_model = joblib.load(MODEL)

old_predictions = old_model.predict(x[test_mask])
new_predictions = specialist.predict(x[test_mask])

actual = y[test_mask]

old_acc = accuracy_score(actual, old_predictions)
new_acc = accuracy_score(actual, new_predictions)

print("\nORIGINAL MODEL")
print(f"Accuracy on HELP/STOP clips: {old_acc:.2%}")

print("\nSPECIALIST RESULTS")
print(classification_report(
    actual, new_predictions,
    labels=["HELP", "STOP"],
    zero_division=0
))

print("Confusion matrix [HELP, STOP]:")
print(confusion_matrix(
    actual, new_predictions,
    labels=["HELP", "STOP"]
))

print(f"\nOld accuracy: {old_acc:.2%}")
print(f"Specialist accuracy: {new_acc:.2%}")

help_recall = np.mean(
    new_predictions[actual == "HELP"] == "HELP"
)
stop_recall = np.mean(
    new_predictions[actual == "STOP"] == "STOP"
)

if (
    new_acc >= old_acc + 0.05
    and help_recall >= 0.80
    and stop_recall >= 0.75
):
    if OUTPUT.exists():
        print("Specialist already exists; not overwriting.")
    else:
        joblib.dump({"model": specialist}, OUTPUT)
        print("Specialist saved:", OUTPUT)
else:
    print("Specialist not reliable enough.")
    print("No model saved or replaced.")
