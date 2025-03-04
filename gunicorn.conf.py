import multiprocessing
import os

# 创建日志目录
log_dir = '/var/log/gunicorn'
if not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

# 绑定的ip与端口
bind = "0.0.0.0:5001"

# 工作进程数
workers = multiprocessing.cpu_count() * 2 + 1

# 工作模式
worker_class = 'sync'

# 最大客户端并发数量
worker_connections = 1000

# 进程文件
pidfile = '/var/run/gunicorn.pid'

# 访问日志和错误日志
accesslog = '/var/log/gunicorn/access.log'
errorlog = '/var/log/gunicorn/error.log'

# 日志级别
loglevel = 'debug'

# 超时设置
timeout = 120
keepalive = 2

# 重启设置
max_requests = 2000
max_requests_jitter = 400

# 工作目录
chdir = '/var/www/MaogeToolbox'

# 不要在 daemon 模式下运行，因为我们使用 systemd 管理
daemon = False

# 环境变量
raw_env = [
    'DEEPSEEK_API_KEY=sk-9dfa947798e84808a42a351cf41d80c1'
]
