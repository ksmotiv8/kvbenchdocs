#!/usr/bin/env python3
"""
gen_medical_docs.py — LLM-generated medical document corpus for KV cache benchmarking.

Two-stage approach using a running vLLM instance (e.g. Qwen3-8B-FP8):

  Stage 1 — Scenario generation
    Prompt the LLM to produce a JSON list of medical document scenarios
    with estimated real-world proportions (e.g. 14% primary care follow-ups,
    12% ED chest pain evaluations, etc.).  The model draws on its training
    data to approximate the mix of document types seen in a typical hospital
    EHR system.

  Stage 2 — Document generation with exact token control
    For each scenario, prompt the LLM to write a complete medical document.
    After each generation/continuation, the accumulated text is tokenized
    locally using the model's own tokenizer to get an exact token count.
    The continuation loop uses this exact count to decide when to stop.
    Once the target is reached (within a small tolerance), the document is
    trimmed to exactly token_target tokens using the tokenizer, guaranteeing
    precise, reproducible document lengths for benchmarking.

  Token counting accuracy (v2 improvements):
    - Local tokenizer loaded at startup for exact counting (replaces the
      old approach of summing per-response completion_tokens with char-ratio
      scaling for stripped <think> blocks).
    - Thinking is disabled at the API level via chat_template_kwargs, not
      just the in-prompt /no_think hint.
    - Final documents are trimmed to exactly token_target tokens, ensuring
      zero variance from the target.
    - The actual_tokens field in the output is verified by the tokenizer,
      not estimated.

Usage:
    # Start vLLM on the GPU node first:
    vllm serve Qwen/Qwen3-8B-FP8 --gpu-memory-utilization 0.9

    # Then generate the corpus (can run on the same node or remotely):
    python gen_medical_docs.py \\
        --api-base http://localhost:8000/v1 \\
        --sizes 10000 \\
        --docs-per-size 15 \\
        --output-dir ./medical_docs

    # Output: one JSONL file per size, e.g. medical_docs/medical_docs_10000.jsonl
    # Each line: {"id", "token_target", "actual_tokens", "scenario_id",
    #             "scenario_title", "doc_type", "document"}

    # Verify token counts after generation:
    python verify_tokens.py medical_docs/medical_docs_10000.jsonl

Requirements:
    pip install openai transformers
"""

import argparse
import json
import math
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI


# ---------------------------------------------------------------------------
# Tokenizer — loaded once, used for exact token counting throughout
# ---------------------------------------------------------------------------

_tokenizer = None


def _load_tokenizer(model_name: str):
    """Load the model's tokenizer for exact local token counting.

    This is the key accuracy improvement: instead of relying on
    completion_tokens from the API (which includes <think> blocks)
    or character-ratio heuristics, we tokenize the actual document
    text locally to get exact counts.
    """
    global _tokenizer
    if _tokenizer is not None:
        return _tokenizer
    try:
        from transformers import AutoTokenizer
    except ImportError:
        print(
            "WARNING: transformers not installed (pip install transformers). "
            "Falling back to API-based token counting (less accurate).",
            file=sys.stderr,
        )
        return None
    print(f"Loading tokenizer: {model_name} ...", file=sys.stderr)
    _tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    print(f"  vocab_size={_tokenizer.vocab_size}", file=sys.stderr)
    return _tokenizer


def count_tokens(text: str) -> int:
    """Count tokens in text using the local tokenizer.

    Returns exact token count if tokenizer is loaded, otherwise falls
    back to a character-based estimate (~4.3 chars/token for medical text).
    """
    if _tokenizer is not None:
        return len(_tokenizer.encode(text))
    return len(text) // 4


