#!/bin/bash

# 删除不再需要的文件
echo "正在清理不需要的文件..."
rm -f DEPLOY.md
rm -f deploy_simple.sh
rm -f gunicorn_config.py
rm -f start.sh
rm -f update.sh

# 删除 Python 缓存文件
echo "正在清理 Python 缓存文件..."
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -delete

# 删除临时文件
echo "正在清理临时文件..."
find . -type d -name ".pytest_cache" -delete
find . -type d -name ".coverage" -delete
rm -rf .coverage
rm -rf htmlcov

echo "清理完成！"

echo "Cleaning up Python processes..."
pkill -f "python app.py"

echo "Checking port 8000..."
if lsof -i :8000 > /dev/null; then
    echo "Port 8000 is still in use. Please check manually with: lsof -i :8000"
    exit 1
else
    echo "Port 8000 is available"
fi
