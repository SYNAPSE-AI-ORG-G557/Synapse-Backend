# In: Synapse-Backend/src/core/celery_app.py

from celery import Celery
from src.core.config import settings # Import settings from your config file

# This is just a client for sending tasks, it connects to the same broker
celery_app = Celery(
    "synapse_backend",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)