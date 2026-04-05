#!/usr/bin/env bash
# start-bonsai.sh — Start Bonsai 1-bit 8B on llama.cpp
set -euo pipefail

BONSAI_DIR="${BONSAI_DIR:-/opt/bonsai}"
PORT="${BONSAI_PORT:-3001}"
CTX="${BONSAI_CTX:-2048}"
SERVER="$BONSAI_DIR/llama.cpp/build/bin/llama-server"
MODEL="$BONSAI_DIR/models/Bonsai-8B-gguf/Bonsai-8B.gguf"
LOG="$BONSAI_DIR/server.log"

[ -f "$SERVER" ] || { echo "ERROR: llama-server not found. Run setup-bonsai.sh first."; exit 1; }
[ -f "$MODEL" ] || { echo "ERROR: Model not found. Run setup-bonsai.sh first."; exit 1; }

# Stop existing
pkill -f "llama-server.*$PORT" 2>/dev/null || true
sleep 1

echo "=== Starting Bonsai 1-bit 8B ==="
echo "Model: $MODEL ($(du -sh "$MODEL" | cut -f1))"
echo "Port: $PORT"

nohup "$SERVER" \
    --model "$MODEL" \
    --host 0.0.0.0 \
    --port "$PORT" \
    --n-gpu-layers 99 \
    --ctx-size "$CTX" \
    --threads 4 \
    --log-disable \
    > "$LOG" 2>&1 &

PID=$!
echo "PID: $PID"

for i in $(seq 1 30); do
    if curl -s "http://localhost:$PORT/v1/models" 2>/dev/null | grep -q "id"; then
        echo "Ready on port $PORT (${i}s)"
        echo "GPU: $(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader 2>/dev/null)"
        exit 0
    fi
    sleep 2
done

echo "WARNING: Server may not be ready"
