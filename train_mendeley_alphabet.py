
from pathlib import Path
from collections import deque
import argparse

import cv2
import joblib
import mediapipe as mp
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score


ROOT = Path(__file__).resolve().parent

DATASET = (
    ROOT / "datasets"
    / "ASL_Raw_Extracted"
    / "asl_dataset"
)

MODEL_PATH = (
    ROOT / "models"
    / "alphabet_static_mendeley_v1.joblib"
)

CACHE_DIR = ROOT / "data_alnum" / "mendeley_cache"

# J and Z require movement, so we will
# train those using video sequences later.
LETTERS = [
    letter for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if letter not in ("J", "Z")
]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def make_features(results):
    """Convert one MediaPipe hand into 63 features."""

    if not results.multi_hand_landmarks:
        return None

    landmarks = results.multi_hand_landmarks[0].landmark

    points = np.array(
        [[p.x, p.y, p.z] for p in landmarks],
        dtype=np.float32,
    )

    # Use the wrist as the coordinate origin.
    points -= points[0].copy()

    # Normalize for hand size and camera distance.
    palm_width = np.linalg.norm(
        points[5, :2] - points[17, :2]
    )

    if palm_width < 0.015:
        return None

    points /= palm_width

    return points.reshape(-1)


def prepare_image(image):
    """Resize without distorting the image."""

    height, width = image.shape[:2]

    longest_side = max(height, width)

    if longest_side > 800:
        scale = 800 / longest_side

        image = cv2.resize(
            image,
            (
                int(width * scale),
                int(height * scale),
            ),
        )

    return image


def build_dataset(per_class):
    if not DATASET.is_dir():
        raise RuntimeError(
            f"Dataset folder not found:\n{DATASET}"
        )

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cache = CACHE_DIR / f"static_{per_class}.npz"

    if cache.exists():
        print("Loading cached features:", cache)

        with np.load(cache) as saved:
            return saved["X"], saved["y"]

    X = []
    y = []

    hands_api = mp.solutions.hands

    print("\nEXTRACTING MEDIAPIPE LANDMARKS")
    print("Dataset:", DATASET)
    print("Classes:", len(LETTERS))

    rng = np.random.default_rng(42)

    with hands_api.Hands(
        static_image_mode=True,
        max_num_hands=1,
        model_complexity=1,
        min_detection_confidence=0.5,
    ) as hands:

        for label in LETTERS:
            folder = DATASET / label

            if not folder.is_dir():
                raise RuntimeError(
                    f"Missing class folder: {folder}"
                )

            images = sorted(
                p for p in folder.iterdir()
                if p.is_file()
                and p.suffix.lower() in IMAGE_EXTENSIONS
            )

            if not images:
                raise RuntimeError(
                    f"No images found for {label}"
                )

            sample_size = min(per_class, len(images))

            indices = rng.choice(
                len(images),
                size=sample_size,
                replace=False,
            )

            success = 0

            for index in indices:
                path = images[int(index)]

                image = cv2.imread(str(path))

                if image is None:
                    continue

                image = prepare_image(image)

                rgb = cv2.cvtColor(
                    image,
                    cv2.COLOR_BGR2RGB,
                )

                results = hands.process(rgb)

                features = make_features(results)

                # Retry horizontally flipped if detection fails.
                if features is None:
                    flipped = cv2.flip(rgb, 1)
                    results = hands.process(flipped)
                    features = make_features(results)

                if features is None:
                    continue

                X.append(features)
                y.append(label)
                success += 1

            print(
                f"{label}: {success}/{sample_size} "
                "images processed",
                flush=True,
            )

    X = np.asarray(X, dtype=np.float32)
    y = np.asarray(y)

    if len(X) == 0:
        raise RuntimeError(
            "MediaPipe could not detect any hands."
        )

    counts = {
        label: int(np.sum(y == label))
        for label in LETTERS
    }

    insufficient = [
        label for label, count in counts.items()
        if count < 30
    ]

    if insufficient:
        raise RuntimeError(
            "Insufficient detected images for: "
            + ", ".join(insufficient)
        )

    np.savez_compressed(cache, X=X, y=y)

    print("\nFeature cache saved:", cache)
    print("Total usable images:", len(X))

    return X, y


