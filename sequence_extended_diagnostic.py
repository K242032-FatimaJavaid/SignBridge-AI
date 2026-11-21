
from pathlib import Path
from datetime import datetime
import argparse
import time

import cv2
import joblib
import mediapipe as mp
import numpy as np

from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import classification_report, confusion_matrix

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data_sequences_full"
MODEL = ROOT / "models" / "sequence_extended_v1.joblib"

LENGTH = 24
FPS = 12
PROCESS_SIZE = (640, 360)
LABELS = ('AGE', 'FOOD', 'HELLO', 'HELP', 'I', 'IS', 'MY', 'NAME', 'NEED', 'NO', 'PLEASE', 'QUIET', 'SHUT_UP', 'THANK_YOU', 'TO', 'WANT', 'WATER', 'YES', 'YOU', 'GOODBYE', 'STOP', 'YOU_ARE_WELCOME', 'WHAT', 'FRIEND', 'CLAP', 'OTHER')


def extract_features(results):
    """Fixed left/right slots, handshape and wrist position."""
    features = np.zeros((2, 66), dtype=np.float32)

    landmarks = results.multi_hand_landmarks or []
    handedness = results.multi_handedness or []

    for hand, hand_info in zip(landmarks, handedness):
        side = hand_info.classification[0].label
        index = 0 if side == "Left" else 1

        coords = np.asarray(
            [[p.x, p.y, p.z] for p in hand.landmark],
            dtype=np.float32
        )

        wrist = coords[0].copy()
        relative = coords - wrist

        scale = max(
            float(np.max(np.linalg.norm(relative[:, :2], axis=1))),
            1e-6
        )

        features[index] = np.concatenate([
            (relative / scale).reshape(-1),
            wrist[:2],
            np.array([1.0], dtype=np.float32)
        ])

    return features.reshape(-1)


def temporal_features(clip):
    """Capture handshape, location and changes over time."""
    clip = np.asarray(clip, dtype=np.float32)

    if clip.shape != (LENGTH, 132):
        raise ValueError(f"Incorrect clip shape: {clip.shape}")

    # Reduce noise while retaining the order of movement.
    smooth = (clip[::2] + clip[1::2]) / 2

    # Wrist coordinates are at these positions.
    wrists = smooth[:, [63, 64, 129, 130]]
    movement = np.diff(wrists, axis=0)

    return np.concatenate([
        smooth.reshape(-1),
        movement.reshape(-1),
        clip.mean(axis=0),
        clip.std(axis=0)
    ]).astype(np.float32)


def open_camera(index):
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)

    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(index)

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open webcam {index}")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def run_camera(mode, camera, label=None, session=None, clips=20):
    if mode == "test" and not MODEL.exists():
        raise SystemExit("Train the pilot model first.")

    model = joblib.load(MODEL) if mode == "test" else None
    cap = open_camera(camera)

    recording = False
    samples = []
    saved = 0
    next_sample = 0.0
    message = "Press SPACE to record a 2-second sign"

    if mode == "collect":
        folder = DATA / label
        folder.mkdir(parents=True, exist_ok=True)

    try:
        with mp.solutions.hands.Hands(
            max_num_hands=2,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5
        ) as hands:

            while True:
                ok, frame = cap.read()
                if not ok:
                    break

                frame = cv2.flip(frame, 1)
                now = time.monotonic()

                if recording and now >= next_sample:
                    small = cv2.resize(
                        frame, PROCESS_SIZE,
                        interpolation=cv2.INTER_AREA
                    )
                    rgb = cv2.cvtColor(
                        small, cv2.COLOR_BGR2RGB
                    )

                    results = hands.process(rgb)
                    samples.append(extract_features(results))
                    next_sample = now + 1.0 / FPS

                    if len(samples) == LENGTH:
                        clip = np.asarray(
                            samples, dtype=np.float32
                        )
                        recording = False

                        # Require visible hands in most of the clip.
                        visible = np.count_nonzero(
                            np.any(
                                clip[:, [65, 131]] > 0.5,
                                axis=1
                            )
                        )

                        if visible < 18:
                            message = (
                                "Clip discarded: hand not detected "
                                "often enough"
                            )
                        elif mode == "collect":
                            stamp = datetime.now().strftime(
                                "%Y%m%d_%H%M%S_%f"
                            )
                            path = folder / f"{session}_{stamp}.npz"

                            np.savez_compressed(
                                path,
                                clip=clip,
                                label=label,
                                session=session
                            )

                            saved += 1
                            message = (
                                f"Saved {saved}/{clips} "
                                f"clips of {label}"
                            )
                        else:
                            x = temporal_features(clip)
                            probabilities = model.predict_proba(
                                x.reshape(1, -1)
                            )[0]

                            ranking = np.argsort(
                                probabilities
                            )[::-1]

                            best = ranking[0]
                            second = ranking[1]

                            predicted = str(
                                model.classes_[best]
                            )
                            confidence = probabilities[best]
                            margin = (
                                probabilities[best]
                                - probabilities[second]
                            )

                            top3 = " | ".join(
                                f"{model.classes_[idx]}: {probabilities[idx]:.1%}"
                                for idx in ranking[:3]
                            )

                            print(
                                f"TOP 3: {top3} | Margin: {margin:.1%}",
                                flush=True
                            )

                            required_conf = {"CLAP": 0.35, "STOP": 0.45}.get(predicted, 0.60)
                            required_margin = {"CLAP": 0.20, "STOP": 0.13}.get(predicted, 0.15)

                            if confidence < required_conf or margin < required_margin:
                                predicted = "UNCERTAIN"

                            message = (
                                f"{predicted} "
                                f"({confidence:.2f})"
                            )

                        samples = []

                preview = cv2.resize(frame, (960, 540))

                title = (
                    f"COLLECT: {label} | SESSION: {session}"
                    if mode == "collect"
                    else "SEQUENCE MODEL - LIVE TEST"
                )

                lines = [
                    title,
                    (
                        f"RECORDING {len(samples)}/{LENGTH}"
                        if recording else message
                    ),
                    "SPACE = Record | Q = Quit"
                ]

                for i, line in enumerate(lines):
                    cv2.putText(
                        preview, line,
                        (15, 40 + i * 45),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 255, 0), 2
                    )

                cv2.imshow(
                    "SignBridge Sequence Pilot", preview
                )

                key = cv2.waitKey(1) & 0xFF

                if key == ord("q"):
                    break

                if key == 32 and not recording:
                    samples = []
                    recording = True
                    next_sample = 0.0
                    message = "Recording..."

                if mode == "collect" and saved >= clips:
                    print(f"Collected {saved} clips for {label}")
                    break

    finally:
        cap.release()
        cv2.destroyAllWindows()


