#!/bin/bash
echo "Starting FastAPI Server..."
uvicorn app.main:app --host 0.0.0.0 --port $PORT
