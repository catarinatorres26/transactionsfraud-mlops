import argparse
import os
import joblib
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline


def parse_args():
    parser = argparse.ArgumentParser()

    # aceitar -C e --C
    parser.add_argument("-C", "--C", type=float, default=1.0)
    parser.add_argument("--max_iter", type=int, default=1000)

    parser.add_argument("--train", type=str, default="/opt/ml/input/data/train")
    parser.add_argument("--validation", type=str, default="/opt/ml/input/data/validation")
    parser.add_argument("--model-dir", type=str, default=os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))

    return parser.parse_args()


def load_channel_csv(channel_dir: str) -> pd.DataFrame:
    files = [f for f in os.listdir(channel_dir) if f.endswith(".csv")]
    if not files:
        raise FileNotFoundError(f"Nenhum CSV encontrado em {channel_dir}")
    return pd.read_csv(os.path.join(channel_dir, files[0]))


def main():
    args = parse_args()

    train_df = load_channel_csv(args.train)
    val_df = load_channel_csv(args.validation)

    # TARGET FIXO PARA ESTE DATASET
    target_col = "Class"

    X_train = train_df.drop(columns=[target_col])
    y_train = train_df[target_col]

    X_val = val_df.drop(columns=[target_col])
    y_val = val_df[target_col]

    model = Pipeline(steps=[
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(
            C=args.C,
            max_iter=args.max_iter,
            solver="lbfgs",
            class_weight="balanced",  # MUITO IMPORTANTE PARA FRAUDE
        ))
    ])

    model.fit(X_train, y_train)

    # Métricas
    y_val_proba = model.predict_proba(X_val)[:, 1]
    pr_auc = average_precision_score(y_val, y_val_proba)

    y_val_pred = (y_val_proba >= 0.5).astype(int)
    f1 = f1_score(y_val, y_val_pred)

    # O SageMaker HPO VAI LER ISTO DO LOG
    print(f"validation:pr_auc={pr_auc:.6f}")
    print(f"validation:f1={f1:.6f}")

    os.makedirs(args.model_dir, exist_ok=True)
    joblib.dump(model, os.path.join(args.model_dir, "model.joblib"))


if __name__ == "__main__":
    main()


