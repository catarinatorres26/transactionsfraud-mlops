import json
import boto3

AWS_REGION = "eu-west-1"
ENDPOINT_NAME = "transactionsfraud-byoc-endpoint"

rt = boto3.client("sagemaker-runtime", region_name=AWS_REGION)

# Ajusta o número de features ao teu modelo
row = [0.0] * 29 + [100.0]  # exemplo: 30 features

payload = {"csv":"0,19.89,20.26,130.5,1214.0,0.1037, ... ,0.09136"}


resp = rt.invoke_endpoint(
    EndpointName=ENDPOINT_NAME,
    ContentType="application/json",
    Accept="application/json",
    Body=json.dumps(payload).encode("utf-8"),
)

print(resp["Body"].read().decode("utf-8"))
