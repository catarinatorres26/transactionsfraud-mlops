import boto3
import sagemaker
from sagemaker.model_monitor import DefaultModelMonitor, EndpointInput

AWS_REGION = "eu-west-1"
ROLE_ARN = "arn:aws:iam::267567228900:role/iseg-prd-sagemaker-role"

ENDPOINT_NAME = "transactionsfraud-byoc-endpoint"
SCHEDULE_NAME = "transactionsfraud-dataquality-schedule"

REPORTS_S3 = "s3://aidm-creditcard-fraud-267567228900/monitoring/reports/"

STATISTICS_S3 = "s3://aidm-creditcard-fraud-267567228900/monitoring/baseline/results/statistics.json"
CONSTRAINTS_S3 = "s3://aidm-creditcard-fraud-267567228900/monitoring/baseline/results/constraints.json"


CRON_HOURLY = "cron(0 * * * ? *)"


def main():
    session = sagemaker.Session(boto3.Session(region_name=AWS_REGION))

    monitor = DefaultModelMonitor(
        role=ROLE_ARN,
        instance_count=1,
        instance_type="ml.m5.large",
        volume_size_in_gb=20,
        max_runtime_in_seconds=3600,
        sagemaker_session=session,
    )

    endpoint_input = EndpointInput(
        endpoint_name=ENDPOINT_NAME,
        destination="/opt/ml/processing/input",
    )

    try:
        monitor.create_monitoring_schedule(
            monitor_schedule_name=SCHEDULE_NAME,
            endpoint_input=endpoint_input,
            output_s3_uri=REPORTS_S3,
            statistics=STATISTICS_S3,
            constraints=CONSTRAINTS_S3,
            schedule_cron_expression=CRON_HOURLY,
        )
        print(f"Created monitoring schedule: {SCHEDULE_NAME}")
    except Exception as e:
        msg = str(e)
        if "already exists" in msg or "AlreadyExists" in msg:
            print(f"Schedule already exists: {SCHEDULE_NAME}")
        else:
            raise

    print("Done.")


if __name__ == "__main__":
    main()



