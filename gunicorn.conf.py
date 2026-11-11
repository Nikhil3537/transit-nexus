"""Production Gunicorn defaults for the Transit Nexus web process."""
import os


bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv("WEB_CONCURRENCY", "4"))
threads = int(os.getenv("WEB_THREADS", "4"))
worker_class = "gthread"
timeout = int(os.getenv("WEB_TIMEOUT", "300"))
keepalive = 5
preload_app = True
max_requests = 1000
max_requests_jitter = 100
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