def trim_to_tokens(text: str, target: int) -> tuple:
    """Trim text to exactly `target` tokens using the tokenizer.

    Decodes the first `target` token IDs back to text. This guarantees
    the output document has exactly the target token count when re-tokenized.

    Returns:
        (trimmed_text, actual_token_count)
    """
    if _tokenizer is None:
        # Without tokenizer, can't trim precisely — return as-is
        return text, count_tokens(text)
    ids = _tokenizer.encode(text)
    if len(ids) <= target:
        return text, len(ids)
    trimmed_ids = ids[:target]
    trimmed_text = _tokenizer.decode(trimmed_ids, skip_special_tokens=True)
    # Verify round-trip (decode can sometimes add/lose a token)
    actual = len(_tokenizer.encode(trimmed_text))
    return trimmed_text, actual


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

def _call_with_retry(client: OpenAI, max_retries: int = 3, **kwargs):
    """Call chat.completions.create with exponential backoff on transient errors."""
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(**kwargs)
        except (APIConnectionError, APITimeoutError) as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            print(f" [retry {attempt + 1}/{max_retries} in {wait}s: {e}]",
                  end="", flush=True)
            time.sleep(wait)


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def _extract_content(resp) -> str:
    """Safely extract message content from a response, returning '' on None."""
    if not resp.choices:
        return ""
    content = resp.choices[0].message.content
    return content if content is not None else ""


def _strip_thinking(text: str) -> str:
    """Remove <think>...</think> reasoning blocks from model output.

    Qwen3 models may emit thinking blocks even when asked not to.
    These must be stripped before the text is used as document content,
    as they are internal reasoning, not part of the medical document.
    """
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _disable_thinking_kwargs() -> dict:
    """Return extra_body kwargs to disable Qwen3 thinking at the API level.

    This is more reliable than the in-prompt /no_think directive,
    which the model sometimes ignores. The chat_template_kwargs
    parameter is passed through to the Jinja template which has
    an explicit enable_thinking flag.
    """
    return {
        "extra_body": {
            "chat_template_kwargs": {"enable_thinking": False},
        }
    }


# ---------------------------------------------------------------------------
# Stage 1 — Ask the LLM to generate medical scenarios with proportions
# ---------------------------------------------------------------------------

STAGE1_PROMPT = """\
You are a health informatics expert. Generate a JSON array of medical document \
scenarios that represent the mix of clinical documents in a typical US hospital \
EHR system. For each scenario provide:

- "scenario_id": short snake_case identifier
- "title": human-readable title
- "doc_type": the clinical document type (e.g. "ED Note", "Discharge Summary")
- "setting": clinical setting (e.g. "Emergency Department", "Primary Care")
- "weight": estimated proportion of all clinical documents (floats summing to 1.0)

Include at least 12 scenario types spanning inpatient, outpatient, emergency, \
surgical, imaging, lab, specialty, and behavioral health settings.

Return ONLY the JSON array, no markdown fences, no explanation."""

REQUIRED_SCENARIO_KEYS = {"scenario_id", "title", "doc_type", "setting", "weight"}


