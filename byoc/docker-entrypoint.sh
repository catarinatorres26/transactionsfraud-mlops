#!/usr/bin/env bash
set -e

if [[ "$1" == "serve" ]]; then
  exec /usr/local/bin/serve
elif [[ "$1" == "train" ]]; then
  # não usado aqui, mas mantém compatibilidade
  shift
  exec python -m train_sm "$@"
else
  # se o SageMaker passar só "serve" como CMD, isto ainda funciona;
  # e se passar outra coisa, tentamos executar diretamente
  exec "$@"
fi
