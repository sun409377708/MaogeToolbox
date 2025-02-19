#!/bin/bash

# 服务器信息
SERVER="root@8.130.132.215"
PROJECT_NAME="MaogeToolbox"
REMOTE_DIR="/var/www/$PROJECT_NAME"

echo "开始部署..."

# 连接服务器并执行命令
ssh $SERVER << 'ENDSSH'
# 安装必要的软件
yum update -y
yum install -y python3 python3-pip nginx git

# 创建项目目录
mkdir -p /var/www/MaogeToolbox
cd /var/www/MaogeToolbox

# 克隆或更新代码
if [ -d ".git" ]; then
    git pull
else
    git clone https://github.com/sun409377708/MaogeToolbox.git .
fi

# 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install gunicorn

# 配置 Nginx
cat > /etc/nginx/conf.d/maoge.conf << 'ENDNGINX'
server {
    listen 80;
    server_name _;  # 替换为你的域名

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/MaogeToolbox/static;
        expires 30d;
    }

    client_max_body_size 16M;
}
ENDNGINX

# 创建 systemd 服务文件
cat > /etc/systemd/system/maoge.service << 'ENDSERVICE'
[Unit]
Description=Maoge Toolbox
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/MaogeToolbox
Environment="PATH=/var/www/MaogeToolbox/venv/bin"
ExecStart=/var/www/MaogeToolbox/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app

[Install]
WantedBy=multi-user.target
ENDSERVICE

# 创建上传目录并设置权限
mkdir -p /var/www/MaogeToolbox/uploads
chmod 755 /var/www/MaogeToolbox/uploads

# 重启服务
systemctl daemon-reload
systemctl enable nginx
systemctl enable maoge
systemctl restart nginx
systemctl restart maoge

echo "部署完成！"
ENDSSH
