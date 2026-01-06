import os
import boto3

BUCKET = "aidm-creditcard-fraud-267567228900"
PREFIX = "transactions/data/splits"

FILES = {
    "train": ("../data/splits/train.csv", f"{PREFIX}/train.csv"),
    "val":   ("../data/splits/val.csv",   f"{PREFIX}/val.csv"),
    "test":  ("../data/splits/test.csv",  f"{PREFIX}/test.csv"),
}

def main():
    s3 = boto3.client("s3")

    for name, (local_path, s3_key) in FILES.items():
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Não encontrei {local_path}. Corre primeiro o split_data.py")

        s3.upload_file(local_path, BUCKET, s3_key)
        print(f"Uploaded {name}: s3://{BUCKET}/{s3_key}")

if __name__ == "__main__":
    main()
