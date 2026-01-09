import os
import boto3
import time
from datetime import datetime

AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")
BUCKET = os.getenv("BUCKET", "aidm-creditcard-fraud-267567228900")

ENDPOINT_NAME = os.getenv("ENDPOINT_NAME", "transactionsfraud-byoc-endpoint")
SCHEDULE_NAME = os.getenv("SCHEDULE_NAME", "transactionsfraud-dataquality-now")

ROLE_ARN = os.getenv("ROLE_ARN", "arn:aws:iam::267567228900:role/iseg-prd-sagemaker-role")

# Baseline (já tens estes ficheiros)
BASELINE_STATS = f"s3://{BUCKET}/monitoring/baseline/statistics.json"
BASELINE_CONS  = f"s3://{BUCKET}/monitoring/baseline/constraints.json"

# Reports do Model Monitor
OUTPUT_S3 = f"s3://{BUCKET}/monitoring/reports/"

# IMPORTANTÍSSIMO: offsets (ISO 8601 duration), NÃO timestamps
DATA_ANALYSIS_START = os.getenv("DATA_ANALYSIS_START", "-PT24H")
DATA_ANALYSIS_END   = os.getenv("DATA_ANALYSIS_END", "PT0H")

# Imagem certa do analyzer (eu-west-1)
MONITOR_IMAGE = os.getenv(
    "MONITOR_IMAGE",
    "468650794304.dkr.ecr.eu-west-1.amazonaws.com/sagemaker-model-monitor-analyzer:latest"
)

sm = boto3.client("sagemaker", region_name=AWS_REGION)

def main():
    print("A criar schedule NOW:", SCHEDULE_NAME)
    print("Endpoint:", ENDPOINT_NAME)
    print("Window:", DATA_ANALYSIS_START, "->", DATA_ANALYSIS_END)
    print("Output:", OUTPUT_S3)

    ep = sm.describe_endpoint(EndpointName=ENDPOINT_NAME)
    ep_cfg = sm.describe_endpoint_config(EndpointConfigName=ep["EndpointConfigName"])
    variant_name = ep_cfg["ProductionVariants"][0]["VariantName"]
    print("EndpointConfig:", ep["EndpointConfigName"])
    print("Variant:", variant_name)

    # Idempotência: apagar se já existir (quando estiveres a iterar)
    try:
        sm.describe_monitoring_schedule(MonitoringScheduleName=SCHEDULE_NAME)
        sm.delete_monitoring_schedule(MonitoringScheduleName=SCHEDULE_NAME)
        print("Schedule antigo apagado:", SCHEDULE_NAME)
        time.sleep(5)
    except sm.exceptions.ResourceNotFound:
        pass

    sm.create_monitoring_schedule(
        MonitoringScheduleName=SCHEDULE_NAME,
        MonitoringScheduleConfig={
            "ScheduleConfig": {
                "ScheduleExpression": "NOW",
                "DataAnalysisStartTime": DATA_ANALYSIS_START,
                "DataAnalysisEndTime": DATA_ANALYSIS_END,
            },
            "MonitoringJobDefinition": {
                "MonitoringAppSpecification": {
                    "ImageUri": MONITOR_IMAGE,
                },
                "MonitoringInputs": [
                    {
                        "EndpointInput": {
                            "EndpointName": ENDPOINT_NAME,
                            "LocalPath": "/opt/ml/processing/input",
                            "S3InputMode": "File",
                            "S3DataDistributionType": "FullyReplicated",
                        }
                    }
                ],
                "MonitoringOutputConfig": {
                    "MonitoringOutputs": [
                        {
                            "S3Output": {
                                "S3Uri": OUTPUT_S3,
                                "LocalPath": "/opt/ml/processing/output",
                                "S3UploadMode": "EndOfJob",
                            }
                        }
                    ]
                },
                "MonitoringResources": {
                    "ClusterConfig": {
                        "InstanceCount": 1,
                        "InstanceType": "ml.m5.xlarge",
                        "VolumeSizeInGB": 20,
                    }
                },
                "StoppingCondition": {"MaxRuntimeInSeconds": 3600},
                "RoleArn": ROLE_ARN,
                "BaselineConfig": {
                    "StatisticsResource": {"S3Uri": BASELINE_STATS},
                    "ConstraintsResource": {"S3Uri": BASELINE_CONS},
                },
                "Environment": {
                    # garante que o processing lê o que está no data capture do endpoint
                    "endpoint_name": ENDPOINT_NAME,
                    "baseline_constraints": BASELINE_CONS,
                    "baseline_statistics": BASELINE_STATS,
                },
            },
        },
        Tags=[{"Key": "project", "Value": "transactionsfraud-mlops"}],
    )

    print("OK: schedule criado:", SCHEDULE_NAME)
    # Mostrar estado (pode demorar a aparecer execução)
    desc = sm.describe_monitoring_schedule(MonitoringScheduleName=SCHEDULE_NAME)
    print("Status:", desc["MonitoringScheduleStatus"])

if __name__ == "__main__":
    main()
