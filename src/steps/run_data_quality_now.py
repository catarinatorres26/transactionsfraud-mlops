import boto3
import sagemaker
from botocore.exceptions import ClientError
from sagemaker.model_monitor import DefaultModelMonitor

AWS_REGION = "eu-west-1"
ROLE_ARN = "arn:aws:iam::267567228900:role/iseg-prd-sagemaker-role"

ENDPOINT_NAME = "transactionsfraud-byoc-endpoint"

# Schedule NOW (se não conseguir apagar, ele cria um nome alternativo)
BASE_SCHEDULE_NAME = "transactionsfraud-dataquality-now2"

OUTPUT_S3 = "s3://sagemaker-eu-west-1-267567228900/monitoring/reports/"



STATISTICS_S3 = "s3://aidm-creditcard-fraud-267567228900/monitoring/baseline/results/statistics.json"
CONSTRAINTS_S3 = "s3://aidm-creditcard-fraud-267567228900/monitoring/baseline/results/constraints.json"

INSTANCE_TYPE = "ml.m5.large"


def try_delete_schedule(sm, name: str) -> bool:
    try:
        sm.delete_monitoring_schedule(MonitoringScheduleName=name)
        print(f"Deleted existing schedule: {name}")
        return True
    except ClientError as e:
        code = e.response["Error"]["Code"]
        msg = str(e)

        # Se não existir, está tudo bem (queríamos "limpar" e seguir)
        if code in ("ResourceNotFound", "ValidationException"):
            return True

        # Se não dá para apagar por execuções em progresso, não falhamos
        if "in-progress executions" in msg or "has in-progress executions" in msg:
            print(f"Cannot delete schedule (in-progress executions): {name}")
            return False

        raise


def main():
    boto_sess = boto3.Session(region_name=AWS_REGION)
    sm = boto_sess.client("sagemaker")
    sm_sess = sagemaker.Session(boto_sess)

    # Usamos o DefaultModelMonitor apenas para obter a imagem correta do analyzer
    monitor = DefaultModelMonitor(
        role=ROLE_ARN,
        instance_count=1,
        instance_type=INSTANCE_TYPE,
        volume_size_in_gb=20,
        max_runtime_in_seconds=3600,
        sagemaker_session=sm_sess,
    )

    analyzer_image = monitor.image_uri
    print("Using analyzer image:", analyzer_image)

    schedule_name = BASE_SCHEDULE_NAME

    # tenta apagar para reutilizar o nome; se não der, cria um nome único
    deleted = try_delete_schedule(sm, schedule_name)
    if not deleted:
        import datetime
        suffix = datetime.datetime.utcnow().strftime("%H%M%S")
        schedule_name = f"{BASE_SCHEDULE_NAME}-{suffix}"
        print("Using alternative schedule name:", schedule_name)

    print(f"Creating NOW DataQuality schedule: {schedule_name}")

    sm.create_monitoring_schedule(
        MonitoringScheduleName=schedule_name,
        MonitoringScheduleConfig={
            "ScheduleConfig": {
                "ScheduleExpression": "NOW",
                # janela larga para garantir que apanha dados (ajusta para -PT1H quando estiver estável)
                "DataAnalysisStartTime": "-PT24H",
                "DataAnalysisEndTime": "PT0H",
            },
            "MonitoringJobDefinition": {
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
                        "InstanceType": INSTANCE_TYPE,
                        "VolumeSizeInGB": 20,
                    }
                },
                "RoleArn": ROLE_ARN,
                "StoppingCondition": {"MaxRuntimeInSeconds": 3600},
                "BaselineConfig": {
                    "StatisticsResource": {"S3Uri": STATISTICS_S3},
                    "ConstraintsResource": {"S3Uri": CONSTRAINTS_S3},
                },
                # ESTE era o parâmetro em falta
                "MonitoringAppSpecification": {
                    "ImageUri": analyzer_image
                },
            },
        },
    )

    print("OK: NOW schedule created:", schedule_name)
    print("Now list executions with:")
    print(
        f"aws sagemaker list-monitoring-executions --monitoring-schedule-name {schedule_name} "
        f"--region {AWS_REGION} --sort-by CreationTime --sort-order Descending --max-results 10 "
        f"--query \"MonitoringExecutionSummaries[].{{Created:CreationTime,Status:MonitoringExecutionStatus,Reason:FailureReason}}\" --output table"
    )


if __name__ == "__main__":
    main()
