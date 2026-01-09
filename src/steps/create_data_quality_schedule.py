import os
import boto3
from sagemaker.session import Session
from sagemaker.model_monitor import DefaultModelMonitor, EndpointInput
from sagemaker.model_monitor.dataset_format import DatasetFormat
from sagemaker.model_monitor import CronExpressionGenerator

AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")
BUCKET = "aidm-creditcard-fraud-267567228900"

ENDPOINT_NAME = "transactionsfraud-byoc-endpoint"
SCHEDULE_NAME = "transactionsfraud-dataquality-schedule"

BASELINE_S3 = f"s3://{BUCKET}/monitoring/baseline/"
MONITOR_OUT_S3 = f"s3://{BUCKET}/monitoring/reports/"

ROLE_ARN = os.getenv("ROLE_ARN", "arn:aws:iam::267567228900:role/iseg-prd-sagemaker-role")

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

    statistics = f"{BASELINE_S3}statistics.json"
    constraints = f"{BASELINE_S3}constraints.json"

    # 1x por hora (ajuste se quiser)
    cron = CronExpressionGenerator.hourly()

    endpoint_in = EndpointInput(
        endpoint_name=ENDPOINT_NAME,
        destination="/opt/ml/processing/input",
    )

    # Criar schedule
    monitor.create_monitoring_schedule(
        monitor_schedule_name=SCHEDULE_NAME,
        endpoint_input=endpoint_in,
        output_s3_uri=MONITOR_OUT_S3,
        statistics=statistics,
        constraints=constraints,
        schedule_cron_expression=cron,
        # Vamos monitorizar CSV (um registo por linha, sem header)
        dataset_format=DatasetFormat.csv(header=False),
    )

    print("Schedule criado:", SCHEDULE_NAME)

if __name__ == "__main__":
    main()
