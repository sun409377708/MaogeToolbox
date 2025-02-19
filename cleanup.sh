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
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# 删除临时文件
echo "正在清理临时文件..."
rm -rf .pytest_cache
rm -rf .coverage
rm -rf htmlcov

echo "清理完成！"
