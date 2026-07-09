#!/bin/bash

echo "Starting Celery Worker..."
celery -A app.services.celery_app worker --loglevel=info &

echo "Starting Celery Beat..."
celery -A app.services.celery_app beat --loglevel=info &

echo "Starting FastAPI Server..."
uvicorn app.main:app --host 0.0.0.0 --port $PORT
