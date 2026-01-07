import boto3

AWS_REGION="eu-west-1"
ENDPOINT_NAME="transactionsfraud-byoc-endpoint"

rt = boto3.client("sagemaker-runtime", region_name=AWS_REGION)

row = [0.0]*29 + [100.0]
csv_line = ",".join(str(x) for x in row) + "\n"

resp = rt.invoke_endpoint(
    EndpointName=ENDPOINT_NAME,
    ContentType="text/csv",
    Body=csv_line.encode("utf-8"),
)

print(resp["Body"].read().decode("utf-8"))
