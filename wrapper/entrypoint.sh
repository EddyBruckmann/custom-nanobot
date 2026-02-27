#!/bin/bash
set -e

# Copiar routing.json si no existe en el volumen
if [ ! -f /root/.nanobot/routing.json ]; then
    cp /app/routing.json.default /root/.nanobot/routing.json
fi

echo "=== Starting NanoBot gateway (background) ==="
nanobot gateway &
GATEWAY_PID=$!

sleep 5

echo "=== Starting memory manager (background) ==="
python3 /app/memory_manager.py &
MEMORY_PID=$!

echo "=== Starting wrapper HTTP server (foreground) ==="
python3 /app/nanobot_wrapper.py

kill $GATEWAY_PID 2>/dev/null
kill $MEMORY_PID 2>/dev/null
