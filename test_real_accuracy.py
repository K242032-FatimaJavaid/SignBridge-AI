
from pathlib import Path
from collections import Counter
import csv
import time

import cv2
import joblib
import mediapipe as mp
import numpy as np

from recognition.features import (
    vectorize_hands,
    hands_present,
)

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "models" / "sign_model.joblib"
REPORT = ROOT / "real_accuracy_results.csv"

TEST_SIGNS = {
    ord("1"): "MY",
    ord("2"): "PLEASE",
    ord("3"): "QUIET",
    ord("4"): "THANK_YOU",
    ord("5"): "I",
    ord("0"): "UNKNOWN",
}

DURATION = 2.5
THRESHOLD = 0.70
MIN_MARGIN = 0.08

model = joblib.load(MODEL)
if isinstance(model, dict):
    model = model["model"]

camera = cv2.VideoCapture(1, cv2.CAP_DSHOW)
if not camera.isOpened():
    camera.release()
    camera = cv2.VideoCapture(1)

if not camera.isOpened():
    raise SystemExit("Could not open webcam 1.")

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

expected = "MY"
end_time = None
predictions = []
trial_number = 0

new_file = not REPORT.exists()
report = REPORT.open("a", newline="", encoding="utf-8")
writer = csv.writer(report)

if new_file:
    writer.writerow([
        "trial", "expected", "predicted",
        "correct", "agreement_percent",
        "predictions"
    ])

print("1 MY | 2 PLEASE | 3 QUIET")
print("4 THANK_YOU | 5 I | 0 UNKNOWN")
print("SPACE = record a test | Q = quit")
print("Hold the sign before pressing SPACE.")

try:
    with mp.solutions.hands.Hands(
        max_num_hands=2,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.5,
    ) as hands:

        while True:
            ok, frame = camera.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)

            # Use original webcam resolution,
            # matching the training data collection.
            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            result = hands.process(rgb)
            prediction = "NO_HAND"
            confidence = 0.0

            if hands_present(result):
                features = vectorize_hands(result)
                probabilities = model.predict_proba(
                    features.reshape(1, -1)
                )[0]

                ranked = np.argsort(probabilities)[::-1]
                top = int(ranked[0])
                confidence = float(probabilities[top])
                runner_up = (
                    float(probabilities[ranked[1]])
                    if len(ranked) > 1 else 0.0
                )

                if (
                    confidence >= THRESHOLD
                    and confidence - runner_up >= MIN_MARGIN
                ):
                    prediction = str(model.classes_[top])
                else:
                    prediction = "UNKNOWN"

            now = time.monotonic()

            if end_time is not None:
                predictions.append(prediction)

                if now >= end_time:
                    trial_number += 1
                    counts = Counter(predictions)
                    final, count = counts.most_common(1)[0]

                    agreement = (
                        100 * count / len(predictions)
                    )
                    correct = (
                        final == expected
                        or (
                            expected == "UNKNOWN"
                            and final in ("UNKNOWN", "NO_HAND")
                        )
                    )

                    writer.writerow([
                        trial_number,
                        expected,
                        final,
                        correct,
                        round(agreement, 1),
                        str(dict(counts)),
                    ])
                    report.flush()

                    print(
                        f"Trial {trial_number}: "
                        f"Expected={expected}, "
                        f"Predicted={final}, "
                        f"Correct={correct}"
                    )
                    print("Frame votes:", dict(counts))

                    end_time = None
                    predictions = []

            preview = cv2.resize(frame, (960, 540))

            lines = [
                f"TEST: {expected}",
                f"Current: {prediction} ({confidence:.2f})",
                (
                    "RECORDING..."
                    if end_time is not None
                    else "Hold sign, then press SPACE"
                ),
                "1-5: Select sign | 0: Unknown | Q: Quit",
            ]

            for i, line in enumerate(lines):
                cv2.putText(
                    preview, line,
                    (15, 35 + i * 38),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 255, 0), 2
                )

            cv2.imshow(
                "SignBridge Real Accuracy Test",
                preview
            )

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break
            elif key in TEST_SIGNS and end_time is None:
                expected = TEST_SIGNS[key]
            elif key == 32 and end_time is None:
                predictions = []
                end_time = time.monotonic() + DURATION
                print(f"Recording fresh attempt: {expected}")

finally:
    camera.release()
    cv2.destroyAllWindows()
    report.close()

print(f"Results saved: {REPORT}")
