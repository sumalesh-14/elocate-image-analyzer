#!/bin/bash
# Get PORT from Railway (required)
PORT=${PORT:-8000}

echo "Starting server on port $PORT"
echo "Host: 0.0.0.0"

# Start uvicorn with explicit port
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --log-level info