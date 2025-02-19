#!/bin/bash

# 设置服务器信息
SERVER="root@8.130.132.215"
DEPLOY_PATH="/var/www/MaogeToolbox"

echo "开始更新代码..."

# 复制更新的文件到服务器
echo "正在复制项目文件..."
scp -r ./* $SERVER:$DEPLOY_PATH/

# 重新安装依赖（如果 requirements.txt 有更新）
echo "正在更新Python依赖..."
ssh $SERVER "cd $DEPLOY_PATH && source venv/bin/activate && pip install -r requirements.txt"

# 重启 Gunicorn 服务
echo "正在重启服务..."
ssh $SERVER "systemctl restart maoge"

echo "更新完成！"
