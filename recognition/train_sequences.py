"""Train an experimental sequence classifier; does not replace sign_model.joblib."""
from collections import Counter
from pathlib import Path
import argparse
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import GroupShuffleSplit

ROOT = Path(__file__).resolve().parents[1]


def train(data, output):
    xs, ys, groups = [], [], []
    for file in sorted(data.glob('*/*.npz')):
        with np.load(file) as item:
            features = item['features']
            if features.shape != (24, 132):
                print('Skipping incompatible file:', file)
                continue
            session = str(item['session'].item())
        xs.append(features.reshape(-1))
        ys.append(file.parent.name)
        groups.append(session)
    if len(set(ys)) < 2:
        raise ValueError('Collect at least two different signs first.')
    print('Sequences by sign:', dict(Counter(ys)))
    x, y, group = np.asarray(xs), np.asarray(ys), np.asarray(groups)
    model = RandomForestClassifier(n_estimators=300, class_weight='balanced', random_state=42, n_jobs=-1)
    if len(set(groups)) >= 2:
        splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
        train_idx, test_idx = next(splitter.split(x, y, group))
        if set(y[train_idx]) == set(y) and set(y[test_idx]) == set(y):
            check_model = RandomForestClassifier(n_estimators=300, class_weight='balanced', random_state=42, n_jobs=-1)
            check_model.fit(x[train_idx], y[train_idx])
            predictions = check_model.predict(x[test_idx])
            print(f'HELD-OUT SESSION accuracy: {accuracy_score(y[test_idx], predictions):.3f}')
            print(classification_report(y[test_idx], predictions, zero_division=0))
        else:
            print('WARNING: Session split omitted some signs; collect every sign in more independent sessions.')
    else:
        print('WARNING: Only one session; cannot measure independent-session accuracy yet.')
    model.fit(x, y)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output)
    print('Experimental model saved:', output)
    print('This model is NOT connected to the live webcam yet.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=ROOT / 'data' / 'sequences')
    parser.add_argument('--output', type=Path, default=ROOT / 'models' / 'sequence_model.joblib')
    args = parser.parse_args()
    train(args.data, args.output)
