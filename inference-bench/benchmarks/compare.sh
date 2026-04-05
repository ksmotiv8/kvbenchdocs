#!/usr/bin/env bash
# compare.sh — Run latency + quality benchmarks across two servers side by side
# Usage: bash compare.sh [port_a] [model_a] [port_b] [model_b]
#        bash compare.sh 3000 google/gemma-4-E2B-it 3001 default
set -eo pipefail

PORT_A="${1:-3000}"
MODEL_A="${2:-default}"
PORT_B="${3:-3001}"
MODEL_B="${4:-default}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SERVING_A=$(curl -s "http://localhost:${PORT_A}/v1/models" | jq -r '.data[0].id' 2>/dev/null)
SERVING_B=$(curl -s "http://localhost:${PORT_B}/v1/models" | jq -r '.data[0].id' 2>/dev/null)

echo "================================================================"
echo "  COMPARISON BENCHMARK"
echo "  A: $SERVING_A (port $PORT_A)"
echo "  B: $SERVING_B (port $PORT_B)"
echo "================================================================"
echo ""

echo "===== LATENCY: $SERVING_A ====="
bash "$SCRIPT_DIR/latency.sh" "$PORT_A" "$MODEL_A"
echo ""

echo "===== LATENCY: $SERVING_B ====="
bash "$SCRIPT_DIR/latency.sh" "$PORT_B" "$MODEL_B"
echo ""

echo "===== QUALITY: $SERVING_A ====="
bash "$SCRIPT_DIR/quality.sh" "$PORT_A" "$MODEL_A"
echo ""

echo "===== QUALITY: $SERVING_B ====="
bash "$SCRIPT_DIR/quality.sh" "$PORT_B" "$MODEL_B"
