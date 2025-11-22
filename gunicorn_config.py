# Gunicorn configuration file
import os

# Bind to the port that Render provides
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# Worker processes
workers = 2
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "sweet_store_backend"