def generate_scenarios(client: OpenAI, model: str) -> List[Dict[str, Any]]:
    """Stage 1: Ask the LLM to produce scenario definitions.

    The model acts as a health informatics expert, generating a realistic
    distribution of clinical document types. Each scenario includes:
      - scenario_id: snake_case identifier for the document type
      - title: human-readable name
      - doc_type: clinical document classification
      - setting: where in the hospital this document originates
      - weight: proportion of total documents (normalized to sum to 1.0)

    The weights approximate real-world EHR document distribution, giving
    the benchmark corpus a realistic mix of document types and lengths.
    """
    print("Stage 1: Generating medical document scenarios via LLM...")

    resp = _call_with_retry(
        client,
        model=model,
        messages=[{"role": "user", "content": STAGE1_PROMPT}],
        max_tokens=4096,
        temperature=0.7,
        **_disable_thinking_kwargs(),
    )

    raw = _extract_content(resp)
    if not raw:
        print("ERROR: Stage 1 returned empty response.", file=sys.stderr)
        sys.exit(1)

    raw = raw.strip()
    # Strip <think> blocks in case the model ignored the disable flag
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    # Strip markdown fences if the model added them
    raw = re.sub(r"^```\w*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    raw = raw.strip()
    # Extract the JSON array if there's surrounding text
    bracket_start = raw.find("[")
    bracket_end = raw.rfind("]")
    if bracket_start >= 0 and bracket_end > bracket_start:
        raw = raw[bracket_start : bracket_end + 1]

    try:
        scenarios = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Stage 1 produced invalid JSON: {e}", file=sys.stderr)
        print(f"  Raw output: {raw[:500]}", file=sys.stderr)
        sys.exit(1)

    # Validate scenario schema
    for i, s in enumerate(scenarios):
        missing = REQUIRED_SCENARIO_KEYS - set(s.keys())
        if missing:
            print(f"ERROR: Scenario {i} missing keys: {missing}", file=sys.stderr)
            sys.exit(1)

    # Normalize weights to sum to 1.0
    total_weight = sum(s["weight"] for s in scenarios)
    if total_weight <= 0:
        print("ERROR: Scenario weights sum to zero.", file=sys.stderr)
        sys.exit(1)
    for s in scenarios:
        s["weight"] = s["weight"] / total_weight

    print(f"  Generated {len(scenarios)} scenarios:")
    for s in scenarios:
        print(f"    {s['weight']:.1%}  {s['title']} ({s['doc_type']})")

    return scenarios


# ---------------------------------------------------------------------------
# Stage 2 — Ask the LLM to write each medical document
# ---------------------------------------------------------------------------

STAGE2_TEMPLATE = """\
Write a complete, realistic {doc_type} for a fictional patient.

Setting: {setting}
Scenario: {title}
Target length: approximately {token_target} tokens (write a thorough, detailed document).

Requirements:
- Invent realistic but fictional patient demographics, history, findings, and plans.
- Use proper medical terminology, abbreviations, and formatting.
- Include all standard sections for this document type.
- Include realistic vital signs, lab values, medication names and dosages.
- Do NOT include any meta-commentary — output only the document itself.
- Write continuously until you have produced a detailed, complete document of \
approximately {token_target} tokens.
- This is document #{doc_number} for this scenario — make it distinct from others."""

CONTINUATION_TEMPLATE = """\
Continue writing the {doc_type} from exactly where you left off. \
Do NOT repeat any content already written. Keep the same patient, \
same case, same formatting. Write at least {remaining_tokens} more tokens \
of additional clinical detail — expand on findings, add more lab results, \
imaging reads, nursing notes, consult responses, or follow-up documentation. \
Output ONLY the continuation text, no preamble."""

# Max chars of accumulated text to send as assistant context in continuations,
# to avoid exceeding the model's context window.
MAX_CONTEXT_CHARS = 80_000  # ~20K tokens, leaving room for prompts + generation

# How close to the target we need to be before stopping the continuation loop.
# 0.02 = within 2% of target. The final trim handles exact sizing.
STOP_TOLERANCE = 0.02


def generate_document(
    client: OpenAI,
    model: str,
    scenario: Dict[str, Any],
    token_target: int,
    doc_index: int,
) -> tuple:
    """Stage 2: Generate one medical document with exact token count control.

    Algorithm:
      1. Initial generation: prompt the LLM to write the full document.
         Disable thinking at the API level to avoid <think> block overhead.
      2. Count tokens exactly using the local tokenizer on the stripped text.
      3. If under target (within STOP_TOLERANCE), continue generating with
         the LLM, each time re-counting tokens on the accumulated text.
      4. Once at or above target, trim to exactly token_target tokens using
         the tokenizer's encode/decode round-trip.

    This replaces the old approach which:
      - Summed completion_tokens from each API response
      - Scaled by character ratio when <think> blocks were stripped
      - Never verified the actual accumulated token count
      - Had no trimming step, leading to +6% to +96% overshoot

    Returns:
        (document_text, actual_token_count)
    """
    first_shot_tokens = min(token_target, 16384)

    prompt = STAGE2_TEMPLATE.format(
        doc_type=scenario["doc_type"],
        setting=scenario["setting"],
        title=scenario["title"],
        token_target=token_target,
        doc_number=doc_index + 1,
    )

    resp = _call_with_retry(
        client,
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=first_shot_tokens,
        temperature=0.9,
        **_disable_thinking_kwargs(),
    )

    raw_content = _extract_content(resp)
    text = _strip_thinking(raw_content)

    # Exact token count via local tokenizer (the key accuracy fix)
    total_tokens = count_tokens(text)
    print(f" [{total_tokens}tok]", end="", flush=True)

    # Continuation loop — extend until within tolerance of target, then trim
    max_continuations = 10
    consecutive_low_yield = 0
    min_target = int(token_target * (1 - STOP_TOLERANCE))

    for attempt in range(max_continuations):
        if total_tokens >= min_target:
            break

        remaining_tokens = token_target - total_tokens
        cont_prompt = CONTINUATION_TEMPLATE.format(
            doc_type=scenario["doc_type"],
            remaining_tokens=remaining_tokens,
        )

        # Truncate context if too large for the model's context window
        context_text = text
        if len(text) > MAX_CONTEXT_CHARS:
            context_text = "...[earlier content truncated]...\n\n" + text[-MAX_CONTEXT_CHARS:]

        # Request slightly more than needed to ensure we reach the target
        cont_max = min(remaining_tokens + 256, 8192)
        resp = _call_with_retry(
            client,
            model=model,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": context_text},
                {"role": "user", "content": cont_prompt},
            ],
            max_tokens=cont_max,
            temperature=0.9,
            **_disable_thinking_kwargs(),
        )

        raw_cont = _extract_content(resp)
        continuation = _strip_thinking(raw_cont)
        if not continuation:
            break

        prev_tokens = total_tokens
        text += "\n\n" + continuation

        # Re-count on the full accumulated text (exact, not estimated)
        total_tokens = count_tokens(text)
        new_tokens = total_tokens - prev_tokens
        print(f" +{new_tokens}tok", end="", flush=True)

        if new_tokens < 50:
            consecutive_low_yield += 1
            if consecutive_low_yield >= 2:
                break
        else:
            consecutive_low_yield = 0

    # Trim to exactly token_target tokens
    if total_tokens > token_target:
        text, total_tokens = trim_to_tokens(text, token_target)
        print(f" [trimmed->{total_tokens}]", end="", flush=True)
    elif total_tokens < token_target:
        print(f" [short:{total_tokens}/{token_target}]", end="", flush=True)

    return text, total_tokens


