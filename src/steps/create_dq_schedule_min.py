import os, time, uuid
import boto3

AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")
BUCKET = os.getenv("BUCKET", "aidm-creditcard-fraud-267567228900")

ENDPOINT_NAME = os.getenv("ENDPOINT_NAME", "transactionsfraud-byoc-endpoint")
ROLE_ARN = os.getenv("ROLE_ARN", "arn:aws:iam::267567228900:role/iseg-prd-sagemaker-role")

# Baseline
BASELINE_STATS = f"s3://{BUCKET}/monitoring/baseline/statistics.json"
BASELINE_CONS  = f"s3://{BUCKET}/monitoring/baseline/constraints.json"

# Output
OUTPUT_S3 = f"s3://{BUCKET}/monitoring/reports/"

# Image do Model Monitor (já tens esta)
MONITOR_IMAGE = "468650794304.dkr.ecr.eu-west-1.amazonaws.com/sagemaker-model-monitor-analyzer:latest"

# Cron construído sem copy/paste do '?'
SCHEDULE_CRON = "cron(" + "0/5 * * * ? *" + ")"

sm = boto3.client("sagemaker", region_name=AWS_REGION)

def main():
    # Nome único para não colidir com schedules antigos
    schedule_name = "transactionsfraud-dq-" + time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    print("Schedule:", schedule_name)
    print("Cron:", SCHEDULE_CRON, "repr=", repr(SCHEDULE_CRON))

    ep = sm.describe_endpoint(EndpointName=ENDPOINT_NAME)
    ep_cfg = sm.describe_endpoint_config(EndpointConfigName=ep["EndpointConfigName"])
    variant_name = ep_cfg["ProductionVariants"][0]["VariantName"]

    sm.create_monitoring_schedule(
        MonitoringScheduleName=schedule_name,
        MonitoringScheduleConfig={
            "ScheduleConfig": {"ScheduleExpression": SCHEDULE_CRON},
            "MonitoringJobDefinition": {
                "MonitoringAppSpecification": {"ImageUri": MONITOR_IMAGE},
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
                "RoleArn": ROLE_ARN,
                "StoppingCondition": {"MaxRuntimeInSeconds": 3600},
                "BaselineConfig": {
                    "ConstraintsResource": {"S3Uri": BASELINE_CONS},
                    "StatisticsResource": {"S3Uri": BASELINE_STATS},
                },
                "Environment": {
                    "endpoint_name": ENDPOINT_NAME,
                    "endpoint_variant_name": variant_name,
                },
            },
        },
    )

    print("OK: schedule criado")

if __name__ == "__main__":
    main()
