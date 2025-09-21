"""
SQLite settings for testing
"""
from .settings import *
import os

# Use SQLite for testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Disable some production features for testing
DEBUG = False
ALLOWED_HOSTS = ['*']
