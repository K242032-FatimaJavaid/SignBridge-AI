#Evaluating Model
from pathlib import Path
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (
    accuracy_score, f1_score,
    classification_report, confusion_matrix
)

from sequence_extended import DATA, LABELS, temporal_features

OUT = Path("evaluation")
OUT.mkdir(exist_ok=True)

# Load the SAME recordings and features as the working SVM.
X, y, sessions = [], [], []

for file in sorted(DATA.glob("*/*.npz")):
    with np.load(file) as item:
        X.append(temporal_features(item["clip"]))
        y.append(str(item["label"]))
        sessions.append(str(item["session"]))

X = np.asarray(X)
y = np.asarray(y)
sessions = np.asarray(sessions)

# Match the existing S2/S3 -> S1 evaluation.
train = sessions != "S1"
test = sessions == "S1"

assert train.any() and test.any(), "Missing training or S1 clips"
assert set(y[train]) == set(LABELS), "Training classes incomplete"
assert set(y[test]) == set(LABELS), "Test classes incomplete"

print("Training:", len(y[train]), "clips")
print("Testing:", len(y[test]), "clips")
print("Classes:", len(LABELS))
print("Training sessions:", sorted(set(sessions[train])))
print("Test sessions:", sorted(set(sessions[test])))

models = {
    "SVM": make_pipeline(
        StandardScaler(),
        SVC(
            kernel="rbf", C=3.0, gamma="scale",
            class_weight="balanced",
            probability=True, random_state=42
        )
    ),
    "Random Forest": RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced_subsample",
        random_state=42, n_jobs=-1
    ),
    "k-NN": make_pipeline(
        StandardScaler(),
        KNeighborsClassifier(
            n_neighbors=5, weights="distance"
        )
    ),
    "Random Baseline": DummyClassifier(
        strategy="uniform", random_state=42
    ),
    "Majority Baseline": DummyClassifier(
        strategy="most_frequent"
    )
}

results = []
svm_predictions = None

for name, model in models.items():
    print("\nTraining:", name, flush=True)
    model.fit(X[train], y[train])
    predictions = model.predict(X[test])

    acc = accuracy_score(y[test], predictions)
    f1 = f1_score(
        y[test], predictions,
        labels=LABELS,
        average="macro",
        zero_division=0
    )

    results.append((name, acc, f1))
    print(f"{name}: Accuracy={acc:.2%}, Macro-F1={f1:.3f}")

    if name == "SVM":
        svm_predictions = predictions
        report = classification_report(
            y[test], predictions,
            labels=LABELS, zero_division=0
        )
        (OUT / "svm_classification_report.txt").write_text(
            report, encoding="utf-8"
        )

with open(OUT / "model_comparison.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Model", "Accuracy", "Macro F1"])
    writer.writerows(results)

# CHART 1: Accuracy and Macro-F1 comparison
names = [r[0] for r in results]
accuracy = [r[1] for r in results]
f1_scores = [r[2] for r in results]

p = np.arange(len(names))
fig, ax = plt.subplots(figsize=(11, 6))
ax.bar(p - 0.2, accuracy, 0.4, label="Accuracy")
ax.bar(p + 0.2, f1_scores, 0.4, label="Macro F1")
ax.set_xticks(p, names, rotation=18, ha="right")
ax.set_ylim(0, 1.05)
ax.set_ylabel("Score")
ax.set_title("SignBridge AI: Model Comparison")
ax.legend()
ax.grid(axis="y", alpha=0.2)
fig.tight_layout()
fig.savefig(OUT / "01_model_comparison.png", dpi=200)
plt.close(fig)

# CHART 2: SVM confusion matrix
cm = confusion_matrix(
    y[test], svm_predictions, labels=LABELS
)

fig, ax = plt.subplots(figsize=(14, 13))
image = ax.imshow(cm, cmap="Blues")

ax.set_xticks(range(len(LABELS)), LABELS, rotation=90)
ax.set_yticks(range(len(LABELS)), LABELS)
ax.set_xlabel("Predicted Sign")
ax.set_ylabel("Actual Sign")
ax.set_title("SVM Confusion Matrix - Session S1")

for i in range(len(LABELS)):
    for j in range(len(LABELS)):
        if cm[i, j]:
            ax.text(
                j, i, str(cm[i, j]),
                ha="center", va="center",
                fontsize=7
            )

fig.colorbar(image, ax=ax)
fig.tight_layout()
fig.savefig(
    OUT / "02_svm_confusion_matrix.png", dpi=200
)
plt.close(fig)

print("\nEVALUATION COMPLETED")
print("Saved to:", OUT.resolve())
print("Working trained models were NOT modified.")
