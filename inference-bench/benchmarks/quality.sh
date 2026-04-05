#!/usr/bin/env bash
# quality.sh — Run quality benchmarks against any OpenAI-compatible server
# Tests factual knowledge, reasoning, code correctness, instruction following
# Usage: bash quality.sh [port] [model_name]
set -eo pipefail

PORT="${1:-3000}"
MODEL="${2:-default}"
URL="http://localhost:${PORT}"

for cmd in curl jq python3; do
    command -v "$cmd" &>/dev/null || { echo "Error: $cmd required"; exit 1; }
done

curl -s "${URL}/v1/models" 2>/dev/null | grep -q "id" || { echo "ERROR: No server on port $PORT"; exit 1; }
SERVING=$(curl -s "${URL}/v1/models" | jq -r '.data[0].id' 2>/dev/null)

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

query() {
    local sys="$1" prompt="$2" out="$3"
    local body
    body=$(jq -n --arg m "$MODEL" --arg s "$sys" --arg p "$prompt" \
        '{model:$m,messages:[{role:"system",content:$s},{role:"user",content:$p}],max_tokens:256,temperature:0,stream:false}')
    curl -s -X POST "${URL}/v1/chat/completions" -H "Content-Type: application/json" -d "$body" > "$out" 2>/dev/null
    jq -r '.choices[0].message.content // "ERROR"' "$out" 2>/dev/null
}

SYS="Answer accurately and concisely."
PASS=0
TOTAL=0

echo "================================================================"
echo "  QUALITY BENCHMARK"
echo "  Model: $SERVING (port $PORT)"
echo "================================================================"
echo ""

check() {
    local label="$1" expected="$2" actual="$3"
    TOTAL=$((TOTAL + 1))
    if echo "$actual" | grep -qi "$expected"; then
        PASS=$((PASS + 1))
        printf "  [PASS] %s\n" "$label"
    else
        printf "  [FAIL] %s\n" "$label"
    fi
    printf "    Answer: %s\n\n" "$(echo "$actual" | head -1 | cut -c1-100)"
}

echo "--- FACTUAL KNOWLEDGE ---"
A=$(query "$SYS" "What does AWQ stand for in the context of LLM quantization? Just the full name." "$TMPDIR/q1")
check "Q1: AWQ full name" "activation-aware" "$A"

A=$(query "$SYS" "What is the computational complexity of self-attention with respect to sequence length n? Give Big-O." "$TMPDIR/q2")
check "Q2: Self-attention complexity" "n.2" "$A"

A=$(query "$SYS" "In the transformer architecture, what are the three matrices in attention? Name them." "$TMPDIR/q3")
check "Q3: Q/K/V matrices" "query" "$A"

A=$(query "$SYS" "What is CUDA graph capture used for in inference engines? One sentence." "$TMPDIR/q4")
check "Q4: CUDA graph capture" "record\|replay\|overhead\|kernel" "$A"

A=$(query "$SYS" "What year was 'Attention Is All You Need' published? Just the year." "$TMPDIR/q5")
check "Q5: Transformer paper year" "2017" "$A"

echo "--- REASONING ---"
A=$(query "$SYS" "A GPU has 300 GB/s memory bandwidth. A model is 16 GB. How many tokens/s if each token reads the full model? Ignore compute." "$TMPDIR/q7")
check "Q6: Bandwidth to tok/s" "18.75\|18\.7" "$A"

echo "--- INSTRUCTION FOLLOWING ---"
A=$(query "$SYS" "List exactly 5 programming languages. Number them 1-5. No descriptions, just names." "$TMPDIR/q10")
TOTAL=$((TOTAL + 1))
COUNT=$(echo "$A" | grep -cE "^[0-9]" 2>/dev/null || echo 0)
if [ "$COUNT" -eq 5 ]; then PASS=$((PASS + 1)); printf "  [PASS] Q7: List 5 languages\n"; else printf "  [FAIL] Q7: List 5 languages (got $COUNT)\n"; fi
printf "    Answer: %s\n\n" "$(echo "$A" | head -1 | cut -c1-100)"

A=$(query "Respond with exactly one word: yes or no." "Is Python dynamically typed?" "$TMPDIR/q11")
check "Q8: Yes/no answer" "^yes$\|^Yes$" "$A"

A=$(query "Output only valid JSON, nothing else." "Create a JSON object with keys 'name' and 'language'. name is 'Qwen', language is 'Chinese'." "$TMPDIR/q12")
TOTAL=$((TOTAL + 1))
if echo "$A" | python3 -c 'import sys,json; json.load(sys.stdin)' 2>/dev/null; then
    PASS=$((PASS + 1)); printf "  [PASS] Q9: Valid JSON output\n"
else
    printf "  [FAIL] Q9: Valid JSON output\n"
fi
printf "    Answer: %s\n\n" "$(echo "$A" | head -1 | cut -c1-80)"

echo "================================================================"
echo "  SCORE: $PASS / $TOTAL"
echo "================================================================"
