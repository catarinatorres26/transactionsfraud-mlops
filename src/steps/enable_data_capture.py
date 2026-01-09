import os
import time
import boto3

AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")
BUCKET = os.getenv("BUCKET", "aidm-creditcard-fraud-267567228900")

ENDPOINT_NAME = os.getenv("ENDPOINT_NAME", "transactionsfraud-byoc-endpoint")
NEW_CONFIG_NAME = os.getenv("CAPTURE_CONFIG_NAME", f"{ENDPOINT_NAME}-config-capture")
CAPTURE_S3 = os.getenv("CAPTURE_S3", f"s3://{BUCKET}/monitoring/datacapture/")

sm = boto3.client("sagemaker", region_name=AWS_REGION)

def _wait_endpoint(endpoint_name: str, timeout_sec: int = 1800):
    start = time.time()
    while True:
        ep = sm.describe_endpoint(EndpointName=endpoint_name)
        status = ep["EndpointStatus"]
        print("EndpointStatus:", status)
        if status == "InService":
            return
        if status == "Failed":
            print("FailureReason:", ep.get("FailureReason", "NA"))
            raise RuntimeError(f"Endpoint {endpoint_name} failed")
        if time.time() - start > timeout_sec:
            raise TimeoutError(f"Timeout waiting for endpoint {endpoint_name}")
        time.sleep(20)

def _endpoint_config_exists(name: str) -> bool:
    try:
        sm.describe_endpoint_config(EndpointConfigName=name)
        return True
    except sm.exceptions.ClientError as e:
        if "Could not find endpoint configuration" in str(e) or "ValidationException" in str(e):
            return False
        raise

def main():
    ep = sm.describe_endpoint(EndpointName=ENDPOINT_NAME)
    old_cfg_name = ep["EndpointConfigName"]
    old_cfg = sm.describe_endpoint_config(EndpointConfigName=old_cfg_name)

    prod_variant = old_cfg["ProductionVariants"][0]

    data_capture = {
        "EnableCapture": True,
        "InitialSamplingPercentage": 100,
        "DestinationS3Uri": CAPTURE_S3,
        "CaptureOptions": [{"CaptureMode": "Input"}, {"CaptureMode": "Output"}],
        "CaptureContentTypeHeader": {
            "CsvContentTypes": ["text/csv"],
            "JsonContentTypes": ["application/json"],
        },
    }

    # Se já existir capture config, tenta reusar; se não bater com o variant atual, recria
    if _endpoint_config_exists(NEW_CONFIG_NAME):
        existing = sm.describe_endpoint_config(EndpointConfigName=NEW_CONFIG_NAME)
        same_variant = (
            existing.get("ProductionVariants", [{}])[0].get("ModelName") == prod_variant.get("ModelName")
            and existing.get("ProductionVariants", [{}])[0].get("InstanceType") == prod_variant.get("InstanceType")
        )
        has_capture = "DataCaptureConfig" in existing and existing["DataCaptureConfig"].get("EnableCapture") is True

        if same_variant and has_capture:
            print("Endpoint config de capture já existe e é compatível. A reutilizar:", NEW_CONFIG_NAME)
        else:
            print("Endpoint config de capture existe mas não é compatível. A apagar e recriar:", NEW_CONFIG_NAME)
            sm.delete_endpoint_config(EndpointConfigName=NEW_CONFIG_NAME)
            # pequena espera para consistência
            time.sleep(5)
            sm.create_endpoint_config(
                EndpointConfigName=NEW_CONFIG_NAME,
                ProductionVariants=[prod_variant],
                DataCaptureConfig=data_capture,
            )
            print("Recriado:", NEW_CONFIG_NAME)
    else:
        sm.create_endpoint_config(
            EndpointConfigName=NEW_CONFIG_NAME,
            ProductionVariants=[prod_variant],
            DataCaptureConfig=data_capture,
        )
        print("Criado:", NEW_CONFIG_NAME)

    sm.update_endpoint(EndpointName=ENDPOINT_NAME, EndpointConfigName=NEW_CONFIG_NAME)
    print("Update iniciado. Novo endpoint config:", NEW_CONFIG_NAME)
    _wait_endpoint(ENDPOINT_NAME)
    print("Done.")

if __name__ == "__main__":
    main()
