web: python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
worker: python -m celery -A app.tasks.celery_app worker -l info

