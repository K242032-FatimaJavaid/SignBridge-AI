
from pathlib import Path
from collections import deque
import argparse
import time

import cv2
import joblib
import mediapipe as mp
import numpy as np

from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import (
    accuracy_score,
    classification_report,
)

import alnum_manager as m


SPECIALIST_PATH = (
    m.ROOT / "models" / "alphabet_uv_specialist_v1.joblib"
)


def train():
    X, y, sessions = m.load_data("alphabet")

    # Use only U and V recordings.
    selected = np.isin(y, ["U", "V"])
    train_mask = selected & (sessions != "S3")
    test_mask = selected & (sessions == "S3")

    for label in ("U", "V"):
        train_count = int(
            np.sum(train_mask & (y == label))
        )
        test_count = int(
            np.sum(test_mask & (y == label))
        )

        print(
            f"{label}: {train_count} training clips, "
            f"{test_count} test clips"
        )

        if train_count < 8 or test_count < 3:
            raise SystemExit(
                "Not enough U/V recordings. "
                "Need at least 8 training clips "
                "and 3 S3 clips per class."
            )

    model = make_pipeline(
        StandardScaler(),
        SVC(
            kernel="rbf",
            C=2.0,
            gamma="scale",
            class_weight="balanced",
            probability=True,
            random_state=42,
        ),
    )

    model.fit(
        X[train_mask],
        y[train_mask],
    )

    predictions = model.predict(X[test_mask])
    actual = y[test_mask]

    accuracy = accuracy_score(actual, predictions)

    print("\nU / V HELD-OUT S3 RESULTS")
    print(f"Accuracy: {accuracy:.2%}")
    print(
        classification_report(
            actual,
            predictions,
            labels=["U", "V"],
            zero_division=0,
        )
    )

    report = classification_report(
        actual,
        predictions,
        labels=["U", "V"],
        zero_division=0,
        output_dict=True,
    )

    # Do not save an unreliable specialist.
    if (
        accuracy < 0.80
        or report["U"]["recall"] < 0.60
        or report["V"]["recall"] < 0.60
    ):
        print(
            "\nSpecialist did not pass validation."
            "\nNo model was replaced."
            "\nWe need to inspect the U/V recordings."
        )
        return

    if SPECIALIST_PATH.exists():
        raise SystemExit(
            "A specialist model already exists. "
            "Back it up before retraining."
        )

    SPECIALIST_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        {
            "model": model,
            "classes": ["U", "V"],
            "s3_accuracy": float(accuracy),
        },
        SPECIALIST_PATH,
    )

    print("\nU/V specialist saved:", SPECIALIST_PATH)
    print("Original alphabet model remains unchanged.")


def test(camera_index):
    main_path = m.model_path("alphabet")

    if not main_path.is_file():
        raise SystemExit(
            "Original alphabet model not found."
        )

    if not SPECIALIST_PATH.is_file():
        raise SystemExit(
            "U/V specialist not found. Run train first."
        )

    main_model = joblib.load(main_path)["model"]
    uv_model = joblib.load(SPECIALIST_PATH)["model"]

    cap = m.open_camera(camera_index)

    previous_r = False

    print("\nR AND U/V RECOGNITION TEST")
    print("SPACE: capture one sign")
    print("ESC: exit")
    print(
        "For R, perform two separate captures "
        "to check consistency."
    )

    try:
        with mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=0,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        ) as hands:

            while True:
                frame = m.get_frame(cap)

                view = m.draw(
                    frame,
                    [
                        "TARGETED ALPHABET TEST",
                        "Test R, U, and V",
                        "SPACE: record | ESC: exit",
                    ],
                )

                cv2.imshow(
                    "SignBridge R/U Test",
                    view,
                )

                key = cv2.waitKey(1) & 0xFF

                if key == 27:
                    break

                if key != 32:
                    continue

                time.sleep(0.7)

                clip = m.capture_clip(cap, hands)

                if clip is None:
                    previous_r = False
                    continue

                vector = m.temporal_features(clip)
                sample = vector.reshape(1, -1)

                probabilities = main_model.predict_proba(
                    sample
                )[0]

                ranking = np.argsort(
                    probabilities
                )[::-1]

                best = int(ranking[0])
                second = int(ranking[1])

                label = str(main_model.classes_[best])
                confidence = float(probabilities[best])

                margin = confidence - float(
                    probabilities[second]
                )

                print("\nMAIN MODEL")
                for index in ranking[:3]:
                    print(
                        f"{main_model.classes_[index]}: "
                        f"{probabilities[index]:.2%}"
                    )

                # R: don't automatically accept one
                # low-confidence prediction. Require
                # consistency across two captures.
                if label == "R":
                    if (
                        confidence >= 0.18
                        and margin >= 0.01
                    ):
                        if previous_r:
                            print(
                                "CONFIRMED R "
                                "(two matching captures)"
                            )
                        else:
                            print(
                                "R looks likely. "
                                "Capture R once more."
                            )

                        previous_r = True
                    else:
                        previous_r = False
                        print("R remains uncertain.")

                    continue

                previous_r = False

                # Only use the U/V specialist when
                # the main model considers them likely.
                top_three = {
                    str(main_model.classes_[i])
                    for i in ranking[:3]
                }

                if (
                    label in ("U", "V")
                    and {"U", "V"}.issubset(top_three)
                ):
                    uv_probs = uv_model.predict_proba(
                        sample
                    )[0]

                    uv_order = np.argsort(
                        uv_probs
                    )[::-1]

                    uv_best = int(uv_order[0])
                    uv_label = str(
                        uv_model.classes_[uv_best]
                    )
                    uv_confidence = float(
                        uv_probs[uv_best]
                    )

                    print("\nU/V SPECIALIST")
                    for i in uv_order:
                        print(
                            f"{uv_model.classes_[i]}: "
                            f"{uv_probs[i]:.2%}"
                        )

                    if uv_confidence >= 0.65:
                        print(
                            "SPECIALIST CANDIDATE:",
                            uv_label
                        )
                    else:
                        print(
                            "U/V still uncertain."
                        )
                else:
                    print(
                        "Main candidate:",
                        label
                        if confidence >= 0.28
                        and margin >= 0.12
                        else "UNCERTAIN"
                    )

    finally:
        cap.release()
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "action",
        choices=["train", "test"],
    )

    parser.add_argument(
        "--camera",
        type=int,
        default=1,
    )

    args = parser.parse_args()

    if args.action == "train":
        train()
    else:
        test(args.camera)


if __name__ == "__main__":
    main()
