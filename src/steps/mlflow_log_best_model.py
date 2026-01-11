import os
import json
import tarfile
import tempfile
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import boto3
import mlflow
import mlflow.sklearn  # IMPORTANTE
import joblib

AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")

# Tracking server do enunciado (confere se é este ARN no teu account)
MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI",
    "arn:aws:sagemaker:eu-west-1:267567228900:mlflow-tracking-server/aidm"
)

BEST_MODEL_TAR_S3 = os.getenv(
    "BEST_MODEL_TAR_S3",
    ""  # ex: s3://.../output/model.tar.gz
)

METRICS_JSON = os.getenv("METRICS_JSON", "notebooks/reports/test_metrics.json")
EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT", "transactionsfraud-mlops")

# Evidências de drift (locais) — ajusta se estiver noutro path
CONSTRAINT_VIOLATIONS = os.getenv("CONSTRAINT_VIOLATIONS", "constraint_violations.json")
DRIFT_REPORT_CSV = os.getenv("DRIFT_REPORT_CSV", "drift_report_drift_only.csv")

# Tags úteis (opcionais mas recomendadas)
ENDPOINT_NAME = os.getenv("ENDPOINT_NAME", "")
MONITORING_SCHEDULE = os.getenv("MONITORING_SCHEDULE", "")
INFERENCE_IMAGE = os.getenv("INFERENCE_IMAGE", "")
MODEL_DATA_URL = os.getenv("MODEL_DATA_URL", BEST_MODEL_TAR_S3)


def _download_s3(s3_uri: str, dst_path: str):
    u = urlparse(s3_uri)
    bucket = u.netloc
    key = u.path.lstrip("/")
    s3 = boto3.client("s3", region_name=AWS_REGION)
    s3.download_file(bucket, key, dst_path)


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _safe_extract_tar(tar: tarfile.TarFile, path: str):
    """Prevent path traversal in tar extraction."""
    base = Path(path).resolve()
    for member in tar.getmembers():
        member_path = (Path(path) / member.name).resolve()
        if base not in member_path.parents and base != member_path:
            raise RuntimeError(f"Unsafe tar member path: {member.name}")
    tar.extractall(path=path)


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
            # === DRIFT EVIDENCE (SageMaker Model Monitoring) ===
        if os.path.exists("constraint_violations.json"):
            mlflow.log_artifact("constraint_violations.json", artifact_path="monitoring")
            mlflow.set_tag("data_drift_detected", "true")
            mlflow.set_tag("drift_type", "schema_drift")
            mlflow.set_tag("drift_check", "extra_column_check")
        else:
            mlflow.set_tag("data_drift_detected", "false")


        # Drift tags (explicitas)
        if os.path.exists(CONSTRAINT_VIOLATIONS):
            mlflow.set_tag("data_drift_detected", "true")
            mlflow.set_tag("drift_type", "schema_drift")
            mlflow.set_tag("drift_check", "extra_column_check")
        else:
            mlflow.set_tag("data_drift_detected", "false")

        # Métricas (manual)
        for k, v in metrics.items():
            try:
                mlflow.log_metric(k, float(v))
            except Exception:
                pass

        # Artifacts: métricas
        if os.path.exists(METRICS_JSON):
            mlflow.log_artifact(METRICS_JSON, artifact_path="reports")

        # Artifacts: drift evidence (muito importante)
        if os.path.exists(CONSTRAINT_VIOLATIONS):
            mlflow.log_artifact(CONSTRAINT_VIOLATIONS, artifact_path="monitoring")
        if DRIFT_REPORT_CSV and os.path.exists(DRIFT_REPORT_CSV):
            mlflow.log_artifact(DRIFT_REPORT_CSV, artifact_path="monitoring")

        # Baixar model.tar.gz e extrair um model.joblib (se existir)
        with tempfile.TemporaryDirectory() as td:
            tar_path = os.path.join(td, "model.tar.gz")
            _download_s3(BEST_MODEL_TAR_S3, tar_path)

            # Log do tar.gz como artifact (ótimo para auditoria)
            mlflow.log_artifact(tar_path, artifact_path="model_artifact")

            extract_dir = os.path.join(td, "extracted")
            os.makedirs(extract_dir, exist_ok=True)

            with tarfile.open(tar_path, "r:gz") as tar:
                _safe_extract_tar(tar, extract_dir)

            candidate_paths = [
                os.path.join(extract_dir, "model.joblib"),
                os.path.join(extract_dir, "model.pkl"),
                os.path.join(extract_dir, "artifacts", "model.joblib"),
            ]
            model_path = next((p for p in candidate_paths if os.path.exists(p)), None)

            if model_path:
                model = joblib.load(model_path)
                mlflow.sklearn.log_model(model, artifact_path="sklearn_model")

        print("MLflow run_id:", run.info.run_id)


if __name__ == "__main__":
    main()

