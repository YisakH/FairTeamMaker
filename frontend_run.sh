#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status

# Set API URL (default to production URL if not provided)
API_URL=${API_URL:-https://maketeam.2esak.com/api}
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-3000}

# Log file path
LOG_FILE="../front.log"

# Ensure data directory exists
mkdir -p data

# Check if frontend directory exists
if [ ! -d "frontend" ]; then
    echo "[ERROR] frontend directory not found."
    exit 1
fi

cd frontend

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "[INFO] node_modules not found. Running npm install..."
    npm install
fi

# Print current settings
echo "[INFO] API URL: $API_URL"
echo "[INFO] Starting React app on $HOST:$PORT"
echo "[INFO] Logs will be written to $LOG_FILE"

# Run React app in background with nohup, and keep it alive after terminal closes
nohup env HOST=$HOST REACT_APP_API_URL=$API_URL PORT=$PORT npm start -- --host $HOST --port $PORT > "$LOG_FILE" 2>&1 &

echo "[SUCCESS] React app started in background. PID: $!"
