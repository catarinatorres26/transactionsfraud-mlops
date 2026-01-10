import json
import os
from io import StringIO
from typing import Any, Tuple

import joblib
import numpy as np
import pandas as pd


def _ensure_2d(x: Any) -> np.ndarray:
    arr = np.asarray(x)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr


def model_fn(model_dir: str):
    """
    SageMaker extrai model.tar.gz para /opt/ml/model.
    Precisamos de encontrar model.joblib na raiz.
    """
    path = os.path.join(model_dir, "model.joblib")
    if not os.path.exists(path):
        contents = os.listdir(model_dir) if os.path.exists(model_dir) else []
        raise FileNotFoundError(f"model.joblib not found at {path}. Contents: {contents}")
    return joblib.load(path)


def input_fn(request_body: str, content_type: str):
    """
    Suporta:
      - application/json com {"instances": [[...], ...]} (recomendado)
        ou {"data": [[...], ...]} (fallback)
      - text/csv com linhas numéricas (sem header)
    """
    if content_type and content_type.startswith("application/json"):
        payload = json.loads(request_body)
        rows = payload.get("instances", payload.get("data"))
        if rows is None:
            raise ValueError("JSON must include 'instances' (preferred) or 'data'.")
        return _ensure_2d(rows)

    if content_type in ("text/csv", "text/plain"):
        df = pd.read_csv(StringIO(request_body), header=None)
        return df.values

    raise ValueError(f"Unsupported Content-Type: {content_type}")


def predict_fn(input_data, model):
    """
    Devolve classe e, se existir, probabilidade da classe positiva.
    """
    X = input_data

    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)[:, 1]
    else:
        proba = None

    pred = model.predict(X)
    return {"pred": pred, "proba": proba}


def output_fn(prediction, accept: str) -> Tuple[str, str]:
    """
    Resposta JSON.
    """
    if accept in ("application/json", "*/*", None):
        pred = prediction["pred"]
        proba = prediction["proba"]

        out = {
            "pred": pred.tolist() if hasattr(pred, "tolist") else pred,
            "proba": proba.tolist() if proba is not None and hasattr(proba, "tolist") else None,
        }
        return json.dumps(out), "application/json"

    raise ValueError(f"Unsupported Accept: {accept}")
