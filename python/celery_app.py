from celery import Celery

app = Celery(
    "tasks",
    broker="redis://redis:6379/0"
)

app.conf.beat_schedule = {
    "1m": {"task": "tasks.agg_1m", "schedule": 60},
    "5m": {"task": "tasks.agg_5m", "schedule": 300},
    "60m": {"task": "tasks.agg_60m", "schedule": 3600},
}