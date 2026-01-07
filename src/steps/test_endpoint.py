import json
import boto3

AWS_REGION = "eu-west-1"
ENDPOINT_NAME = "transactionsfraud-byoc-endpoint"

rt = boto3.client("sagemaker-runtime", region_name=AWS_REGION)

# IMPORTANTE:
# O seu modelo espera 30 features (Time, V1..V28, Amount) sem a coluna Class.
# Abaixo é só um exemplo; idealmente substitua por uma linha real do dataset (sem Class).
sample = ",".join(["0"] * 29 + ["100.0"]) + "\n"

resp = rt.invoke_endpoint(
    EndpointName=ENDPOINT_NAME,
    ContentType="text/csv",
    Body=sample.encode("utf-8"),
)

out = resp["Body"].read().decode("utf-8")
print(out)
print(json.loads(out))
