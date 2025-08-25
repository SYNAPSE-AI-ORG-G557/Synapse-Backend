# In: Synapse-Worker/src/worker.py

from celery import Celery
from src.core.config import settings  # Import settings from your config file

# Define the Celery application instance with the standard name 'app'
app = Celery(
    "synapse_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    # This tells Celery where to find your task modules
    include=["src.tasks.cpu_light_tasks", "src.tasks.cpu_heavy_tasks", "src.tasks.gpu_heavy_tasks"]
)

# This is the key part for routing tasks to different workers
app.conf.task_routes = {
    'src.tasks.gpu_heavy_tasks.*': {'queue': 'gpu'},
    'src.tasks.cpu_heavy_tasks.*': {'queue': 'cpu_heavy'},
    'src.tasks.cpu_light_tasks.*': {'queue': 'cpu_light'},
}

app.conf.update(task_track_started=True)