def train(per_class):
    X, y = build_dataset(per_class)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    # Mirror training samples to better support
    # right-handed and left-handed camera views.
    mirrored = X_train.copy()

    mirrored[:, 0::3] *= -1

    X_augmented = np.concatenate(
        [X_train, mirrored],
        axis=0,
    )

    y_augmented = np.concatenate(
        [y_train, y_train],
        axis=0,
    )

    model = RandomForestClassifier(
        n_estimators=200,
        min_samples_leaf=2,
        max_features="sqrt",
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=42,
    )

    print("\nTraining alphabet classifier...")

    model.fit(X_augmented, y_augmented)

    predictions = model.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)

    print("\nHELD-OUT IMAGE RESULTS")
    print(f"Accuracy: {accuracy:.2%}")

    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0,
        )
    )

    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if MODEL_PATH.exists():
        raise RuntimeError(
            "Model already exists. "
            "Rename or back up the existing file "
            "before retraining."
        )

    joblib.dump(
        {
            "model": model,
            "labels": LETTERS,
            "feature_type": "static_mediapipe_63",
            "validation_accuracy": float(accuracy),
        },
        MODEL_PATH,
    )

    print("\nALPHABET MODEL SAVED")
    print(MODEL_PATH)
    print(
        "\nNext: Test against your own webcam."
    )


def open_camera(index):
    cap = cv2.VideoCapture(
        index,
        cv2.CAP_DSHOW,
    )

    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(index)

    if not cap.isOpened():
        raise RuntimeError(
            f"Could not open camera {index}"
        )

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

    return cap


def test(camera_index):
    if not MODEL_PATH.exists():
        raise RuntimeError(
            "Train the alphabet model first."
        )

    saved = joblib.load(MODEL_PATH)
    model = saved["model"]

    cap = open_camera(camera_index)

    votes = deque(maxlen=6)
    last_label = "SHOW A LETTER"
    confirmed = ""

    frame_count = 0

    print("\nLIVE ALPHABET TEST")
    print("Show a letter and hold your hand steady.")
    print("Press ESC to exit.")
    print("J and Z are not trained yet.")

    try:
        with mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        ) as hands:

            while True:
                ok, frame = cap.read()

                if not ok:
                    break

                frame = cv2.flip(frame, 1)

                frame_count += 1

                if frame_count % 3 == 0:
                    image = prepare_image(frame)

                    rgb = cv2.cvtColor(
                        image,
                        cv2.COLOR_BGR2RGB,
                    )

                    results = hands.process(rgb)

                    features = make_features(results)

                    if features is None:
                        votes.clear()
                        last_label = "NO HAND"
                        confirmed = ""

                    else:
                        probabilities = model.predict_proba(
                            features.reshape(1, -1)
                        )[0]

                        ranking = np.argsort(
                            probabilities
                        )[::-1]

                        first = int(ranking[0])
                        second = int(ranking[1])

                        label = str(
                            model.classes_[first]
                        )

                        confidence = float(
                            probabilities[first]
                        )

                        margin = confidence - float(
                            probabilities[second]
                        )

                        last_label = (
                            f"POSSIBLE {label}: "
                            f"{confidence:.2f}"
                        )

                        if (
                            confidence >= 0.55
                            and margin >= 0.12
                        ):
                            votes.append(label)

                        else:
                            votes.append(None)

                        if (
                            len(votes) == votes.maxlen
                            and len(set(votes)) == 1
                            and votes[0] is not None
                        ):
                            confirmed = label

                cv2.putText(
                    frame,
                    last_label,
                    (15, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (0, 255, 255),
                    2,
                )

                if confirmed:
                    cv2.putText(
                        frame,
                        f"STABLE: {confirmed}",
                        (15, 75),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.9,
                        (0, 255, 0),
                        2,
                    )

                cv2.putText(
                    frame,
                    "ESC: EXIT | 24 STATIC LETTERS",
                    (15, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 255),
                    2,
                )

                cv2.imshow(
                    "SignBridge Alphabet Test",
                    frame,
                )

                if cv2.waitKey(1) & 0xFF == 27:
                    break

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
        "--per-class",
        type=int,
        default=250,
    )

    parser.add_argument(
        "--camera",
        type=int,
        default=1,
    )

    args = parser.parse_args()

    if args.action == "train":
        train(args.per_class)

    else:
        test(args.camera)


if __name__ == "__main__":
    main()
