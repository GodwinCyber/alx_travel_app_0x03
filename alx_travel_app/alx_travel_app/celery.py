"""
Celery configuration for the travel app
This integrate Celery with Django and RabbitMQ for asynchronous task process
"""

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_travel_app.settings')

# Create Celery App instance
app = Celery('alx_travel_app')

# Load configuration from djnago settings with celery prefix
# app.config_from_object('django.conf:settings', namespace='CELERY')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover task in installed apps
app.autodiscover_tasks()


