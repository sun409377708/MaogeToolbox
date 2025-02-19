#!/bin/bash

# 获取脚本所在目录的绝对路径
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 激活虚拟环境（如果存在）
if [ -d "$DIR/.venv" ]; then
    source "$DIR/.venv/bin/activate"
    echo "Activated virtual environment"
fi

# 设置环境变量（可选）
# export PORT=5000

# 启动应用
echo "Starting application..."
python "$DIR/app.py"
