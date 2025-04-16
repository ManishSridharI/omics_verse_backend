# app/celery.py

from celery import Celery

def make_celery(app=None):
    celery = Celery(
        'app',
        broker='redis://redis:6379/0',
        backend='redis://redis:6379/0'
        # include=['app.mixomics_tasks']
    )
    
    # Configure Celery settings
    celery.conf.update(
        result_expires=3600,  # Results expire after 1 hour
        worker_prefetch_multiplier=1,  # One task per worker at a time
        task_acks_late=True,  # Acknowledge tasks after execution
        task_track_started=True,  # Track when tasks are started
    )
    
    if app:
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        
        celery.Task = ContextTask
    
    return celery

# # This is the Celery instance that will be imported by the worker process
# celery = make_celery()

# # This function will be called by the Flask app to initialize Celery with the Flask app context
# def init_celery(app):
#     celery = make_celery(app)
#     return celery