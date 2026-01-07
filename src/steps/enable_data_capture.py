import boto3

AWS_REGION="eu-west-1"
ENDPOINT_NAME="transactionsfraud-byoc-endpoint"
NEW_CONFIG_NAME=f"{ENDPOINT_NAME}-config-capture"
CAPTURE_S3="s3://aidm-creditcard-fraud-267567228900/monitoring/datacapture/"

sm = boto3.client("sagemaker", region_name=AWS_REGION)

def main():
    ep = sm.describe_endpoint(EndpointName=ENDPOINT_NAME)
    old_cfg = ep["EndpointConfigName"]
    cfg = sm.describe_endpoint_config(EndpointConfigName=old_cfg)

    prod_variant = cfg["ProductionVariants"][0]
    data_capture = {
        "EnableCapture": True,
        "InitialSamplingPercentage": 100,
        "DestinationS3Uri": CAPTURE_S3,
        "CaptureOptions": [{"CaptureMode": "Input"}, {"CaptureMode": "Output"}],
        "CaptureContentTypeHeader": {
            "CsvContentTypes": ["text/csv"],
            "JsonContentTypes": ["application/json"]
        }
    }

    sm.create_endpoint_config(
        EndpointConfigName=NEW_CONFIG_NAME,
        ProductionVariants=[prod_variant],
        DataCaptureConfig=data_capture
    )

    sm.update_endpoint(EndpointName=ENDPOINT_NAME, EndpointConfigName=NEW_CONFIG_NAME)
    print("Update iniciado. Novo endpoint config:", NEW_CONFIG_NAME)

if __name__ == "__main__":
    main()
