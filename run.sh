#!/bin/bash
# 自动激活虚拟环境并设置PYTHONPATH，运行传入的python脚本

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
source "$SCRIPT_DIR/venv/bin/activate"
export PYTHONPATH="$SCRIPT_DIR"
python "$@" 