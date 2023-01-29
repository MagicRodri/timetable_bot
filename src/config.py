import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# GENERAL
ACADEMIC_YEAR = "2022/2023"
DEBUG = bool(int(os.getenv('DEBUG')))

# Telegram
TG_TOKEN = os.getenv('TG_TOKEN')
SECRET_KEY = os.getenv('SECRET_KEY')

# Database
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME')

# Redis
REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = os.getenv('REDIS_PORT')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

# Celery
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')

# Browserstack
BROWSERSTACK_USERNAME = os.getenv('BROWSERSTACK_USERNAME')
BROWSERSTACK_ACCESS_KEY = os.getenv('BROWSERSTACK_ACCESS_KEY')

#Render
URL = os.getenv('URL')
PORT = os.getenv('PORT')