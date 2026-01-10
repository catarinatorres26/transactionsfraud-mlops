import boto3

AWS_REGION = "eu-west-1"

MODEL_NAME = "transactionsfraud-byoc-model"
ENDPOINT_CONFIG_NAME = "transactionsfraud-byoc-config"
ENDPOINT_NAME = "transactionsfraud-byoc-endpoint"

IMAGE_URI = "267567228900.dkr.ecr.eu-west-1.amazonaws.com/transactionsfraud-byoc:fix4c"


MODEL_DATA_URL = "s3://sagemaker-eu-west-1-267567228900/sagemaker-scikit-lea-260108-1333-006-6204bea1/output/model.tar.gz"

# Idealmente, usa o mesmo role que já usas noutros scripts de SageMaker no repo
ROLE_ARN = "arn:aws:iam::267567228900:role/iseg-prd-sagemaker-role"

sm = boto3.client("sagemaker", region_name=AWS_REGION)


def ensure_model():
    try:
        sm.describe_model(ModelName=MODEL_NAME)
        print(f"Model exists: {MODEL_NAME}")
    except sm.exceptions.ClientError:
        print(f"Creating model: {MODEL_NAME}")
        sm.create_model(
            ModelName=MODEL_NAME,
            ExecutionRoleArn=ROLE_ARN,
            PrimaryContainer={"Image": IMAGE_URI, "ModelDataUrl": MODEL_DATA_URL},
        )


def ensure_endpoint_config():
    try:
        sm.describe_endpoint_config(EndpointConfigName=ENDPOINT_CONFIG_NAME)
        print(f"EndpointConfig exists: {ENDPOINT_CONFIG_NAME}")
    except sm.exceptions.ClientError:
        print(f"Creating EndpointConfig: {ENDPOINT_CONFIG_NAME}")
        sm.create_endpoint_config(
            EndpointConfigName=ENDPOINT_CONFIG_NAME,
            ProductionVariants=[
                {
                    "VariantName": "AllTraffic",
                    "ModelName": MODEL_NAME,
                    "InstanceType": "ml.m5.large",
                    "InitialInstanceCount": 1,
                }
            ],
        )


def create_or_update_endpoint():
    try:
        sm.describe_endpoint(EndpointName=ENDPOINT_NAME)
        print(f"Updating Endpoint: {ENDPOINT_NAME}")
        sm.update_endpoint(
            EndpointName=ENDPOINT_NAME,
            EndpointConfigName=ENDPOINT_CONFIG_NAME,
        )
    except sm.exceptions.ClientError:
        print(f"Creating Endpoint: {ENDPOINT_NAME}")
        sm.create_endpoint(
            EndpointName=ENDPOINT_NAME,
            EndpointConfigName=ENDPOINT_CONFIG_NAME,
        )


def wait_in_service():
    print("Waiting for endpoint to be InService...")
    waiter = sm.get_waiter("endpoint_in_service")
    waiter.wait(EndpointName=ENDPOINT_NAME)
    print("Endpoint is InService")


if __name__ == "__main__":
    ensure_model()
    ensure_endpoint_config()
    create_or_update_endpoint()
    wait_in_service()

