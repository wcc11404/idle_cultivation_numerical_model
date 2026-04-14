#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

PORT="${PORT:-8501}"
HOST="${HOST:-localhost}"

if [ ! -d "venv" ]; then
  echo "[restart] venv 不存在，正在创建..."
  python3 -m venv venv
fi

if [ ! -x "venv/bin/streamlit" ]; then
  echo "[restart] 正在安装依赖..."
  ./venv/bin/pip install -r requirements.txt
fi

OLD_PID="$(lsof -tiTCP:${PORT} -sTCP:LISTEN || true)"
if [ -n "${OLD_PID}" ]; then
  echo "[restart] 关闭旧进程: ${OLD_PID}"
  kill ${OLD_PID} || true
  sleep 1
fi

echo "[restart] 启动 Streamlit (热加载开启) -> http://${HOST}:${PORT}"
exec ./venv/bin/streamlit run app.py \
  --server.address "${HOST}" \
  --server.port "${PORT}" \
  --server.headless true \
  --server.runOnSave true
