# celery_app.py
from celery import Celery

celery = Celery(
    'fish_farm',
    broker='redis://localhost:6379/0',      # 或你的 RabbitMQ: 'amqp://guest@localhost//'
    backend='redis://localhost:6379/1'
)
celery.conf.task_routes = {'tasks.*': {'queue': 'video'}}
import tasks
