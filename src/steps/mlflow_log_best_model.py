import os
import json
import tarfile
import tempfile
from urllib.parse import urlparse

import boto3
import mlflow
import joblib

AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")

# Tracking server do enunciado (ajuste se necessário)
MLFLOW_TRACKING_URI = "arn:aws:sagemaker:eu-west-1:267567228900:mlflow-tracking-server/aidm"

# Preencha com o ModelDataUrl do melhor modelo (pode vir do Model Package)
# Exemplo: s3://sagemaker-eu-west-1-.../output/model.tar.gz
BEST_MODEL_TAR_S3 = os.getenv("BEST_MODEL_TAR_S3", "")

# Métricas que você já calculou no evaluate (ajuste path se necessário)
METRICS_JSON = os.getenv("METRICS_JSON", "notebooks/reports/test_metrics.json")

EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT", "transactionsfraud-mlops")
REGISTERED_MODEL_NAME = os.getenv("REGISTERED_MODEL_NAME", "transactionsfraud-sklearn")


def _download_s3(s3_uri: str, dst_path: str):
    u = urlparse(s3_uri)
    bucket = u.netloc
    key = u.path.lstrip("/")
    s3 = boto3.client("s3", region_name=AWS_REGION)
    s3.download_file(bucket, key, dst_path)


def main():
    if not BEST_MODEL_TAR_S3:
        raise RuntimeError("Defina BEST_MODEL_TAR_S3 com o S3 URI do model.tar.gz (best training job artifact).")

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    # Ler métricas (se existir)
    metrics = {}
    if os.path.exists(METRICS_JSON):
        with open(METRICS_JSON, "r") as f:
            metrics = json.load(f)

    with mlflow.start_run(run_name="byoc-best-model") as run:
        # Tags (manual)
        mlflow.set_tag("project", "transactionsfraud-mlops")
        mlflow.set_tag("stage", "evaluation")
        mlflow.set_tag("best_model_artifact", BEST_MODEL_TAR_S3)

        # Métricas (manual)
        # Ajuste chaves conforme o seu metrics.json
        for k, v in metrics.items():
            try:
                mlflow.log_metric(k, float(v))
            except Exception:
                pass

        # Artifact: metrics json (manual)
        if os.path.exists(METRICS_JSON):
            mlflow.log_artifact(METRICS_JSON, artifact_path="reports")

        # Baixar model.tar.gz e extrair um model.joblib (se existir)
        with tempfile.TemporaryDirectory() as td:
            tar_path = os.path.join(td, "model.tar.gz")
            _download_s3(BEST_MODEL_TAR_S3, tar_path)

            # Log do tar.gz como artifact
            mlflow.log_artifact(tar_path, artifact_path="model_artifact")

            extract_dir = os.path.join(td, "extracted")
            os.makedirs(extract_dir, exist_ok=True)

            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(path=extract_dir)

            # Procura um joblib comum
            candidate_paths = [
                os.path.join(extract_dir, "model.joblib"),
                os.path.join(extract_dir, "model.pkl"),
                os.path.join(extract_dir, "artifacts", "model.joblib"),
            ]
            model_path = next((p for p in candidate_paths if os.path.exists(p)), None)

            if model_path:
                model = joblib.load(model_path)
                mlflow.sklearn.log_model(model, artifact_path="sklearn_model")

                # Registo no MLflow Registry (opcional)
                model_uri = f"runs:/{run.info.run_id}/sklearn_model"
                mlflow.register_model(model_uri, REGISTERED_MODEL_NAME)

        print("MLflow run_id:", run.info.run_id)


if __name__ == "__main__":
    main()
