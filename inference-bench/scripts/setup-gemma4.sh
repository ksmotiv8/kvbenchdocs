#!/usr/bin/env bash
# setup-gemma4.sh — Install vLLM and prepare Gemma 4 models
# Supports: E2B, E4B variants
set -euo pipefail

echo "=== Gemma 4 Setup ==="

VLLM_DIR="${VLLM_DIR:-/opt/vllm}"
GEMMA_DIR="${GEMMA_DIR:-/opt/gemma4}"
MODEL_VARIANT="${GEMMA4_MODEL:-E2B}"

sudo mkdir -p "$VLLM_DIR" "$GEMMA_DIR" && sudo chown "$(whoami)" "$VLLM_DIR" "$GEMMA_DIR"

# Ensure uv
command -v uv &>/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH"; }

# Create venv
if [ ! -d "$VLLM_DIR/.venv" ]; then
    echo "Creating Python 3.12 venv..."
    uv venv "$VLLM_DIR/.venv" --python 3.12
fi

export PATH="$VLLM_DIR/.venv/bin:$HOME/.local/bin:$PATH"

# Install vLLM
echo "Installing vLLM..."
uv pip install --python "$VLLM_DIR/.venv/bin/python" vllm==0.19.0 2>&1 | tail -3

# Gemma 4 requires bleeding-edge transformers
echo "Installing transformers from source (Gemma 4 support)..."
uv pip install --python "$VLLM_DIR/.venv/bin/python" \
    "transformers @ git+https://github.com/huggingface/transformers.git" 2>&1 | tail -3

# Verify
echo ""
python -c "import vllm; print(f'vLLM: {vllm.__version__}')"
python -c "import transformers; print(f'Transformers: {transformers.__version__}')"

# Verify Gemma 4 config loads
case "$MODEL_VARIANT" in
    E2B|e2b) MODEL_ID="google/gemma-4-E2B-it" ;;
    E4B|e4b) MODEL_ID="google/gemma-4-E4B-it" ;;
    *)       MODEL_ID="$MODEL_VARIANT" ;;
esac

echo ""
python -c "
from transformers import AutoConfig
c = AutoConfig.from_pretrained('$MODEL_ID')
print(f'Model: $MODEL_ID')
print(f'Type: {c.model_type}')
print(f'Architecture: {c.architectures}')
print('Config OK')
"

echo ""
echo "=== Gemma 4 Setup Complete ==="
echo "Model: $MODEL_ID"
echo "Start: GEMMA4_MODEL=$MODEL_VARIANT bash scripts/start-gemma4.sh"
echo ""
echo "Note: Model weights download on first server start (~9.5 GB for E2B, ~14.9 GB for E4B)"
