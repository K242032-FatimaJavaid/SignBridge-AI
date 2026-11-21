
"""Diagnose SignBridge AI predictions for the YOU sign."""

from pathlib import Path

import cv2
import joblib
import mediapipe as mp
import numpy as np

from recognition.features import vectorize_hands, hands_present


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "sign_model.joblib"


def main():
    model = joblib.load(MODEL_PATH)

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("ERROR: Could not open webcam.")
        return

    print("SignBridge AI - YOU Diagnostic")
    print("Perform the YOU sign in front of the camera.")
    print("Press Q to quit.")

    mp_hands = mp.solutions.hands

    try:
        with mp_hands.Hands(
            max_num_hands=2,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        ) as hands:

            while True:
                ok, frame = camera.read()

                if not ok:
                    break

                frame = cv2.flip(frame, 1)

                rgb = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2RGB,
                )

                result = hands.process(rgb)

                if hands_present(result):
                    features = vectorize_hands(result)

                    probabilities = model.predict_proba(
                        [features]
                    )[0]

                    top_indices = np.argsort(
                        probabilities
                    )[::-1][:3]

                    for rank, index in enumerate(top_indices):
                        label = model.classes_[index]
                        confidence = probabilities[index]

                        text = (
                            f"{rank + 1}. {label}: "
                            f"{confidence:.2f}"
                        )

                        cv2.putText(
                            frame,
                            text,
                            (20, 45 + rank * 40),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            (0, 255, 0),
                            2,
                        )

                else:
                    cv2.putText(
                        frame,
                        "NO HAND DETECTED",
                        (20, 45),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 200, 255),
                        2,
                    )

                cv2.imshow(
                    "SignBridge AI - YOU Diagnostic",
                    frame,
                )

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
