#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

PORT="${PORT:-8501}"
HOST="${HOST:-127.0.0.1}"

if [ ! -d "venv" ]; then
  echo "[restart] venv 不存在，正在创建..."
  python3 -m venv venv
fi

if [ "$(uname)" = "Darwin" ]; then
  DEFAULT_CA_FILE="/Library/Frameworks/Python.framework/Versions/3.12/etc/openssl/cert.pem"
  if [ ! -f "$DEFAULT_CA_FILE" ] && [ -f "/etc/ssl/cert.pem" ]; then
    echo "[restart] 检测到 Python 证书缺失，使用系统证书 /etc/ssl/cert.pem"
    export SSL_CERT_FILE="/etc/ssl/cert.pem"
    export REQUESTS_CA_BUNDLE="/etc/ssl/cert.pem"
    export PIP_CERT="/etc/ssl/cert.pem"
  fi
fi

if ! ./venv/bin/python -c "import fastapi, uvicorn, pandas, pytest" >/dev/null 2>&1; then
  echo "[restart] 正在安装 Python 依赖..."
  ./venv/bin/pip install -r requirements.txt
fi

if [ ! -d "web/node_modules" ]; then
  echo "[restart] 正在安装前端依赖..."
  (cd web && npm install)
fi

echo "[restart] 构建 React 前端..."
(cd web && npm run build)

OLD_PID="$(lsof -tiTCP:${PORT} -sTCP:LISTEN || true)"
if [ -n "${OLD_PID}" ]; then
  echo "[restart] 关闭旧进程: ${OLD_PID}"
  kill ${OLD_PID} || true
  sleep 1
fi

echo "[restart] 启动 FastAPI + React -> http://${HOST}:${PORT}"
exec ./venv/bin/python -m uvicorn backend.app:app \
  --host "${HOST}" \
  --port "${PORT}"
