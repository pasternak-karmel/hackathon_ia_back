import os
import logging
from logging.handlers import RotatingFileHandler
from django.conf import settings

# Create logs directory if it doesn't exist
logs_dir = os.path.join(settings.BASE_DIR, 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Vérification et correction des permissions (facultatif)
if not os.access(logs_dir, os.W_OK):
    os.chmod(logs_dir, 0o777)  # Donne tous les droits en dev


# Configure authentication logger
auth_logger = logging.getLogger('authentication')
auth_logger.setLevel(logging.INFO)

# Create handlers
auth_file_handler = RotatingFileHandler(
    os.path.join(logs_dir, 'authentication.log'),
    maxBytes=10485760,  # 10MB
    backupCount=5,
    encoding='utf-8'
)

# Create formatters and add it to handlers
log_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
auth_file_handler.setFormatter(log_formatter)

# Add handlers to the logger
auth_logger.addHandler(auth_file_handler)

# Function to get the authentication logger
def get_auth_logger():
    return auth_logger