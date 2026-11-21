"""Extract normalized hand landmarks from MediaPipe's classic Hands API."""
import numpy as np

FEATURE_COUNT = 126  # 2 hands x 21 landmarks x xyz


def vectorize_hands(results):
    """Return stable, wrist-centered hand features, padded for missing hands."""
    hands = []
    if results.multi_hand_landmarks:
        for hand in results.multi_hand_landmarks[:2]:
            coords = np.array([[p.x, p.y, p.z] for p in hand.landmark], dtype=np.float32)
            coords -= coords[0]  # remove translation
            scale = max(float(np.max(np.linalg.norm(coords[:, :2], axis=1))), 1e-6)
            hands.append((coords / scale).reshape(-1))
    # Consistent ordering by handedness when available; left/right ambiguity
    # is reduced by collecting samples with the same signing hand setup.
    while len(hands) < 2:
        hands.append(np.zeros(63, dtype=np.float32))
    return np.concatenate(hands).astype(np.float32)


def hands_present(results):
    return bool(results.multi_hand_landmarks)
