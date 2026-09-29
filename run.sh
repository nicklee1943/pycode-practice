#!/usr/bin/env bash
# PyCode 練習：Ubuntu / Linux / macOS 啟動腳本
# 用法：./run.sh [--port 5000] [--host 127.0.0.1] [--no-browser]
# 需求：Python 3.10 以上（Ubuntu 22.04 / 24.04 內建），不需要 pip install、不需要網路
set -e
cd "$(dirname "$0")"
export PYTHONUTF8=1

PY=""
for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1 && \
       "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        PY="$cand"
        break
    fi
done

if [ -z "$PY" ]; then
    echo "找不到 Python 3.10 以上的版本。"
    echo "Ubuntu 請執行：sudo apt install python3"
    exit 1
fi

# 沒有圖形介面（例如 SSH 連線）時不要嘗試開瀏覽器
if [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ] && [ "$(uname)" != "Darwin" ]; then
    set -- --no-browser "$@"
fi

exec "$PY" launcher.py "$@"