# ---------------------------------------------------------------------------
# Allocation helpers
# ---------------------------------------------------------------------------

def allocate_counts(total: int, weights: List[float]) -> List[int]:
    """Distribute `total` documents across scenarios by weight.

    Uses the largest-remainder method (Hamilton's method) for fair
    proportional allocation. Each scenario gets floor(weight * total)
    documents, then remaining slots are assigned to scenarios with
    the largest fractional remainders.

    Example with 10 docs and weights [0.35, 0.25, 0.20, 0.20]:
      raw  = [3.5, 2.5, 2.0, 2.0]
      floor = [3,   2,   2,   2]  = 9 total, 1 remainder
      remainder goes to scenario 0 (0.5 frac) -> [4, 2, 2, 2] = 10
    """
    raw = [w * total for w in weights]
    counts = [int(math.floor(x)) for x in raw]
    remainder = total - sum(counts)
    fracs = sorted(
        [(i, raw[i] - counts[i]) for i in range(len(weights))],
        key=lambda x: x[1],
        reverse=True,
    )
    for i in range(remainder):
        counts[fracs[i][0]] += 1
    return counts


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def generate_dataset(
    client: OpenAI,
    model: str,
    token_target: int,
    docs_per_size: int,
) -> List[Dict[str, Any]]:
    """Run both stages and return the full dataset.

    Stage 1: Generate scenario definitions (document type mix).
    Stage 2: For each scenario, generate the allocated number of documents
             with exact token count control.
    """
    # Stage 1
    scenarios = generate_scenarios(client, model)

    # Stage 2
    weights = [s["weight"] for s in scenarios]
    counts = allocate_counts(docs_per_size, weights)

    items: List[Dict[str, Any]] = []
    doc_id = 0
    total_docs = sum(counts)

    for scenario, count in zip(scenarios, counts):
        for j in range(count):
            print(
                f"Stage 2: [{doc_id + 1}/{total_docs}] "
                f"{scenario['title']} ({j + 1}/{count})...",
                end="",
                flush=True,
            )
            t0 = time.time()
            doc_text, actual_tokens = generate_document(
                client, model, scenario, token_target, doc_id
            )
            elapsed = time.time() - t0
            print(f" -> {actual_tokens} tokens, {elapsed:.1f}s")

            items.append(
                {
                    "id": f"{scenario['scenario_id']}-{token_target}-{doc_id}",
                    "token_target": token_target,
                    "actual_tokens": actual_tokens,
                    "scenario_id": scenario["scenario_id"],
                    "scenario_title": scenario["title"],
                    "doc_type": scenario["doc_type"],
                    "document": doc_text,
                }
            )
            doc_id += 1

    return items