def train():
    x, y, groups = [], [], []

    for file in sorted(DATA.glob("*/*.npz")):
        with np.load(file) as item:
            clip = item["clip"]
            label = str(item["label"])
            session = str(item["session"])

        x.append(temporal_features(clip))
        y.append(label)
        groups.append(session)

    if not x:
        raise SystemExit("No sequence recordings found.")

    x = np.asarray(x)
    y = np.asarray(y)
    groups = np.asarray(groups)

    print("Total clips:", len(x))
    print("Classes:", sorted(set(y)))
    print("Sessions:", sorted(set(groups)))

    if set(y) != set(LABELS):
        raise SystemExit(
            "Collect all 19 signs and OTHER before training."
        )

    if len(set(groups)) < 3:
        raise SystemExit(
            "Collect at least three separate sessions."
        )

    # Entire sessions are held out, not random frames.
    splitter = GroupShuffleSplit(
        n_splits=40,
        test_size=0.33,
        random_state=42
    )

    split = None
    for a, b in splitter.split(x, y, groups):
        if set(y[a]) == set(LABELS) and set(y[b]) == set(LABELS):
            split = (a, b)
            break

    if split is None:
        raise SystemExit(
            "Every class must be recorded in multiple sessions."
        )

    train_idx, test_idx = split

    model = make_pipeline(
        StandardScaler(),
        SVC(
            kernel="rbf",
            C=3.0,
            gamma="scale",
            class_weight="balanced",
            probability=True,
            random_state=42
        )
    )

    model.fit(x[train_idx], y[train_idx])
    predictions = model.predict(x[test_idx])

    print("\n=== UNSEEN SESSION RESULTS ===")
    print("Training sessions:", set(groups[train_idx]))
    print("Test sessions:", set(groups[test_idx]))

    print(classification_report(
        y[test_idx],
        predictions,
        labels=LABELS,
        zero_division=0
    ))

    print("Confusion matrix:")
    print(confusion_matrix(
        y[test_idx],
        predictions,
        labels=LABELS
    ))

    # Save this pilot separately, without overwriting
    # the existing 19-sign model.
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL)

    print("Saved experimental model:", MODEL)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "mode", choices=["collect", "train", "test"]
    )
    parser.add_argument(
        "--label", choices=LABELS
    )
    parser.add_argument(
        "--session"
    )
    parser.add_argument(
        "--clips", type=int, default=20
    )
    parser.add_argument(
        "--camera", type=int, default=1
    )

    args = parser.parse_args()

    if args.mode == "collect":
        if not args.label or not args.session:
            parser.error(
                "collect requires --label and --session"
            )
        run_camera(
            "collect", args.camera,
            args.label, args.session, args.clips
        )

    elif args.mode == "train":
        train()

    else:
        run_camera("test", args.camera)
