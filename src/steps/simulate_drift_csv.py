import random
import boto3

AWS_REGION="eu-west-1"
ENDPOINT="transactionsfraud-byoc-endpoint"

def main(n=300):
    rt = boto3.client("sagemaker-runtime", region_name=AWS_REGION)

    for _ in range(n):
        # 30 features: Time + V1..V28 + Amount
        # drift forte no Amount
        row = [0.0]*29 + [5000.0 + random.random()*2000.0]
        csv_line = ",".join(str(x) for x in row) + "\n"

        rt.invoke_endpoint(
            EndpointName=ENDPOINT,
            ContentType="text/csv",
            Body=csv_line.encode("utf-8"),
        )

    print(f"Enviados {n} requests com drift (CSV) para {ENDPOINT}")

if __name__ == "__main__":
    main()
