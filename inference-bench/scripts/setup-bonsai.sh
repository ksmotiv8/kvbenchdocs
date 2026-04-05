#!/usr/bin/env bash
# setup-bonsai.sh — Install PrismML's llama.cpp fork and download Bonsai 1-bit 8B
# Idempotent: safe to rerun
set -euo pipefail

echo "=== Bonsai 1-bit 8B Setup ==="

BONSAI_DIR="${BONSAI_DIR:-/opt/bonsai}"
CUDA_HOME="${CUDA_HOME:-$(ls -d /usr/local/cuda-* 2>/dev/null | sort -V | tail -1)}"

if [ -z "$CUDA_HOME" ]; then
    echo "ERROR: No CUDA installation found"
    exit 1
fi

echo "CUDA: $CUDA_HOME"
echo "Install dir: $BONSAI_DIR"

# Ensure deps
for cmd in git cmake gcc g++; do
    command -v "$cmd" &>/dev/null || { echo "ERROR: $cmd required"; exit 1; }
done

sudo mkdir -p "$BONSAI_DIR" && sudo chown "$(whoami)" "$BONSAI_DIR"

# Clone PrismML llama.cpp fork
if [ -d "$BONSAI_DIR/llama.cpp" ]; then
    echo "llama.cpp fork already cloned"
else
    echo "Cloning PrismML llama.cpp fork..."
    git clone https://github.com/PrismML-Eng/llama.cpp.git "$BONSAI_DIR/llama.cpp"
fi

# Build with CUDA
echo "Building with CUDA..."
cd "$BONSAI_DIR/llama.cpp"
mkdir -p build && cd build
cmake .. \
    -DGGML_CUDA=ON \
    -DCMAKE_CUDA_COMPILER="$CUDA_HOME/bin/nvcc" \
    -DCMAKE_BUILD_TYPE=Release 2>&1 | tail -5
cmake --build . --config Release -j"$(nproc)" 2>&1 | tail -5

if [ ! -f bin/llama-server ]; then
    echo "ERROR: Build failed"
    exit 1
fi
echo "Build OK: $(ls bin/llama-server bin/llama-cli bin/llama-bench 2>/dev/null | wc -l) binaries"

# Download model
MODEL_DIR="$BONSAI_DIR/models/Bonsai-8B-gguf"
if [ -f "$MODEL_DIR/Bonsai-8B.gguf" ]; then
    echo "Model already downloaded"
else
    echo "Downloading Bonsai-8B GGUF (1.15 GB)..."
    mkdir -p "$MODEL_DIR"

    # Try huggingface-cli from any available venv
    HF_CLI=""
    for venv in /opt/sglang/.venv /opt/vllm/.venv; do
        if [ -f "$venv/bin/huggingface-cli" ] || [ -f "$venv/bin/hf" ]; then
            HF_CLI="$venv/bin"
            break
        fi
    done

    if [ -n "$HF_CLI" ]; then
        "$HF_CLI/hf" download prism-ml/Bonsai-8B-gguf Bonsai-8B.gguf \
            --local-dir "$MODEL_DIR" 2>&1 | tail -3
    else
        echo "No huggingface-cli found. Install with: pip install huggingface_hub"
        exit 1
    fi
fi

echo ""
echo "=== Bonsai Setup Complete ==="
echo "Model: $MODEL_DIR/Bonsai-8B.gguf ($(du -sh "$MODEL_DIR/Bonsai-8B.gguf" | cut -f1))"
echo "Server: $BONSAI_DIR/llama.cpp/build/bin/llama-server"
echo "Bench:  $BONSAI_DIR/llama.cpp/build/bin/llama-bench"
echo ""
echo "Start: bash scripts/start-bonsai.sh"
