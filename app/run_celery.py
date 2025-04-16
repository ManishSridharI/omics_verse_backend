# app/run_celery.py
from app import celery

if __name__ == '__main__':
    celery.worker_main(['worker', '--loglevel=info'])