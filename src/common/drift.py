import argparse
import json
from dataclasses import dataclass
from typing import List, Dict

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp


@dataclass
class FeatureResult:
    feature: str
    p_value: float
    statistic: float
    status: str


def parse_args():
    p = argparse.ArgumentParser(description="Drift detector (KS-test) baseline vs current (CSV numeric).")
    p.add_argument("--baseline", required=True, help="CSV baseline (sem header)")
    p.add_argument("--current", required=True, help="CSV current (sem header)")
    p.add_argument("--out-json", default="drift_report.json")
    p.add_argument("--out-csv", default="drift_report.csv")
    p.add_argument("--alpha-warn", type=float, default=0.01, help="p-value threshold para WARN")
    p.add_argument("--alpha-alert", type=float, default=0.001, help="p-value threshold para ALERT")
    p.add_argument("--max-rows", type=int, default=50000, help="limite de linhas lidas")
    return p.parse_args()


def load_csv(path: str, max_rows: int) -> pd.DataFrame:
    df = pd.read_csv(path, header=None, nrows=max_rows)
    df = df.apply(pd.to_numeric, errors="coerce")
    df = df.fillna(df.median(numeric_only=True))
    return df


def main():
    args = parse_args()

    b = load_csv(args.baseline, args.max_rows)
    c = load_csv(args.current, args.max_rows)

    if b.shape[1] != c.shape[1]:
        raise SystemExit(f"ERROR: baseline cols={b.shape[1]} != current cols={c.shape[1]}")

    results: List[FeatureResult] = []
    counts = {"OK": 0, "WARN": 0, "ALERT": 0}

    for j in range(b.shape[1]):
        x = b.iloc[:, j].to_numpy(dtype=float)
        y = c.iloc[:, j].to_numpy(dtype=float)

        r = ks_2samp(x, y, alternative="two-sided", mode="auto")
        pval = float(r.pvalue)
        stat = float(r.statistic)

        if pval < args.alpha_alert:
            status = "ALERT"
        elif pval < args.alpha_warn:
            status = "WARN"
        else:
            status = "OK"

        counts[status] += 1
        results.append(FeatureResult(feature=f"f{j}", p_value=pval, statistic=stat, status=status))

    df_out = pd.DataFrame([r.__dict__ for r in results]).sort_values(["status", "p_value"], ascending=[True, True])
    df_out.to_csv(args.out_csv, index=False)

    payload: Dict = {
        "baseline": args.baseline,
        "current": args.current,
        "alpha_warn": args.alpha_warn,
        "alpha_alert": args.alpha_alert,
        "counts": counts,
        "results": [r.__dict__ for r in results],
    }
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("counts:", counts)
    if counts["ALERT"] > 0:
        print("RESULT: ALERT")
        raise SystemExit(2)
    if counts["WARN"] > 0:
        print("RESULT: WARN")
        raise SystemExit(1)
    print("RESULT: OK")


if __name__ == "__main__":
    main()
