#!/usr/bin/env bash
# latency.sh — Run latency benchmarks against any OpenAI-compatible server
# Usage: bash latency.sh [port] [model_name]
#        bash latency.sh 3000 google/gemma-4-E2B-it
#        bash latency.sh 3001 default
set -eo pipefail

PORT="${1:-3000}"
MODEL="${2:-default}"
SYSTEM="You are extremely concise. Max 12 words."
MAX_TOKENS=48
TEMP=0.2
URL="http://localhost:${PORT}"

for cmd in curl jq bc; do
    command -v "$cmd" &>/dev/null || { echo "Error: $cmd required"; exit 1; }
done

curl -s "${URL}/v1/models" 2>/dev/null | grep -q "id" || { echo "ERROR: No server on port $PORT"; exit 1; }

SERVING=$(curl -s "${URL}/v1/models" | jq -r '.data[0].id' 2>/dev/null)

PROMPTS=(
    "What is a KV cache?"
    "Explain attention in transformers"
    "Write a Python function to check if a number is prime"
    "What are the tradeoffs between FP16 and INT4 quantization?"
    "Explain speculative decoding in 2 sentences"
    "What is CUDA graph capture?"
    "How does AWQ quantization work?"
    "Write a bash one-liner to find the largest file in a directory"
)

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

echo "================================================================"
echo "  LATENCY BENCHMARK"
echo "  Model: $SERVING (port $PORT)"
echo "  System: \"$SYSTEM\""
echo "  Max tokens: $MAX_TOKENS | Temp: $TEMP"
echo "================================================================"
echo ""

# Warmup
curl -s -X POST "${URL}/v1/chat/completions" -H "Content-Type: application/json" \
    -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":5,\"temperature\":0}" > /dev/null 2>&1
sleep 1

TOTAL_MS=0
TOTAL_TOK=0

printf "%-50s %8s %5s %8s\n" "Prompt" "ms" "tok" "ms/tok"
echo "────────────────────────────────────────────────────────────────────────"

for PROMPT in "${PROMPTS[@]}"; do
    BODY=$(jq -n --arg m "$MODEL" --arg s "$SYSTEM" --arg p "$PROMPT" \
        --argjson max "$MAX_TOKENS" --argjson temp "$TEMP" \
        '{model:$m,messages:[{role:"system",content:$s},{role:"user",content:$p}],max_tokens:$max,temperature:$temp,stream:false}')

    curl -s -X POST "${URL}/v1/chat/completions" -H "Content-Type: application/json" \
        -w '\n__TIME__%{time_total}' -d "$BODY" > "$TMPDIR/resp" 2>/dev/null

    TIME=$(grep '__TIME__' "$TMPDIR/resp" | sed 's/__TIME__//')
    sed -i '/__TIME__/d' "$TMPDIR/resp"
    TOK=$(jq -r '.usage.completion_tokens // 0' "$TMPDIR/resp" 2>/dev/null)
    MS=$(printf '%.0f' "$(echo "$TIME * 1000" | bc)" 2>/dev/null)
    MSPT="N/A"
    [ "$TOK" -gt 0 ] 2>/dev/null && MSPT=$(echo "scale=1; $MS / $TOK" | bc)

    SHORT=$(echo "$PROMPT" | cut -c1-48)
    printf "%-50s %6sms %4st %6s\n" "$SHORT" "$MS" "$TOK" "$MSPT"

    TOTAL_MS=$((TOTAL_MS + MS))
    TOTAL_TOK=$((TOTAL_TOK + TOK))
done

echo "────────────────────────────────────────────────────────────────────────"
NUM=${#PROMPTS[@]}
AVG=$((TOTAL_MS / NUM))
AVGMSPT="N/A"
[ "$TOTAL_TOK" -gt 0 ] && AVGMSPT=$(echo "scale=1; $TOTAL_MS / $TOTAL_TOK" | bc)
printf "%-50s %6sms %4st %6s\n" "AVERAGE ($NUM prompts)" "$AVG" "$TOTAL_TOK" "$AVGMSPT"
echo ""
echo "GPU: $(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader 2>/dev/null)"
