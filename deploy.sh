#!/bin/bash

# 错误处理函数
handle_error() {
    echo "错误: $1"
    exit 1
}

# 检查命令执行状态
check_status() {
    if [ $? -ne 0 ]; then
        handle_error "$1"
    fi
}

# 设置变量
SERVER="root@8.130.132.215"
REMOTE_DIR="/var/www/MaogeToolbox"
LOCAL_DIR="/Users/jianqin/Desktop/craeDemo/imageCompression"

echo "=== 开始部署 ==="

# 检查本地文件
echo "检查本地文件..."
[ -f "$LOCAL_DIR/requirements.txt" ] || handle_error "requirements.txt 不存在"
[ -f "$LOCAL_DIR/app.py" ] || handle_error "app.py 不存在"
[ -f "$LOCAL_DIR/gunicorn.service" ] || handle_error "gunicorn.service 不存在"
[ -f "$LOCAL_DIR/nginx.conf" ] || handle_error "nginx.conf 不存在"

# 创建远程目录
echo "创建远程目录..."
ssh $SERVER "mkdir -p $REMOTE_DIR"
check_status "创建远程目录失败"

# 同步文件到服务器
echo "同步文件到服务器..."
rsync -avz --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'venv' \
    --exclude '.env' \
    $LOCAL_DIR/ $SERVER:$REMOTE_DIR/
check_status "文件同步失败"

# 在服务器上执行部署命令
echo "在服务器上执行部署..."
ssh $SERVER "bash -s" << 'ENDSSH'
    set -e  # 遇到错误立即退出

    echo "=== 服务器端部署开始 ==="
    
    # 安装系统依赖
    echo "更新系统包..."
    sudo yum update -y
    sudo yum install -y python3-devel gcc nginx
    sudo yum groupinstall -y "Development Tools"

    # 进入项目目录
    cd /var/www/MaogeToolbox

    # 创建并激活虚拟环境
    echo "设置 Python 虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate

    # 配置 pip 使用国内镜像
    echo "配置 pip 镜像..."
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

    # 安装依赖（带重试机制）
    echo "安装 Python 依赖..."
    max_retries=3
    retry_count=0
    while [ $retry_count -lt $max_retries ]; do
        if pip install -r requirements.txt; then
            break
        fi
        retry_count=$((retry_count + 1))
        echo "依赖安装失败，尝试重试 ($retry_count/$max_retries)..."
        sleep 5
    done
    if [ $retry_count -eq $max_retries ]; then
        echo "依赖安装失败，已达到最大重试次数"
        exit 1
    fi

    # 验证依赖安装
    echo "验证依赖安装..."
    python3 -c "import jieba" || { echo "jieba 模块导入失败"; exit 1; }
    python3 -c "import flask" || { echo "flask 模块导入失败"; exit 1; }
    python3 -c "import gunicorn" || { echo "gunicorn 模块导入失败"; exit 1; }

    # 清理旧的 Nginx 配置
    echo "配置 Nginx..."
    sudo rm -f /etc/nginx/conf.d/*.conf.bak
    sudo rm -f /etc/nginx/conf.d/compress.conf
    sudo rm -f /etc/nginx/conf.d/default.conf

    # 配置 Nginx
    sudo cp nginx.conf /etc/nginx/conf.d/maoge.conf
    sudo nginx -t || { echo "Nginx 配置测试失败"; exit 1; }
    sudo systemctl restart nginx

    # 创建日志目录
    echo "设置日志目录..."
    sudo mkdir -p /var/log/gunicorn
    sudo chown -R root:root /var/log/gunicorn

    # 确保上传目录存在并设置权限
    echo "设置上传目录..."
    mkdir -p uploads
    chmod 755 uploads

    # 停止旧的 Gunicorn 进程
    echo "重启 Gunicorn..."
    pkill gunicorn || true

    # 配置 Gunicorn 系统服务
    sudo cp gunicorn.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable gunicorn
    sudo systemctl restart gunicorn

    # 验证服务状态
    echo "验证服务状态..."
    sudo systemctl is-active --quiet nginx || { echo "Nginx 服务未运行"; exit 1; }
    sudo systemctl is-active --quiet gunicorn || { echo "Gunicorn 服务未运行"; exit 1; }

    # 检查端口
    echo "检查端口..."
    netstat -tlpn | grep -q ':80' || { echo "Nginx 端口 (80) 未监听"; exit 1; }
    netstat -tlpn | grep -q ':5001' || { echo "Gunicorn 端口 (5001) 未监听"; exit 1; }

    echo "=== 服务器端部署完成 ==="
ENDSSH

check_status "服务器端部署失败"

echo "=== 部署成功完成 ==="
echo "您现在可以访问："
echo "- HTTPS: https://jianqin.fun"
echo "- HTTP: http://8.130.132.215"
