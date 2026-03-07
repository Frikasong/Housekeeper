import os

bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
workers = 1
timeout = 180
max_requests = 50
max_requests_jitter = 10
