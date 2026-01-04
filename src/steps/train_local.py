import os
import json
import joblib
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, average_precision_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def main():
    # Onde estão os dados 
    train_path = "../data/splits/train.csv"
    val_path = "../data/splits/val.csv"

    if not os.path.exists(train_path):
        raise FileNotFoundError(f"Não encontrei {train_path}. Corre primeiro o split_data.py")
    if not os.path.exists(val_path):
        raise FileNotFoundError(f"Não encontrei {val_path}. Corre primeiro o split_data.py")

    # Ler CSVs
    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)

    # Definir o alvo
    TARGET = "Class"
    if TARGET not in train_df.columns:
        raise ValueError(f"Não encontrei a coluna alvo '{TARGET}' no treino.")
    if TARGET not in val_df.columns:
        raise ValueError(f"Não encontrei a coluna alvo '{TARGET}' na validação.")

    # Separar X (inputs) e y (target)
    X_train = train_df.drop(columns=[TARGET])
    y_train = train_df[TARGET]

    X_val = val_df.drop(columns=[TARGET])
    y_val = val_df[TARGET]

    # Criar o modelo (baseline simples e rápido)
    # class_weight="balanced" é importante porque só ~0.17% são fraudes.
    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                n_jobs=-1
             ))
          ]
    )

    # Treinar 
    model.fit(X_train, y_train)

    # Avaliar na validação
    y_pred = model.predict(X_val)               # devolve 0/1
    y_proba = model.predict_proba(X_val)[:, 1]  # devolve probabilidade de fraude

    f1 = f1_score(y_val, y_pred)
    pr_auc = average_precision_score(y_val, y_proba)

    # Mostrar métricas
    print("Validation metrics:")
    print(f"validation:f1={f1}")
    print(f"validation:pr_auc={pr_auc}")

    # Guardar artefactos (modelo + métricas)
    os.makedirs("artifacts", exist_ok=True)

    joblib.dump(model, "artifacts/model.joblib")

    metrics = {
        "f1": float(f1),
        "pr_auc": float(pr_auc),
        "model": "LogisticRegression",
        "max_iter": 300,
        "class_weight": "balanced"
    }
    with open("artifacts/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print("Artefactos guardados:")
    print(" - artifacts/model.joblib")
    print(" - artifacts/metrics.json")


if __name__ == "__main__":
    main()