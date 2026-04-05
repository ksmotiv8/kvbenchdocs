#!/usr/bin/env bash
# stop-all.sh — Stop all inference servers
set -euo pipefail

echo "=== Stopping all servers ==="

# SGLang
if [ -f /opt/sglang/server.pid ]; then
    bash /opt/sglang/scripts/stop.sh 2>/dev/null || true
fi
pkill -f "sglang.launch_server" 2>/dev/null || true

# Bonsai (llama.cpp)
pkill -f "llama-server" 2>/dev/null || true

# vLLM (Gemma 4)
pkill -f "vllm.entrypoints" 2>/dev/null || true

sleep 3
echo "GPU: $(nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader 2>/dev/null)"
echo "Done"
