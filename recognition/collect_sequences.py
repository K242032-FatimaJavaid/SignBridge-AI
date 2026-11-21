"""Collect complete sign repetitions without changing legacy data/*.npz files.

Run: python -m recognition.collect_sequences --label PLEASE --count 25 --session day1
SPACE starts one repetition; recording captures 24 consecutive valid frames.
"""
import argparse
from datetime import datetime
from pathlib import Path
import cv2
import mediapipe as mp
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'sequences'
FRAMES = 24
LABELS = ['HELLO','YES','NO','HELP','THANK_YOU','I','YOU','NEED','WANT','WATER','FOOD','PLEASE','MY','NAME','IS','TO','AGE','SHUT_UP','QUIET']


def sequence_features(results):
    """Wrist-relative handshape + absolute wrist locations, sorted left-to-right."""
    hands = []
    for hand in (results.multi_hand_landmarks or []):
        coords = np.asarray([[p.x, p.y, p.z] for p in hand.landmark], dtype=np.float32)
        wrist = coords[0].copy()
        relative = coords - wrist
        scale = max(float(np.max(np.linalg.norm(relative[:, :2], axis=1))), 1e-6)
        hands.append((float(wrist[0]), np.concatenate([ (relative / scale).ravel(), wrist])))
    hands.sort(key=lambda h: h[0])
    arrays = [item[1] for item in hands[:2]]
    while len(arrays) < 2:
        arrays.append(np.zeros(66, dtype=np.float32))
    return np.concatenate(arrays).astype(np.float32)


def collect(label, count, session, camera):
    target = OUT / label
    target.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(camera)
    if not cap.isOpened():
        raise RuntimeError('Could not open webcam')
    recorded = 0
    frames = []
    active = False
    mp_hands = mp.solutions.hands
    try:
        with mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.6, min_tracking_confidence=0.5) as hands:
            while recorded < count:
                ok, image = cap.read()
                if not ok:
                    break
                image = cv2.flip(image, 1)
                result = hands.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                visible = bool(result.multi_hand_landmarks)
                if active:
                    if visible:
                        frames.append(sequence_features(result))
                        if len(frames) == FRAMES:
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                            filename = target / f'{session}_{timestamp}.npz'
                            np.savez_compressed(filename, features=np.stack(frames), session=np.array(session))
                            recorded += 1
                            frames = []
                            active = False
                            print(f'Saved {recorded}/{count}: {filename.name}')
                    else:
                        frames = []
                        active = False
                        print('Hand lost: repetition discarded; try again')
                status = f'{label} | {recorded}/{count} | {len(frames)}/{FRAMES} frames'
                cv2.putText(image, status, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(image, 'SPACE: start ONE complete gesture | Q: quit', (12, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
                cv2.imshow('SignBridge - Sequence Collection', image)
                key = cv2.waitKey(1) & 0xFF
                if key == ord(' ') and not active:
                    frames = []
                    active = True
                elif key == ord('q'):
                    break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    print(f'Finished: saved {recorded} complete repetitions in {target}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True, type=str.upper, choices=LABELS)
    parser.add_argument('--count', type=int, default=25)
    parser.add_argument('--session', required=True, help='Use a new session name for each recording session, e.g. day1, day2')
    parser.add_argument('--camera', type=int, default=0)
    args = parser.parse_args()
    if args.count < 1:
        parser.error('--count must be positive')
    collect(args.label, args.count, args.session, args.camera)
