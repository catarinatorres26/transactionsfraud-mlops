import os
import boto3

AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")
BUCKET = "aidm-creditcard-fraud-267567228900"

ENDPOINT_NAME = "transactionsfraud-byoc-endpoint"
SCHEDULE_NAME = "transactionsfraud-dataquality-schedule"

ROLE_ARN = os.getenv("ROLE_ARN", "arn:aws:iam::267567228900:role/iseg-prd-sagemaker-role")

BASELINE_STATS = f"s3://{BUCKET}/monitoring/baseline/statistics.json"
BASELINE_CONS  = f"s3://{BUCKET}/monitoring/baseline/constraints.json"
OUTPUT_S3      = f"s3://{BUCKET}/monitoring/reports/"

# a cada 1h
SCHEDULE_CRON = "cron(0 * ? * * *)"

sm = boto3.client("sagemaker", region_name=AWS_REGION)

def main():
    # descobrir endpoint config atual (importante, porque você atualizou com data capture)
    ep = sm.describe_endpoint(EndpointName=ENDPOINT_NAME)
    ep_cfg_name = ep["EndpointConfigName"]
    ep_cfg = sm.describe_endpoint_config(EndpointConfigName=ep_cfg_name)

    pv = ep_cfg["ProductionVariants"][0]
    variant_name = pv["VariantName"]

    # Se já existir, apagar (idempotência)
    try:
        sm.describe_monitoring_schedule(MonitoringScheduleName=SCHEDULE_NAME)
        sm.delete_monitoring_schedule(MonitoringScheduleName=SCHEDULE_NAME)
        print("Schedule existente apagado:", SCHEDULE_NAME)
    except sm.exceptions.ResourceNotFound:
        pass

    sm.create_monitoring_schedule(
        MonitoringScheduleName=SCHEDULE_NAME,
        MonitoringScheduleConfig={
            "ScheduleConfig": {"ScheduleExpression": SCHEDULE_CRON},
            "MonitoringJobDefinition": {
                "MonitoringAppSpecification": {
                    "ImageUri": "156813124566.dkr.ecr.eu-west-1.amazonaws.com/sagemaker-model-monitor-analyzer:latest"
                },
                "MonitoringInputs": [{
                    "EndpointInput": {
                        "EndpointName": ENDPOINT_NAME,
                        "LocalPath": "/opt/ml/processing/input",
                        "S3InputMode": "File",
                        "S3DataDistributionType": "FullyReplicated",
                    }
                }],
                "MonitoringOutputConfig": {
                    "MonitoringOutputs": [{
                        "S3Output": {
                            "S3Uri": OUTPUT_S3,
                            "LocalPath": "/opt/ml/processing/output",
                            "S3UploadMode": "EndOfJob"
                        }
                    }]
                },
                "MonitoringResources": {
                    "ClusterConfig": {
                        "InstanceCount": 1,
                        "InstanceType": "ml.m5.xlarge",
                        "VolumeSizeInGB": 20
                    }
                },
                "RoleArn": ROLE_ARN,
                "BaselineConfig": {
                    "StatisticsResource": {"S3Uri": BASELINE_STATS},
                    "ConstraintsResource": {"S3Uri": BASELINE_CONS},
                },
                "Environment": {
                    # diz ao monitor que é data quality
                    "analysis_type": "data_quality",
                    # importante: para ligar ao variant certo
                    "endpoint_variant_name": variant_name,
                },
                "StoppingCondition": {"MaxRuntimeInSeconds": 3600},
            }
        }
    )

    print("Schedule criado:", SCHEDULE_NAME)
    print("EndpointConfig usado:", ep_cfg_name)
    print("VariantName:", variant_name)

if __name__ == "__main__":
    main()
