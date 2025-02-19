#!/bin/bash

echo "正在创建项目目录..."
ssh root@8.130.132.215 "mkdir -p /var/www/MaogeToolbox"

echo "正在复制项目文件..."
scp -r ./* root@8.130.132.215:/var/www/MaogeToolbox/

echo "正在配置Python环境..."
ssh root@8.130.132.215 "cd /var/www/MaogeToolbox && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt gunicorn"

echo "正在配置Nginx..."
ssh root@8.130.132.215 "cat > /etc/nginx/conf.d/maoge.conf << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location /static {
        alias /var/www/MaogeToolbox/static;
    }

    client_max_body_size 16M;
}
EOF"

echo "正在配置系统服务..."
ssh root@8.130.132.215 "cat > /etc/systemd/system/maoge.service << 'EOF'
[Unit]
Description=Maoge Toolbox
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/MaogeToolbox
Environment=\"PATH=/var/www/MaogeToolbox/venv/bin\"
ExecStart=/var/www/MaogeToolbox/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app

[Install]
WantedBy=multi-user.target
EOF"

echo "正在启动服务..."
ssh root@8.130.132.215 "systemctl daemon-reload && systemctl enable nginx && systemctl enable maoge && systemctl restart nginx && systemctl restart maoge"

echo "部署完成！"