def write_jsonl(path: str, items: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate medical document corpus via LLM for KV cache benchmarking.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Generate 15 documents of ~10K tokens each:
  python gen_medical_docs.py --api-base http://localhost:8000/v1 \\
      --sizes 10000 --docs-per-size 15

  # Generate multiple sizes:
  python gen_medical_docs.py --api-base http://GPU_HOST:8000/v1 \\
      --sizes 1000,5000,10000 --docs-per-size 20

  # Verify token accuracy after generation:
  python verify_tokens.py medical_docs/medical_docs_10000.jsonl
""",
    )
    parser.add_argument(
        "--api-base",
        default="http://localhost:8000/v1",
        help="vLLM OpenAI-compatible API base URL (default: http://localhost:8000/v1)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model name for tokenizer + generation. If omitted, auto-detected from vLLM.",
    )
    parser.add_argument(
        "--output-dir",
        default="./medical_docs",
        help="Directory to write JSONL output files (default: ./medical_docs)",
    )
    parser.add_argument(
        "--docs-per-size",
        type=int,
        default=15,
        help="Number of documents to generate per token-size bucket (default: 15)",
    )
    parser.add_argument(
        "--sizes",
        default="10000",
        help="Comma-separated list of target token counts (default: 10000)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sizes = [int(s.strip()) for s in args.sizes.split(",") if s.strip()]

    client = OpenAI(base_url=args.api_base, api_key="not-needed")

    # Auto-detect model if not specified
    model = args.model
    if not model:
        models = client.models.list()
        if not models.data:
            print("ERROR: vLLM server returned no models. Is a model loaded?",
                  file=sys.stderr)
            sys.exit(1)
        model = models.data[0].id
        print(f"Auto-detected model: {model}")

    # Load tokenizer for exact token counting
    _load_tokenizer(model)

    for size in sizes:
        print(f"\n{'=' * 60}")
        print(f"Generating {args.docs_per_size} documents at exactly {size} tokens each")
        print(f"{'=' * 60}")

        items = generate_dataset(
            client=client,
            model=model,
            token_target=size,
            docs_per_size=args.docs_per_size,
        )

        out_path = os.path.join(args.output_dir, f"medical_docs_{size}.jsonl")
        write_jsonl(out_path, items)

        # Summary stats
        tokens = [it["actual_tokens"] for it in items]
        print(f"\nWrote {len(items)} documents to {out_path}")
        print(f"  Target:  {size} tokens/doc")
        print(f"  Actual:  mean={sum(tokens)/len(tokens):.0f}, "
              f"min={min(tokens)}, max={max(tokens)}")


if __name__ == "__main__":
    main()
