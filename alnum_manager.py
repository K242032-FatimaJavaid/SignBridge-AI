
from pathlib import Path
from collections import Counter
import argparse
import time

import cv2
import joblib
import mediapipe as mp
import numpy as np

from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import classification_report, accuracy_score

# Reuse the SAME feature extraction as your working
# 19-sign sequence model.
from sequence_full import extract_features, temporal_features, LENGTH
from recognition.features import hands_present


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data_alnum"
MODELS = ROOT / "models"

LABELS = {
    "alphabet": list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ["OTHER"],
    "numbers": list("0123456789") + ["OTHER"],
}

SESSIONS = ("S1", "S2", "S3")
FPS = 12
FRAME_SIZE = (640, 360)


def model_path(mode):
    return MODELS / f"alnum_{mode}_v1.joblib"


def data_folder(mode, label):
    return DATA / mode / label


def count_clips(mode, label, session):
    folder = data_folder(mode, label)
    return len(list(folder.glob(f"{session}_*.npz")))


def progress(mode):
    print(f"\n{mode.upper()} DATA COLLECTION")
    print(f"{'LABEL':<10} {'S1':>5} {'S2':>5} {'S3':>5}")

    total = 0

    for label in LABELS[mode]:
        counts = [
            count_clips(mode, label, s)
            for s in SESSIONS
        ]
        total += sum(counts)

        print(
            f"{label:<10}"
            f"{counts[0]:>5}"
            f"{counts[1]:>5}"
            f"{counts[2]:>5}"
        )

    print(f"\nTotal clips: {total}")


def open_camera(index):
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)

    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(index)

    if not cap.isOpened():
        raise RuntimeError(f"Camera {index} could not open.")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

    return cap


def get_frame(cap):
    ok, frame = cap.read()

    if not ok:
        raise RuntimeError("Camera frame unavailable.")

    frame = cv2.resize(frame, FRAME_SIZE)
    frame = cv2.flip(frame, 1)

    return frame


def draw(frame, lines):
    image = frame.copy()

    for i, line in enumerate(lines):
        cv2.putText(
            image,
            str(line),
            (12, 30 + i * 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.60,
            (0, 255, 255),
            2,
        )

    return image


def capture_clip(cap, hands):
    frames = []
    visible = 0

    for i in range(LENGTH):
        started = time.perf_counter()

        frame = get_frame(cap)

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB,
        )

        result = hands.process(rgb)

        if hands_present(result):
            visible += 1

        frames.append(extract_features(result))

        view = draw(
            frame,
            [
                f"RECORDING {i + 1}/{LENGTH}",
                "Keep the complete sign visible",
                "ESC: stop",
            ],
        )

        cv2.imshow("SignBridge Alphanumeric", view)

        if cv2.waitKey(1) & 0xFF == 27:
            raise KeyboardInterrupt

        remaining = (
            1.0 / FPS
            - (time.perf_counter() - started)
        )

        if remaining > 0:
            time.sleep(remaining)

    data = np.asarray(frames, dtype=np.float32)

    # Reject clips containing too many missing-hand frames.
    if visible < int(LENGTH * 0.85):
        print(
            "Clip rejected: hands were not visible "
            "throughout enough of the recording."
        )
        return None

    return data


def collect(args):
    labels = LABELS[args.mode]
    cap = open_camera(args.camera)

    hands_api = mp.solutions.hands

    print("\nDATA COLLECTION")
    print("SPACE = Record one complete sign")
    print("N = Skip current label")
    print("ESC = Exit and save progress")
    print("J and Z: perform their full movements.")
    print("OTHER: perform gestures outside this mode.")

    try:
        with hands_api.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=0,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        ) as hands:

            for label in labels:
                folder = data_folder(args.mode, label)
                folder.mkdir(parents=True, exist_ok=True)

                while True:
                    done = count_clips(
                        args.mode,
                        label,
                        args.session,
                    )

                    if done >= args.clips:
                        print(f"Completed {label}: {done} clips")
                        break

                    frame = get_frame(cap)

                    view = draw(
                        frame,
                        [
                            f"MODE: {args.mode.upper()}",
                            f"LABEL: {label}",
                            f"SESSION: {args.session}",
                            f"CLIPS: {done}/{args.clips}",
                            "SPACE record | N next | ESC exit",
                        ],
                    )

                    cv2.imshow(
                        "SignBridge Alphanumeric",
                        view,
                    )

                    key = cv2.waitKey(1) & 0xFF

                    if key == 27:
                        return

                    if key == ord("n"):
                        print(f"Skipped {label}")
                        break

                    if key != 32:
                        continue

                    print(f"Recording {label}...")

                    # Brief preparation delay.
                    time.sleep(0.7)

                    clip = capture_clip(cap, hands)

                    if clip is None:
                        continue

                    filename = (
                        f"{args.session}_"
                        f"{time.time_ns()}.npz"
                    )

                    np.savez_compressed(
                        folder / filename,
                        frames=clip,
                    )

                    print(
                        f"Saved {label}: "
                        f"{count_clips(args.mode, label, args.session)}"
                    )

    except KeyboardInterrupt:
        print("\nCollection interrupted safely.")

    finally:
        cap.release()
        cv2.destroyAllWindows()

    print("\nCollection session finished.")


