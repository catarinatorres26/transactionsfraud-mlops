import os
import time
import boto3

AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")

# Ajusta se necessário
ENDPOINT_NAME = os.getenv("ENDPOINT_NAME", "transactionsfraud-byoc-endpoint")
MODEL_NAME = f"{ENDPOINT_NAME}-model"
ENDPOINT_CONFIG_NAME = os.getenv("ENDPOINT_CONFIG_NAME", f"{ENDPOINT_NAME}-config")

# Obrigatórios (tens isto no teu repo; mantém os mesmos valores)
ROLE_ARN = os.getenv("ROLE_ARN", "arn:aws:iam::267567228900:role/iseg-prd-sagemaker-role")

# Model Package do Model Registry (o teu já existe)
MODEL_PACKAGE_ARN = os.getenv(
    "MODEL_PACKAGE_ARN",
    "arn:aws:sagemaker:eu-west-1:267567228900:model-package/transactionsfraud-sklearn/1",
)

# BYOC image no ECR (já tens :latest)
IMAGE_URI = os.getenv(
    "IMAGE_URI",
    "267567228900.dkr.ecr.eu-west-1.amazonaws.com/transactionsfraud-byoc:latest",
)

INSTANCE_TYPE = os.getenv("INSTANCE_TYPE", "ml.m5.large")
INITIAL_INSTANCE_COUNT = int(os.getenv("INITIAL_INSTANCE_COUNT", "1"))

sm = boto3.client("sagemaker", region_name=AWS_REGION)


def _exists_model(model_name: str) -> bool:
    try:
        sm.describe_model(ModelName=model_name)
        return True
    except sm.exceptions.ClientError as e:
        if "Could not find model" in str(e) or "ValidationException" in str(e):
            return False
        raise


def _delete_endpoint_if_exists(name: str):
    try:
        sm.describe_endpoint(EndpointName=name)
        print("Endpoint já existe. A apagar:", name)
        sm.delete_endpoint(EndpointName=name)
        # esperar até desaparecer
        while True:
            try:
                sm.describe_endpoint(EndpointName=name)
                time.sleep(10)
            except sm.exceptions.ClientError as e:
                if "Could not find endpoint" in str(e) or "ValidationException" in str(e):
                    break
                raise
    except sm.exceptions.ClientError as e:
        if "Could not find endpoint" in str(e) or "ValidationException" in str(e):
            return
        raise


def _delete_endpoint_config_if_exists(name: str):
    try:
        sm.describe_endpoint_config(EndpointConfigName=name)
        print("Endpoint config já existe. A apagar:", name)
        sm.delete_endpoint_config(EndpointConfigName=name)
    except sm.exceptions.ClientError as e:
        if "Could not find endpoint configuration" in str(e) or "ValidationException" in str(e):
            return
        raise


def _wait_endpoint(name: str, timeout_sec: int = 1800):
    start = time.time()
    while True:
        desc = sm.describe_endpoint(EndpointName=name)
        status = desc["EndpointStatus"]
        print("EndpointStatus:", status)
        if status == "InService":
            return
        if status == "Failed":
            print("FailureReason:", desc.get("FailureReason", "NA"))
            raise RuntimeError(f"Endpoint {name} failed")
        if time.time() - start > timeout_sec:
            raise TimeoutError(f"Timeout waiting for endpoint {name}")
        time.sleep(20)


def main():
    # 1) ModelDataUrl a partir do Model Package
    mp = sm.describe_model_package(ModelPackageName=MODEL_PACKAGE_ARN)
    model_data_url = mp["InferenceSpecification"]["Containers"][0]["ModelDataUrl"]

    # 2) Create Model (ou reuse)
    if _exists_model(MODEL_NAME):
        print("Model já existe. A reutilizar:", MODEL_NAME)
    else:
        print("Creating model:", MODEL_NAME)
        sm.create_model(
            ModelName=MODEL_NAME,
            PrimaryContainer={
                "Image": IMAGE_URI,
                "ModelDataUrl": model_data_url,
            },
            ExecutionRoleArn=ROLE_ARN,
        )

    # 3) Endpoint config: apagar e recriar (mais simples/robusto)
    _delete_endpoint_config_if_exists(ENDPOINT_CONFIG_NAME)
    print("Creating endpoint config:", ENDPOINT_CONFIG_NAME)
    sm.create_endpoint_config(
        EndpointConfigName=ENDPOINT_CONFIG_NAME,
        ProductionVariants=[
            {
                "VariantName": "AllTraffic",
                "ModelName": MODEL_NAME,
                "InitialInstanceCount": INITIAL_INSTANCE_COUNT,
                "InstanceType": INSTANCE_TYPE,
                "InitialVariantWeight": 1.0,
            }
        ],
    )

    # 4) Endpoint: se existir, apagar e recriar (garante consistência)
    _delete_endpoint_if_exists(ENDPOINT_NAME)
    print("Creating endpoint:", ENDPOINT_NAME)
    sm.create_endpoint(
        EndpointName=ENDPOINT_NAME,
        EndpointConfigName=ENDPOINT_CONFIG_NAME,
    )

    _wait_endpoint(ENDPOINT_NAME)
    print("Done.")


if __name__ == "__main__":
    main()
