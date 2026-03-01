#!/bin/bash
# Railway startup script that properly handles PORT environment variable

PORT=${PORT:-8000}
echo "Starting server on port $PORT"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