def load_data(mode):
    vectors = []
    labels = []
    sessions = []

    for label in LABELS[mode]:
        folder = data_folder(mode, label)

        for session in SESSIONS:
            for path in sorted(
                folder.glob(f"{session}_*.npz")
            ):
                with np.load(path) as saved:
                    frames = saved["frames"]

                if frames.shape[0] != LENGTH:
                    raise ValueError(
                        f"Incorrect clip length: {path}"
                    )

                vector = temporal_features(
                    frames.astype(np.float32)
                )

                vectors.append(vector)
                labels.append(label)
                sessions.append(session)

    if not vectors:
        raise RuntimeError("No training clips found.")

    return (
        np.asarray(vectors, dtype=np.float32),
        np.asarray(labels),
        np.asarray(sessions),
    )


def train(mode):
    print("\nChecking training dataset...")

    missing = []

    for label in LABELS[mode]:
        for session in SESSIONS:
            count = count_clips(mode, label, session)

            if count < 5:
                missing.append(
                    f"{label} / {session}: {count} clips"
                )

    if missing:
        print("Need at least 5 clips per class per session.")
        print("Incomplete classes:")

        for item in missing:
            print(" -", item)

        return

    X, y, sessions = load_data(mode)

    training = sessions != "S3"
    testing = sessions == "S3"

    classifier = make_pipeline(
        StandardScaler(),
        SVC(
            kernel="rbf",
            C=3.0,
            gamma="scale",
            class_weight="balanced",
            probability=True,
            random_state=42,
        ),
    )

    classifier.fit(X[training], y[training])

    predictions = classifier.predict(X[testing])

    accuracy = accuracy_score(
        y[testing],
        predictions,
    )

    print("\nUNSEEN SESSION S3 RESULTS")
    print(f"Accuracy: {accuracy:.2%}")

    print(
        classification_report(
            y[testing],
            predictions,
            labels=LABELS[mode],
            zero_division=0,
        )
    )

    MODELS.mkdir(parents=True, exist_ok=True)

    output = model_path(mode)

    # Keep an existing model before replacing it.
    if output.exists():
        backup = output.with_name(
            f"{output.stem}_{time.time_ns()}_backup.joblib"
        )
        import shutil
        shutil.copy2(output, backup)
        print("Previous model backed up:", backup)

    joblib.dump(
        {
            "model": classifier,
            "mode": mode,
            "labels": LABELS[mode],
            "sequence_length": LENGTH,
            "unseen_session_accuracy": float(accuracy),
        },
        output,
    )

    print("\nModel saved:", output)
    print(
        "Review per-class recall before using "
        "the model for automatic translation."
    )


def test(args):
    path = model_path(args.mode)

    if not path.exists():
        raise SystemExit(
            f"Model missing: {path}\n"
            "Collect and train this mode first."
        )

    saved = joblib.load(path)
    model = saved["model"]

    if saved["sequence_length"] != LENGTH:
        raise SystemExit("Sequence length mismatch.")

    cap = open_camera(args.camera)

    hands_api = mp.solutions.hands

    print("\nSTANDALONE RECOGNITION TEST")
    print("SPACE = Test one complete sign")
    print("ESC = Exit")

    try:
        with hands_api.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=0,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        ) as hands:

            while True:
                frame = get_frame(cap)

                cv2.imshow(
                    "SignBridge Alphanumeric",
                    draw(
                        frame,
                        [
                            f"TEST: {args.mode.upper()}",
                            "SPACE: capture one sign",
                            "ESC: exit",
                        ],
                    ),
                )

                key = cv2.waitKey(1) & 0xFF

                if key == 27:
                    break

                if key != 32:
                    continue

                time.sleep(0.7)

                clip = capture_clip(cap, hands)

                if clip is None:
                    continue

                vector = temporal_features(clip)

                probabilities = model.predict_proba(
                    vector.reshape(1, -1)
                )[0]

                ranking = np.argsort(
                    probabilities
                )[::-1]

                print("\nTOP PREDICTIONS")

                for index in ranking[:3]:
                    print(
                        f"{model.classes_[index]}: "
                        f"{probabilities[index]:.2%}"
                    )

                first = int(ranking[0])
                second = int(ranking[1])

                confidence = float(
                    probabilities[first]
                )

                margin = confidence - float(
                    probabilities[second]
                )

                if (
                    confidence >= 0.28
                    and margin >= 0.12
                    and str(model.classes_[first]) != "OTHER"
                ):
                    print(
                        "Candidate:",
                        model.classes_[first],
                    )
                else:
                    print(
                        "UNCERTAIN — do not confirm."
                    )

    except KeyboardInterrupt:
        pass

    finally:
        cap.release()
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(
        description="SignBridge alphabet and number trainer"
    )

    parser.add_argument(
        "action",
        choices=("collect", "progress", "train", "test"),
    )

    parser.add_argument(
        "mode",
        choices=("alphabet", "numbers"),
    )

    parser.add_argument(
        "--session",
        choices=SESSIONS,
        default="S1",
    )

    parser.add_argument(
        "--clips",
        type=int,
        default=10,
    )

    parser.add_argument(
        "--camera",
        type=int,
        default=1,
    )

    args = parser.parse_args()

    if args.action == "collect":
        collect(args)

    elif args.action == "progress":
        progress(args.mode)

    elif args.action == "train":
        train(args.mode)

    elif args.action == "test":
        test(args)


if __name__ == "__main__":
    main()
