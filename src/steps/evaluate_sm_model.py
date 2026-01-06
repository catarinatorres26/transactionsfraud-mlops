import os
import json
import argparse
import tarfile
import tempfile
from urllib.parse import urlparse

import boto3
import joblib
import pandas as pd
from sklearn.metrics import f1_score, average_precision_score


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model_tar_s3", type=str, required=True,
                   help="S3 URI do model.tar.gz do SageMaker (estimator.model_data)")
    p.add_argument("--test_s3", type=str, required=True,
                   help="S3 URI do test.csv")
    return p.parse_args()


def download_s3_to_file(s3_uri: str, local_path: str):
    parsed = urlparse(s3_uri)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")
    s3 = boto3.client("s3")
    s3.download_file(bucket, key, local_path)


def main():
    args = parse_args()

    # Criar pasta temporária para trabalhar sem sujar o repo
    with tempfile.TemporaryDirectory() as tmp:
        model_tar_path = os.path.join(tmp, "model.tar.gz")
        test_path = os.path.join(tmp, "test.csv")

        # Download do model.tar.gz e do test.csv
        download_s3_to_file(args.model_tar_s3, model_tar_path)
        download_s3_to_file(args.test_s3, test_path)

        # Extrair o tar.gz (lá dentro deve estar model.joblib)
        extract_dir = os.path.join(tmp, "model")
        os.makedirs(extract_dir, exist_ok=True)

        with tarfile.open(model_tar_path, "r:gz") as tar:
            tar.extractall(path=extract_dir)

        model_file = os.path.join(extract_dir, "model.joblib")
        if not os.path.exists(model_file):
            raise FileNotFoundError(f"Não encontrei model.joblib dentro do tar. Conteúdo em: {extract_dir}")

        # Carregar modelo
        model = joblib.load(model_file)

        # Carregar dados de teste
        df = pd.read_csv(test_path)
        TARGET = "Class"
        X_test = df.drop(columns=[TARGET])
        y_test = df[TARGET]

        # Prever e calcular métricas finais
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        f1 = f1_score(y_test, y_pred)
        pr_auc = average_precision_score(y_test, y_proba)

        print("Test metrics (final):")
        print(f"test:f1={f1}")
        print(f"test:pr_auc={pr_auc}")

        # Guardar relatório local (leve, versionável se quiseres)
        os.makedirs("reports", exist_ok=True)
        report = {
            "model_tar_s3": args.model_tar_s3,
            "test_s3": args.test_s3,
            "f1": float(f1),
            "pr_auc": float(pr_auc)
        }
        with open("reports/test_metrics.json", "w") as f:
            json.dump(report, f, indent=2)

        print("Relatório guardado em: reports/test_metrics.json")


if __name__ == "__main__":
    main()
