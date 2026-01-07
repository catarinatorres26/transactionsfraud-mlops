import time
import boto3

AWS_REGION = "eu-west-1"

# IAM Role (tem de ser arn:aws:iam::...:role/..., NÃO sts::assumed-role)
ROLE_ARN = "arn:aws:iam::267567228900:role/iseg-prd-sagemaker-role"

# Preencha com a sua imagem no ECR (ex.: 2675...dkr.ecr.eu-west-1.amazonaws.com/transactionsfraud-byoc:latest)
IMAGE_URI = "REPLACE_ME_IMAGE_URI"

# Model Package que você já criou
MODEL_PACKAGE_ARN = "arn:aws:sagemaker:eu-west-1:267567228900:model-package/transactionsfraud-sklearn/1"

ENDPOINT_NAME = "transactionsfraud-byoc-endpoint"
MODEL_NAME = f"{ENDPOINT_NAME}-model"
ENDPOINT_CONFIG_NAME = f"{ENDPOINT_NAME}-config"

sm = boto3.client("sagemaker", region_name=AWS_REGION)


def main():
    mp = sm.describe_model_package(ModelPackageName=MODEL_PACKAGE_ARN)
    model_data_url = mp["InferenceSpecification"]["Containers"][0]["ModelDataUrl"]

    if IMAGE_URI == "REPLACE_ME_IMAGE_URI":
        raise RuntimeError("Edite IMAGE_URI no ficheiro e coloque o URI real do ECR.")

    # 1) Create Model
    print("Creating model:", MODEL_NAME)
    sm.create_model(
        ModelName=MODEL_NAME,
        PrimaryContainer={
            "Image": IMAGE_URI,
            "ModelDataUrl": model_data_url,
        },
        ExecutionRoleArn=ROLE_ARN,
    )

    # 2) Endpoint config
    print("Creating endpoint config:", ENDPOINT_CONFIG_NAME)
    sm.create_endpoint_config(
        EndpointConfigName=ENDPOINT_CONFIG_NAME,
        ProductionVariants=[
            {
                "VariantName": "AllTraffic",
                "ModelName": MODEL_NAME,
                "InitialInstanceCount": 1,
                "InstanceType": "ml.m5.large",
            }
        ],
    )

    # 3) Endpoint
    print("Creating endpoint:", ENDPOINT_NAME)
    sm.create_endpoint(
        EndpointName=ENDPOINT_NAME,
        EndpointConfigName=ENDPOINT_CONFIG_NAME,
    )

    # 4) Wait
    while True:
        d = sm.describe_endpoint(EndpointName=ENDPOINT_NAME)
        status = d["EndpointStatus"]
        print("EndpointStatus:", status)
        if status in ["InService", "Failed"]:
            if status == "Failed":
                print("FailureReason:", d.get("FailureReason"))
            break
        time.sleep(30)

    print("Done.")


if __name__ == "__main__":
    main()
