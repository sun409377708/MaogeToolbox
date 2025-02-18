workers = 4
bind = '0.0.0.0:8000'
timeout = 120
worker_class = 'gevent'
max_requests = 2000
max_requests_jitter = 400
