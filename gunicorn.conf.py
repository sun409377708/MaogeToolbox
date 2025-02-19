import multiprocessing

# 绑定的ip与端口
bind = "127.0.0.1:5001"

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
loglevel = 'info'

# 后台运行
daemon = True

# 超时时间
timeout = 30

# 重启间隔
graceful_timeout = 30

# 环境变量
raw_env = [
    'DEEPSEEK_API_KEY=sk-9dfa947798e84808a42a351cf41d80c1'
]
