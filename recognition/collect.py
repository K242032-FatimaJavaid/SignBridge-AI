
"""Collect webcam hand-landmark examples for SignBridge AI."""

import argparse
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from recognition.features import vectorize_hands, hands_present


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

SUPPORTED_SIGNS = [
    "HELLO",
    "YES",
    "NO",
    "HELP",
    "THANK_YOU",
    "I",
    "YOU",
    "NEED",
    "WANT",
    "WATER",
    "FOOD",
    "PLEASE",
    "MY",
    "NAME",
    "IS",
    "TO",
    "AGE",
    "SHUT_UP",
    "QUIET",
]


def collect(label, count=150, camera=0):
    label = label.upper().strip()

    if label not in SUPPORTED_SIGNS:
        raise ValueError(
            f"Unsupported sign: {label}\n"
            f"Available signs: {', '.join(SUPPORTED_SIGNS)}"
        )

    if count <= 0:
        raise ValueError("Count must be greater than zero.")

    path = DATA_DIR / f"{label}.npz"

    samples = []

    if path.exists():
        with np.load(path) as old:
            samples = list(old["features"])

    start_count = len(samples)

    print(f"\nCollecting sign: {label}")
    print(f"Existing samples: {start_count}")
    print(f"New samples requested: {count}")
    print("SPACE = Start/Pause recording")
    print("Q = Save and quit\n")

    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

    if not cap.isOpened():
        raise RuntimeError("Cannot access camera.")

    mp_hands = mp.solutions.hands

    recording = False

    try:
        with mp_hands.Hands(
            max_num_hands=2,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        ) as hands:

            while len(samples) - start_count < count:

                ok, frame = cap.read()

                if not ok:
                    print("Could not read webcam frame.")
                    break

                frame = cv2.flip(frame, 1)

                rgb = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2RGB
                )

                result = hands.process(rgb)

                if recording and hands_present(result):
                    features = vectorize_hands(result)
                    samples.append(features)

                # Draw detected hand landmarks
                if result.multi_hand_landmarks:
                    for landmarks in result.multi_hand_landmarks:
                        mp.solutions.drawing_utils.draw_landmarks(
                            frame,
                            landmarks,
                            mp_hands.HAND_CONNECTIONS
                        )

                new_count = len(samples) - start_count

                status = (
                    "RECORDING"
                    if recording
                    else "PAUSED"
                )

                color = (
                    (0, 255, 0)
                    if recording
                    else (0, 200, 255)
                )

                cv2.putText(
                    frame,
                    f"SIGN: {label}",
                    (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 255, 255),
                    2
                )

                cv2.putText(
                    frame,
                    f"{status}: {new_count}/{count}",
                    (10, 75),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    color,
                    2
                )

                cv2.putText(
                    frame,
                    "SPACE: Record/Pause | Q: Save & Quit",
                    (10, 115),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 255),
                    2
                )

                cv2.imshow(
                    "SignBridge AI - ASL Data Collection",
                    frame
                )

                key = cv2.waitKey(1) & 0xFF

                if key == ord(" "):
                    recording = not recording

                elif key == ord("q"):
                    break

    finally:
        cap.release()
        cv2.destroyAllWindows()

        if len(samples) > start_count:
            DATA_DIR.mkdir(parents=True, exist_ok=True)

            np.savez_compressed(
                path,
                features=np.asarray(
                    samples,
                    dtype=np.float32
                )
            )

            print(
                f"\nSaved {len(samples)} total samples "
                f"to {path}"
            )

        else:
            print("\nNo new samples recorded.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--label",
        required=True,
        choices=SUPPORTED_SIGNS,
        type=str.upper,
    )

    parser.add_argument(
        "--count",
        type=int,
        default=150,
    )

    parser.add_argument(
        "--camera",
        type=int,
        default=0,
    )

    args = parser.parse_args()

    collect(
        label=args.label,
        count=args.count,
        camera=args.camera,
    )
