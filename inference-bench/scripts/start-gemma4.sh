#!/usr/bin/env bash
# start-gemma4.sh — Start Gemma 4 on vLLM
# Usage: GEMMA4_MODEL=E2B bash start-gemma4.sh
#        GEMMA4_MODEL=E4B bash start-gemma4.sh
set -euo pipefail

VLLM_DIR="${VLLM_DIR:-/opt/vllm}"
GEMMA_DIR="${GEMMA_DIR:-/opt/gemma4}"
PORT="${GEMMA4_PORT:-3000}"
MODEL_VARIANT="${GEMMA4_MODEL:-E2B}"
CTX="${GEMMA4_CTX:-2048}"
GPU_UTIL="${GEMMA4_GPU_UTIL:-0.90}"

export PATH="$VLLM_DIR/.venv/bin:$HOME/.local/bin:$PATH"
export HF_HOME="$GEMMA_DIR/hf_cache"

case "$MODEL_VARIANT" in
    E2B|e2b) MODEL_ID="google/gemma-4-E2B-it" ;;
    E4B|e4b) MODEL_ID="google/gemma-4-E4B-it" ;;
    *)       MODEL_ID="$MODEL_VARIANT" ;;
esac

# Stop existing
pkill -f "vllm.entrypoints.*$PORT" 2>/dev/null || true
sleep 2

echo "=== Starting Gemma 4 ($MODEL_VARIANT) ==="
echo "Model: $MODEL_ID"
echo "Port: $PORT"
echo "Context: $CTX"
echo "GPU util: $GPU_UTIL"

mkdir -p "$GEMMA_DIR"
nohup python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_ID" \
    --host 0.0.0.0 \
    --port "$PORT" \
    --dtype bfloat16 \
    --gpu-memory-utilization "$GPU_UTIL" \
    --max-model-len "$CTX" \
    --max-num-seqs 2 \
    > "$GEMMA_DIR/server.log" 2>&1 &

PID=$!
echo "PID: $PID"

echo "Waiting for server (model download may take a while)..."
MAX_WAIT=600
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s "http://localhost:$PORT/v1/models" 2>/dev/null | grep -q "id"; then
        echo "Ready on port $PORT (${WAITED}s)"
        echo "Serving: $(curl -s "http://localhost:$PORT/v1/models" | jq -r '.data[0].id' 2>/dev/null)"
        echo "GPU: $(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader 2>/dev/null)"
        exit 0
    fi
    if ! kill -0 "$PID" 2>/dev/null; then
        echo "ERROR: Server died"
        tail -20 "$GEMMA_DIR/server.log"
        exit 1
    fi
    sleep 10
    WAITED=$((WAITED + 10))
    if [ $((WAITED % 60)) -eq 0 ]; then echo "  ...waiting (${WAITED}s)"; fi
done

echo "WARNING: Server not ready after ${MAX_WAIT}s"
tail -10 "$GEMMA_DIR/server.log"
