import json
import os
from io import StringIO
from typing import Any, Tuple

import joblib
import numpy as np
import pandas as pd
from flask import Flask, Response, request


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

    proba = None
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)[:, 1]

    pred = model.predict(X)
    return {"pred": pred, "proba": proba}


def output_fn(prediction, accept: str) -> Tuple[str, str]:
    """
    Output determinístico para monitoring:

    - Se Accept CSV/text: devolve CSV com 2 colunas (pred, proba) quando possível.
      Ex.: "0,7.976846774430716e-06\n"
      Se o modelo não suportar predict_proba, faz fallback para 1 coluna (pred).

    - Se Accept JSON: devolve {"pred":[...], "proba":[...]}.
    """
    pred = prediction["pred"]
    proba = prediction["proba"]

    pred_list = pred.tolist() if hasattr(pred, "tolist") else pred
    if not isinstance(pred_list, list):
        pred_list = [pred_list]

    proba_list = None
    if proba is not None:
        proba_list = proba.tolist() if hasattr(proba, "tolist") else proba
        if not isinstance(proba_list, list):
            proba_list = [proba_list]

    accept_norm = (accept or "*/*").lower()

    # CSV/text: pred,proba por linha (2 colunas)
    if accept_norm.startswith("text/csv") or accept_norm.startswith("text/plain") or accept_norm == "*/*":
        if proba_list is not None:
            lines = [f"{p},{pr}" for p, pr in zip(pred_list, proba_list)]
        else:
            lines = [f"{p}" for p in pred_list]
        return "\n".join(lines) + "\n", "text/csv"

    # JSON: pred + proba
    if accept_norm.startswith("application/json"):
        out = {"pred": pred_list, "proba": proba_list}
        return json.dumps(out), "application/json"

    raise ValueError(f"Unsupported Accept: {accept}")


app = Flask(__name__)
_model = None


@app.get("/ping")
def ping():
    global _model
    if _model is None:
        _model = model_fn(os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    return Response("ok\n", mimetype="text/plain")


@app.post("/invocations")
def invocations():
    global _model
    if _model is None:
        _model = model_fn(os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))

    body = request.get_data(as_text=True)

    # Normaliza content-type (remove charset)
    content_type = (request.content_type or "").split(";")[0].strip().lower()
    accept = request.headers.get("Accept", "*/*")
    accept = (accept or "*/*").split(";")[0].strip().lower()

    # Regra determinística para o teu caso de monitoring:
    # se input é CSV -> output CSV (independente do Accept)
    if content_type in ("text/csv", "text/plain"):
        accept = "text/csv"

    x = input_fn(body, content_type)
    pred = predict_fn(x, _model)
    out_body, out_ctype = output_fn(pred, accept)
    return Response(out_body, mimetype=out_ctype)
