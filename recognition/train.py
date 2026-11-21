"""Train a simple landmark-based isolated-sign classifier."""
import argparse
from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]


def train(data_dir=ROOT / 'data', output=ROOT / 'models' / 'sign_model.joblib'):
    files = sorted(Path(data_dir).glob('*.npz'))
    if not files:
        raise ValueError('No samples found. Run collect.py for at least two signs.')
    xs, ys = [], []
    for file in files:
        with np.load(file) as d:
            x = d['features']
            if x.ndim != 2 or x.shape[1] != 126:
                raise ValueError(f'Invalid features in {file}')
            xs.extend(x)
            ys.extend([file.stem.upper()] * len(x))
    if len(set(ys)) < 2:
        raise ValueError('Collect at least two different sign labels.')
    if min(ys.count(label) for label in set(ys)) < 5:
        raise ValueError('Collect at least five samples for every label.')
    x = np.asarray(xs)
    y = np.asarray(ys)
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.25, random_state=42, stratify=y
    )
    clf = RandomForestClassifier(n_estimators=150, random_state=42, class_weight='balanced')
    clf.fit(x_train, y_train)
    preds = clf.predict(x_test)
    print(f'Holdout frame accuracy: {accuracy_score(y_test, preds):.3f}')
    print(classification_report(y_test, preds, zero_division=0))
    print('WARNING: This is a random FRAME split, not signer-independent evaluation.')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, output)
    print('Saved:', output)
    return clf


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default=str(ROOT / 'data'))
    parser.add_argument('--output', default=str(ROOT / 'models' / 'sign_model.joblib'))
    args = parser.parse_args()
    train(args.data, args.output)
