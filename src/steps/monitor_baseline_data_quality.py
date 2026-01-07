import os
import boto3
from urllib.parse import urlparse

from sagemaker.session import Session
from sagemaker.model_monitor import DefaultModelMonitor
from sagemaker.model_monitor.dataset_format import DatasetFormat

AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")

BUCKET = "aidm-creditcard-fraud-267567228900"
BASELINE_S3 = f"s3://{BUCKET}/transactions/data/splits/train.csv"

# Onde guardar outputs do baseline
BASELINE_OUT_S3 = f"s3://{BUCKET}/monitoring/baseline/"

ROLE_ARN = os.getenv("ROLE_ARN", "arn:aws:iam::267567228900:role/iseg-prd-sagemaker-role")


def _list_s3(prefix_uri: str):
    u = urlparse(prefix_uri)
    s3 = boto3.client("s3", region_name=AWS_REGION)
    resp = s3.list_objects_v2(Bucket=u.netloc, Prefix=u.path.lstrip("/"))
    return [o["Key"] for o in resp.get("Contents", [])]


def main():
    sm_sess = Session(boto3.Session(region_name=AWS_REGION))

    monitor = DefaultModelMonitor(
        role=ROLE_ARN,
        instance_count=1,
        instance_type="ml.m5.xlarge",
        volume_size_in_gb=20,
        max_runtime_in_seconds=3600,
        sagemaker_session=sm_sess,
    )

    monitor.suggest_baseline(
        baseline_dataset=BASELINE_S3,
        dataset_format=DatasetFormat.csv(header=True),
        output_s3_uri=BASELINE_OUT_S3,
        wait=True,
        logs=True,
    )

    print("Baseline criado em:", BASELINE_OUT_S3)

    # Validar que os ficheiros existem no prefix
    keys = _list_s3(BASELINE_OUT_S3)
    stats = [k for k in keys if k.endswith("statistics.json")]
    cons = [k for k in keys if k.endswith("constraints.json")]

    print("Encontrados statistics.json:", len(stats))
    print("Encontrados constraints.json:", len(cons))

    if stats:
        print("Exemplo statistics.json:", f"s3://{BUCKET}/{stats[0]}")
    if cons:
        print("Exemplo constraints.json:", f"s3://{BUCKET}/{cons[0]}")

    if not stats or not cons:
        raise RuntimeError("Baseline gerado, mas não encontrei statistics/constraints no S3. Verifique permissões/prefix.")

if __name__ == "__main__":
    main()
