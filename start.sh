#!/bin/bash
# Get PORT from Railway (required)
PORT=${PORT:-8000}

echo "Starting server on port $PORT"
echo "Host: 0.0.0.0"

# Start via run.py which handles PORT variable correctly
python run.py