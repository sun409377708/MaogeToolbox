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
    sudo yum install -y epel-release
    
    # 安装 Nginx
    echo "安装 Nginx..."
    sudo yum install -y nginx
    sudo systemctl enable nginx
    sudo systemctl start nginx
    
    # 安装 Python 3.9
    echo "安装 Python 3.9..."
    sudo yum install -y gcc openssl-devel bzip2-devel libffi-devel
    sudo yum install -y python39 python39-devel
    
    # 安装其他系统依赖
    echo "安装系统依赖..."
    for pkg in libjpeg-devel \
        zlib-devel \
        freetype-devel \
        libffi-devel \
        cairo-devel \
        pango-devel \
        libpng-devel \
        libtiff-devel \
        openssl-devel \
        lcms2-devel \
        openjpeg2-devel \
        harfbuzz-devel \
        fribidi-devel \
        libraqm-devel \
        libxml2-devel \
        libxslt-devel; do
        echo "安装 $pkg..."
        sudo yum install -y $pkg || echo "警告: $pkg 安装失败，继续安装其他包..."
    done

    # 进入项目目录
    cd /var/www/MaogeToolbox

    # 创建并激活虚拟环境
    echo "设置 Python 虚拟环境..."
    python3.9 -m venv venv
    source venv/bin/activate

    # 升级 pip
    echo "升级 pip..."
    python3.9 -m pip install --upgrade pip setuptools wheel

    # 配置 pip 使用国内镜像
    echo "配置 pip 镜像..."
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

    # 安装依赖（带重试机制和详细日志）
    echo "安装 Python 依赖..."
    max_retries=3
    retry_count=0
    while [ $retry_count -lt $max_retries ]; do
        if pip install -v -r requirements.txt 2>&1 | tee pip_install.log; then
            break
        fi
        retry_count=$((retry_count + 1))
        echo "依赖安装失败，尝试重试 ($retry_count/$max_retries)..."
        echo "错误日志："
        tail -n 50 pip_install.log
        sleep 5
    done
    if [ $retry_count -eq $max_retries ]; then
        echo "依赖安装失败，已达到最大重试次数"
        echo "完整错误日志："
        cat pip_install.log
        exit 1
    fi

    # 验证依赖安装
    echo "验证依赖安装..."
    python3.9 -c "import jieba" || { echo "jieba 模块导入失败"; exit 1; }
    python3.9 -c "import flask" || { echo "flask 模块导入失败"; exit 1; }
    python3.9 -c "import gunicorn" || { echo "gunicorn 模块导入失败"; exit 1; }

    # 清理旧的 Nginx 配置
    echo "配置 Nginx..."
    sudo rm -f /etc/nginx/conf.d/*.conf.bak
    sudo rm -f /etc/nginx/conf.d/compress.conf
    sudo rm -f /etc/nginx/conf.d/default.conf

    # 配置 Nginx
    sudo cp nginx.conf /etc/nginx/conf.d/maoge.conf
    sudo nginx -t || { echo "Nginx 配置测试失败"; exit 1; }
    sudo systemctl restart nginx

    # 设置项目目录权限
    echo "设置目录权限..."
    sudo chown -R root:root /var/www/MaogeToolbox
    sudo chmod -R 755 /var/www/MaogeToolbox
    sudo chmod -R 777 /var/www/MaogeToolbox/uploads  # 确保上传目录可写

    # 确保日志目录存在并设置权限
    echo "设置日志目录..."
    sudo mkdir -p /var/log/gunicorn
    sudo chown -R root:root /var/log/gunicorn
    sudo chmod -R 755 /var/log/gunicorn

    # 配置 Gunicorn 系统服务
    echo "配置 Gunicorn 服务..."
    sudo cp gunicorn.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable gunicorn
    sudo systemctl restart gunicorn
    sleep 5  # 等待服务启动

    # 检查 Gunicorn 状态
    echo "检查 Gunicorn 状态..."
    sudo systemctl status gunicorn
    sudo journalctl -u gunicorn --no-pager -n 50

    # 验证服务状态
    echo "验证服务状态..."
    if ! sudo systemctl is-active --quiet nginx; then
        echo "Nginx 服务未运行"
        sudo systemctl status nginx
        exit 1
    fi

    if ! sudo systemctl is-active --quiet gunicorn; then
        echo "Gunicorn 服务未运行"
        sudo systemctl status gunicorn
        sudo journalctl -u gunicorn --no-pager -n 50
        exit 1
    fi

    # 检查端口
    echo "检查端口..."
    if ! netstat -tlpn | grep -q ':80'; then
        echo "Nginx 端口 (80) 未监听"
        sudo systemctl status nginx
        exit 1
    fi

    if ! netstat -tlpn | grep -q ':5001'; then
        echo "Gunicorn 端口 (5001) 未监听"
        sudo systemctl status gunicorn
        sudo journalctl -u gunicorn --no-pager -n 50
        sudo netstat -tlpn
        exit 1
    fi

    echo "=== 服务器端部署完成 ==="
ENDSSH

check_status "服务器端部署失败"

echo "=== 部署成功完成 ==="
echo "您现在可以访问："
echo "- HTTPS: https://jianqin.fun"
echo "- HTTP: http://8.130.132.215"
