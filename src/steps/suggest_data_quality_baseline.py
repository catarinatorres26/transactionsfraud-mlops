import boto3
import sagemaker
from sagemaker.model_monitor import DefaultModelMonitor
from sagemaker.model_monitor.dataset_format import DatasetFormat

AWS_REGION = "eu-west-1"
ROLE_ARN = "arn:aws:iam::267567228900:role/iseg-prd-sagemaker-role"

BASELINE_DATA_S3 = "s3://aidm-creditcard-fraud-267567228900/monitoring/baseline/baseline.csv"
BASELINE_OUTPUT_S3 = "s3://aidm-creditcard-fraud-267567228900/monitoring/baseline/results/"
JOB_NAME = "transactionsfraud-dq-baseline"

if __name__ == "__main__":
    session = sagemaker.Session(boto3.Session(region_name=AWS_REGION))

    monitor = DefaultModelMonitor(
        role=ROLE_ARN,
        instance_count=1,
        instance_type="ml.m5.large",
        volume_size_in_gb=20,
        max_runtime_in_seconds=3600,
        sagemaker_session=session,
    )

    monitor.suggest_baseline(
        baseline_dataset=BASELINE_DATA_S3,
        dataset_format=DatasetFormat.csv(header=False),
        output_s3_uri=BASELINE_OUTPUT_S3,
        wait=True,
        job_name=JOB_NAME,
    )

    print("Baseline created.")
    print(f"Statistics:  {BASELINE_OUTPUT_S3}{JOB_NAME}/statistics.json")
    print(f"Constraints: {BASELINE_OUTPUT_S3}{JOB_NAME}/constraints.json")
