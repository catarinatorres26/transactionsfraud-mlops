
import argparse
import random
import boto3


def parse_args():
    p = argparse.ArgumentParser(
        description="Envia requests CSV para um endpoint SageMaker com drift intencional (Amount alto)."
    )
    p.add_argument("--region", default="eu-west-1", help="AWS region (default: eu-west-1)")
    p.add_argument("--endpoint", default="transactionsfraud-byoc-endpoint", help="Nome do endpoint")
    p.add_argument("--n", type=int, default=300, help="Número de requests a enviar")
    p.add_argument("--amount-min", type=float, default=5000.0, help="Valor mínimo do Amount driftado")
    p.add_argument("--amount-max", type=float, default=7000.0, help="Valor máximo do Amount driftado")
    p.add_argument("--seed", type=int, default=42, help="Seed para reproducibilidade")
    p.add_argument("--time", type=float, default=0.0, help="Valor do campo Time (default 0.0)")
    p.add_argument("--v-fill", type=float, default=0.0, help="Valor fill para V1..V28 (default 0.0)")
    return p.parse_args()


def main():
    args = parse_args()
    random.seed(args.seed)

    rt = boto3.client("sagemaker-runtime", region_name=args.region)

    for _ in range(args.n):
        # 30 features: Time + V1..V28 + Amount
        amount = args.amount_min + random.random() * (args.amount_max - args.amount_min)
        row = [args.time] + [args.v_fill] * 28 + [amount]
        csv_line = ",".join(str(x) for x in row) + "\n"

        rt.invoke_endpoint(
            EndpointName=args.endpoint,
            ContentType="text/csv",
            Body=csv_line.encode("utf-8"),
        )

    print(f"Enviados {args.n} requests com drift (CSV) para {args.endpoint}")
    print(f"Amount range: [{args.amount_min}, {args.amount_max}]  seed={args.seed}  region={args.region}")


if __name__ == "__main__":
    main()
