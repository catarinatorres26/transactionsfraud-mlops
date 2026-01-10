FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    SAGEMAKER_PROGRAM=inference.py

WORKDIR /opt/program

# Instala deps SEM rede (a partir de wheels locais)
COPY requirements.txt .
COPY wheels /opt/wheels
RUN pip install --no-index --find-links=/opt/wheels -r requirements.txt

# Código de inference e entrypoint
COPY inference.py /opt/program/inference.py
COPY serve /usr/local/bin/serve
RUN chmod +x /usr/local/bin/serve

EXPOSE 8080
ENTRYPOINT ["serve"]
