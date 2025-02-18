# 部署说明

## 1. 服务器环境准备

```bash
# 更新系统包
sudo apt-get update
sudo apt-get upgrade

# 安装必要的系统包
sudo apt-get install python3-pip python3-dev nginx git

# 创建应用目录
sudo mkdir -p /var/www/imagecompression
sudo chown -R $USER:$USER /var/www/imagecompression
```

## 2. 部署代码

```bash
# 克隆代码到服务器
cd /var/www/imagecompression
git clone <你的仓库地址> .

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 3. 配置 Nginx

```bash
# 备份默认配置
sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup

# 复制项目的 nginx 配置
sudo cp nginx.conf /etc/nginx/sites-available/imagecompression

# 创建符号链接
sudo ln -s /etc/nginx/sites-available/imagecompression /etc/nginx/sites-enabled/

# 修改 nginx 配置中的域名和路径
sudo nano /etc/nginx/sites-available/imagecompression

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

## 4. 配置 Supervisor 管理应用进程

```bash
# 安装 supervisor
sudo apt-get install supervisor

# 创建配置文件
sudo nano /etc/supervisor/conf.d/imagecompression.conf
```

添加以下内容：
```ini
[program:imagecompression]
directory=/var/www/imagecompression
command=/var/www/imagecompression/venv/bin/gunicorn -c gunicorn_config.py app:app
user=<你的用户名>
autostart=true
autorestart=true
stderr_logfile=/var/log/imagecompression/err.log
stdout_logfile=/var/log/imagecompression/out.log
```

```bash
# 创建日志目录
sudo mkdir -p /var/log/imagecompression
sudo chown -R $USER:$USER /var/log/imagecompression

# 重新加载 supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start imagecompression
```

## 5. 配置域名

1. 在阿里云控制台的域名解析中添加记录：
   - 记录类型: A
   - 主机记录: @ 或者子域名
   - 记录值: 你的服务器 IP
   - TTL: 600

2. 等待 DNS 解析生效（通常需要几分钟到几小时）

## 6. SSL 配置（可选但推荐）

```bash
# 安装 certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取并配置 SSL 证书
sudo certbot --nginx -d your-domain.com
```

## 7. 维护命令

```bash
# 查看应用状态
sudo supervisorctl status imagecompression

# 重启应用
sudo supervisorctl restart imagecompression

# 查看日志
tail -f /var/log/imagecompression/out.log
tail -f /var/log/imagecompression/err.log

# 更新代码
cd /var/www/imagecompression
git pull
sudo supervisorctl restart imagecompression
```

## 注意事项

1. 确保服务器防火墙允许 80 和 443 端口访问
2. 定期备份 uploads 目录
3. 监控服务器资源使用情况
4. 根据需要调整 gunicorn 的 workers 数量
5. 设置日志轮转以防止日志文件过大
