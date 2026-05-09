import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

app = Celery('medisync')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'run-scheduled-analytics': {
        'task': 'backend.analytics.tasks.run_scheduled_analytics',
        'schedule': 3600.0,  # Run every hour
    },
    'cleanup-old-analytics': {
        'task': 'backend.analytics.tasks.cleanup_old_analytics',
        'schedule': 86400.0,  # Run daily
    },
    'refresh-analytics-cache': {
        'task': 'backend.analytics.tasks.refresh_analytics_cache',
        'schedule': 1800.0,  # Run every 30 minutes
    },
    'auto-close-queues': {
        'task': 'backend.operations.tasks.auto_close_queues',
        'schedule': 300.0,  # Run every 5 minutes
    },
    'retry-failed-notifications': {
        'task': 'backend.operations.tasks.retry_failed_notifications',
        'schedule': 900.0,  # Run every 15 minutes
    },
    'update-queue-statistics': {
        'task': 'backend.operations.tasks.update_queue_statistics',
        'schedule': 120.0,  # Run every 2 minutes
    },
    'process-expired-no-shows': {
        'task': 'backend.operations.tasks.process_expired_no_shows',
        'schedule': 15.0,
    },
}

app.conf.timezone = 'UTC'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
