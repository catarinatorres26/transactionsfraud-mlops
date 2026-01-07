import os
import json
import joblib
import pandas as pd
from flask import Flask, request, Response

MODEL_PATH = os.environ.get("MODEL_PATH", "/opt/ml/model/model.joblib")

app = Flask(__name__)
model = None


def load_model():
    global model
    if model is None:
        if not os.path.exists(MODEL_PATH):
            # Ajuda a depurar quando o tar.gz não tem o ficheiro esperado
            contents = []
            if os.path.exists("/opt/ml/model"):
                contents = os.listdir("/opt/ml/model")
            raise FileNotFoundError(f"Model not found at {MODEL_PATH}. /opt/ml/model contents: {contents}")
        model = joblib.load(MODEL_PATH)
    return model


@app.get("/ping")
def ping():
    try:
        load_model()
        return Response(response="OK", status=200, mimetype="text/plain")
    except Exception as e:
        return Response(response=str(e), status=500, mimetype="text/plain")


@app.post("/invocations")
def invocations():
    m = load_model()

    ctype = request.content_type or ""
    raw = request.data.decode("utf-8")

    if "text/csv" in ctype:
        # CSV sem header; uma ou várias linhas
        df = pd.read_csv(pd.io.common.StringIO(raw), header=None)
    elif "application/json" in ctype:
        payload = json.loads(raw)
        rows = payload.get("instances") or payload.get("data")
        if rows is None:
            return Response(
                response="JSON must contain 'instances' or 'data' with rows.",
                status=400,
                mimetype="text/plain",
            )
        df = pd.DataFrame(rows)
    else:
        return Response(
            response=f"Unsupported content-type: {ctype}. Use text/csv or application/json.",
            status=415,
            mimetype="text/plain",
        )

    if hasattr(m, "predict_proba"):
        proba = m.predict_proba(df)[:, 1].tolist()
    else:
        proba = None

    pred = m.predict(df).tolist()

    out = {"pred": pred, "proba": proba}
    return Response(response=json.dumps(out), status=200, mimetype="application/json")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
