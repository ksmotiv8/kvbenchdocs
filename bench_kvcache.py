#!/usr/bin/env python3
"""
bench_kvcache.py -- Improved KV-cache benchmark based on LMCache long_doc_qa.

Improvements over original:
  1. Realistic document generation with diverse vocabulary and styles
  2. Separate warmup and query concurrency controls
  3. --skip-warmup / --skip-pre-warmup flags
  4. Detailed per-phase timing breakdown (min/max/mean/p50/p95/p99 TTFT)
  5. CSV export for tracking results across runs
"""

import argparse
import asyncio
import csv
import hashlib
import math
import os
import random
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
from openai import AsyncOpenAI

# ---------------------------------------------------------------------------
# Word lists for realistic document generation
# ---------------------------------------------------------------------------

_COMMON_WORDS = [
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "I",
    "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
    "this", "but", "his", "by", "from", "they", "we", "say", "her", "she",
    "or", "an", "will", "my", "one", "all", "would", "there", "their", "what",
    "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
    "when", "make", "can", "like", "time", "no", "just", "him", "know", "take",
    "people", "into", "year", "your", "good", "some", "could", "them", "see",
    "other", "than", "then", "now", "look", "only", "come", "its", "over",
    "think", "also", "back", "after", "use", "two", "how", "our", "work",
    "first", "well", "way", "even", "new", "want", "because", "any", "these",
    "give", "day", "most", "us", "great", "between", "need", "large", "often",
    "important", "national", "under", "major", "second", "long", "already",
    "according", "made", "public", "hand", "high", "small", "part", "world",
]

_TECHNICAL_WORDS = [
    "algorithm", "latency", "throughput", "pipeline", "cache", "buffer",
    "kernel", "tensor", "gradient", "embedding", "transformer", "attention",
    "inference", "quantization", "precision", "batch", "shard", "replica",
    "checkpoint", "tokenizer", "decoder", "encoder", "prefill", "decode",
    "bandwidth", "memory", "allocation", "garbage", "collector", "mutex",
    "semaphore", "thread", "coroutine", "async", "await", "callback",
    "middleware", "endpoint", "payload", "serialization", "deserialization",
    "schema", "partition", "replication", "consensus", "quorum", "leader",
    "follower", "snapshot", "compaction", "bloom", "filter", "index",
    "bitmap", "radix", "trie", "hashmap", "linked", "queue", "stack",
    "heap", "binary", "search", "sort", "merge", "graph", "node", "edge",
    "vertex", "adjacency", "traversal", "breadth", "depth", "optimization",
    "heuristic", "constraint", "objective", "feasible", "optimal", "convex",
    "parameter", "hyperparameter", "regularization", "dropout", "normalization",
    "activation", "softmax", "sigmoid", "relu", "pooling", "convolution",
    "recurrent", "residual", "bottleneck", "architecture", "deployment",
    "orchestration", "container", "microservice", "monolith", "serverless",
    "configuration", "monitoring", "observability", "telemetry", "metric",
    "dashboard", "alert", "threshold", "anomaly", "detection", "classification",
]

_LEGAL_WORDS = [
    "whereas", "hereby", "thereof", "herein", "pursuant", "notwithstanding",
    "aforementioned", "stipulation", "jurisdiction", "plaintiff", "defendant",
    "appellant", "respondent", "counsel", "statute", "provision", "amendment",
    "regulation", "compliance", "arbitration", "mediation", "indemnify",
    "liability", "warranty", "disclaimer", "covenant", "obligation", "breach",
    "termination", "dissolution", "injunction", "precedent", "adjudicate",
    "deposition", "testimony", "affidavit", "subpoena", "verdict", "judgment",
    "sentencing", "probation", "parole", "felony", "misdemeanor", "tort",
    "negligence", "fiduciary", "executor", "trustee", "beneficiary", "estate",
    "conveyance", "lien", "mortgage", "easement", "encumbrance", "zoning",
    "ordinance", "promulgate", "enact", "ratify", "rescind", "repeal",
    "sovereign", "immunity", "habeas", "corpus", "certiorari", "mandamus",
    "amicus", "curiae", "prima", "facie", "bona", "fide", "de", "facto",
    "pro", "tempore", "ex", "parte", "in", "absentia", "mens", "rea",
]

_CONVERSATION_WORDS = [
    "yeah", "okay", "sure", "right", "well", "actually", "honestly",
    "basically", "literally", "probably", "definitely", "maybe", "perhaps",
    "anyway", "whatever", "seriously", "obviously", "apparently", "exactly",
    "absolutely", "totally", "really", "pretty", "quite", "rather",
    "interesting", "amazing", "wonderful", "terrible", "fantastic", "awful",
    "hey", "listen", "look", "guess", "suppose", "mean", "think", "believe",
    "feel", "agree", "disagree", "understand", "remember", "forget", "notice",
    "mention", "suggest", "recommend", "consider", "wonder", "imagine",
    "explain", "describe", "discuss", "argue", "debate", "compare",
    "morning", "afternoon", "evening", "tonight", "yesterday", "tomorrow",
    "weekend", "coffee", "lunch", "dinner", "meeting", "project", "team",
    "office", "email", "phone", "message", "update", "schedule", "deadline",
]

_NARRATIVE_WORDS = [
    "whispered", "shouted", "murmured", "exclaimed", "wondered", "gazed",
    "wandered", "stumbled", "crept", "dashed", "lingered", "trembled",
    "forest", "castle", "village", "mountain", "river", "ocean", "desert",
    "meadow", "valley", "cliff", "cavern", "tower", "bridge", "garden",
    "shadow", "moonlight", "twilight", "dawn", "dusk", "storm", "mist",
    "ancient", "mysterious", "enchanted", "forgotten", "hidden", "sacred",
    "golden", "silver", "crimson", "emerald", "sapphire", "obsidian",
    "warrior", "merchant", "scholar", "healer", "traveler", "guardian",
    "companion", "stranger", "sovereign", "prophet", "artisan", "wanderer",
    "courage", "wisdom", "destiny", "betrayal", "redemption", "sacrifice",
    "journey", "quest", "legend", "prophecy", "oath", "alliance", "rival",
    "sword", "shield", "cloak", "pendant", "scroll", "compass", "lantern",
    "beneath", "beyond", "within", "among", "across", "through", "toward",
]

_PUNCTUATION_ENDINGS = [".", ".", ".", ".", "!", "?", ".", ";", ".", "."]
_NUMBERS = [str(i) for i in range(100)] + [
    "3.14", "42", "100", "1,000", "2.5", "0.01", "17.3", "256", "1024",
    "99.9%", "50%", "$100", "$3.2M", "10x", "2024", "2025", "500ms",
]

_STYLE_VOCAB = {
    "mixed": _COMMON_WORDS + _TECHNICAL_WORDS[:30] + _NUMBERS[:10],
    "technical": _COMMON_WORDS[:40] + _TECHNICAL_WORDS + _NUMBERS,
    "conversation": _COMMON_WORDS[:60] + _CONVERSATION_WORDS,
    "legal": _COMMON_WORDS[:40] + _LEGAL_WORDS,
    "narrative": _COMMON_WORDS[:50] + _NARRATIVE_WORDS,
}


def _generate_document(
    target_tokens: int, doc_index: int, style: str, seed: int
) -> str:
    """Generate a plausible document of approximately target_tokens tokens.

    Uses a seeded RNG so the same (doc_index, seed) always produces the
    same document.  The style parameter selects vocabulary and sentence
    structure.
    """
    rng = random.Random(hashlib.sha256(f"{seed}-{doc_index}".encode()).digest())
    vocab = _STYLE_VOCAB.get(style, _STYLE_VOCAB["mixed"])

    sentences: list[str] = []
    # Rough heuristic: 1 token ~= 0.75 words on average for English.
    target_words = int(target_tokens * 0.75)
    word_count = 0

    while word_count < target_words:
        if style == "conversation":
            sent_len = rng.randint(3, 15)
        elif style == "legal":
            sent_len = rng.randint(15, 50)
        elif style == "narrative":
            sent_len = rng.randint(8, 25)
        elif style == "technical":
            sent_len = rng.randint(8, 30)
        else:
            sent_len = rng.randint(5, 25)

        words = [rng.choice(vocab) for _ in range(sent_len)]
        words[0] = words[0].capitalize()
        ending = rng.choice(_PUNCTUATION_ENDINGS)
        sentence = " ".join(words) + ending
        sentences.append(sentence)
        word_count += sent_len

        # Paragraph breaks every few sentences
        if rng.random() < 0.15:
            sentences.append("")

    return "\n".join(sentences)


# ---------------------------------------------------------------------------
# RequestStats dataclass
# ---------------------------------------------------------------------------

@dataclass
class RequestStats:
    """Statistics for a single completed request."""
    start_time: float = 0.0
    end_time: float = 0.0
    first_token_time: float = 0.0
    ttft: float = 0.0            # time to first token
    total_time: float = 0.0
    output_tokens: int = 0
    prompt_index: int = -1
    is_cache_hit: bool = True
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Content extraction helpers (preserved from original)
# ---------------------------------------------------------------------------

def extract_reasoning_content(chunk) -> Tuple[str, bool]:
    """Extract content from a reasoning-mode chunk."""
    content = ""
    is_final = False
    if hasattr(chunk, "choices") and chunk.choices:
        choice = chunk.choices[0]
        delta = choice.delta
        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
            content = delta.reasoning_content
        if hasattr(delta, "content") and delta.content:
            content += delta.content
        if choice.finish_reason is not None:
            is_final = True
    return content, is_final


def extract_normal_content(chunk) -> Tuple[str, bool]:
    """Extract content from a standard (non-reasoning) chunk."""
    content = ""
    is_final = False
    if hasattr(chunk, "choices") and chunk.choices:
        choice = chunk.choices[0]
        delta = choice.delta
        if hasattr(delta, "content") and delta.content:
            content = delta.content
        if choice.finish_reason is not None:
            is_final = True
    return content, is_final


# ---------------------------------------------------------------------------
# Core request handler (preserved from original)
# ---------------------------------------------------------------------------

async def process_single_prompt(
    client: AsyncOpenAI,
    model: str,
    prompt: str,
    prompt_index: int,
    semaphore: asyncio.Semaphore,
    max_tokens: int,
    is_completions: bool,
    is_reasoning: bool,
    is_cache_hit: bool = True,
) -> RequestStats:
    """Send a single prompt and collect streaming stats."""
    stats = RequestStats(prompt_index=prompt_index, is_cache_hit=is_cache_hit)
    extract = extract_reasoning_content if is_reasoning else extract_normal_content

    async with semaphore:
        stats.start_time = time.perf_counter()
        try:
            if is_completions:
                stream = await client.completions.create(
                    model=model,
                    prompt=prompt,
                    max_tokens=max_tokens,
                    stream=True,
                    temperature=0,
                )
                first = True
                async for chunk in stream:
                    if first:
                        stats.first_token_time = time.perf_counter()
                        stats.ttft = stats.first_token_time - stats.start_time
                        first = False
                    if hasattr(chunk, "choices") and chunk.choices:
                        text = chunk.choices[0].text or ""
                        if text:
                            stats.output_tokens += 1
            else:
                stream = await client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    stream=True,
                    temperature=0,
                )
                first = True
                async for chunk in stream:
                    if first:
                        stats.first_token_time = time.perf_counter()
                        stats.ttft = stats.first_token_time - stats.start_time
                        first = False
                    content, _ = extract(chunk)
                    if content:
                        stats.output_tokens += 1
        except Exception as e:
            stats.error = str(e)
        finally:
            stats.end_time = time.perf_counter()
            stats.total_time = stats.end_time - stats.start_time

    return stats


# ---------------------------------------------------------------------------
# Prompt generation helpers (preserved from original)
# ---------------------------------------------------------------------------

def repeat_prompts(
    prompts: List[str],
    num_requests: int,
    mode: str = "tile",
) -> List[str]:
    """Expand a list of prompts to num_requests length.

    Modes:
      tile       -- cycle through prompts in order
      interleave -- same as tile (alias)
      random     -- random selection with replacement
    """
    if mode in ("tile", "interleave"):
        repeated = []
        for i in range(num_requests):
            repeated.append(prompts[i % len(prompts)])
        return repeated
    elif mode == "random":
        rng = random.Random(42)
        return [rng.choice(prompts) for _ in range(num_requests)]
    else:
        raise ValueError(f"Unknown repeat mode: {mode}")


def add_cache_misses(
    prompts: List[str],
    hit_ratio: float,
    miss_document_length: int,
    style: str,
    seed: int,
) -> Tuple[List[str], List[bool]]:
    """Replace a fraction of prompts with unique miss-documents.

    Returns (new_prompts, is_cache_hit_flags).
    """
    if hit_ratio >= 1.0:
        return prompts, [True] * len(prompts)

    new_prompts = []
    is_hit = []
    rng = random.Random(seed + 999)
    miss_counter = 0
    for p in prompts:
        if rng.random() < hit_ratio:
            new_prompts.append(p)
            is_hit.append(True)
        else:
            miss_doc = _generate_document(
                miss_document_length, miss_counter + 100_000, style, seed
            )
            question = "Summarize the key points of this document."
            new_prompts.append(f"{miss_doc}\n\n{question}")
            is_hit.append(False)
            miss_counter += 1
    return new_prompts, is_hit


# ---------------------------------------------------------------------------
# Trimmed mean (preserved from original)
# ---------------------------------------------------------------------------

def trimmed_mean(data: List[float], trim_fraction: float = 0.1) -> float:
    """Compute the mean after trimming extreme values from both ends."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    n = len(sorted_data)
    trim_count = int(n * trim_fraction)
    if trim_count * 2 >= n:
        return float(np.mean(sorted_data))
    trimmed = sorted_data[trim_count : n - trim_count]
    return float(np.mean(trimmed))


# ---------------------------------------------------------------------------
# Statistics summary
# ---------------------------------------------------------------------------

def _percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    return float(np.percentile(data, p))


def print_phase_stats(
    label: str,
    stats_list: List[RequestStats],
    wall_time: float,
) -> dict:
    """Print and return a timing breakdown for a phase."""
    successful = [s for s in stats_list if s.error is None]
    errors = [s for s in stats_list if s.error is not None]
    ttfts = [s.ttft for s in successful if s.ttft > 0]

    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    print(f"  Requests:   {len(stats_list)} total, {len(successful)} ok, {len(errors)} errors")
    print(f"  Wall time:  {wall_time:.3f}s")

    summary = {
        "phase": label,
        "total_requests": len(stats_list),
        "successful": len(successful),
        "errors": len(errors),
        "wall_time_s": round(wall_time, 4),
    }

    if ttfts:
        min_t = min(ttfts)
        max_t = max(ttfts)
        mean_t = float(np.mean(ttfts))
        p50 = _percentile(ttfts, 50)
        p95 = _percentile(ttfts, 95)
        p99 = _percentile(ttfts, 99)
        throughput = len(successful) / wall_time if wall_time > 0 else 0

        print(f"  Throughput: {throughput:.2f} prompts/s")
        print(f"  TTFT (s):   min={min_t:.4f}  max={max_t:.4f}  mean={mean_t:.4f}")
        print(f"              p50={p50:.4f}  p95={p95:.4f}  p99={p99:.4f}")
        print(f"  Trimmed mean TTFT: {trimmed_mean(ttfts):.4f}s")

        summary.update({
            "throughput_rps": round(throughput, 4),
            "ttft_min": round(min_t, 6),
            "ttft_max": round(max_t, 6),
            "ttft_mean": round(mean_t, 6),
            "ttft_p50": round(p50, 6),
            "ttft_p95": round(p95, 6),
            "ttft_p99": round(p99, 6),
            "ttft_trimmed_mean": round(trimmed_mean(ttfts), 6),
        })
    else:
        print("  (no TTFT data)")

    if errors:
        print(f"  First error: {errors[0].error}")
    print()

    return summary


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

_CSV_FIELDS = [
    "timestamp", "phase",
    "total_requests", "successful", "errors",
    "wall_time_s", "throughput_rps",
    "ttft_min", "ttft_max", "ttft_mean",
    "ttft_p50", "ttft_p95", "ttft_p99", "ttft_trimmed_mean",
    # Config metadata
    "model", "base_url", "num_documents", "document_length",
    "doc_style", "num_requests", "warmup_concurrency", "query_concurrency",
    "max_tokens", "repeat_mode", "hit_ratio",
    "completions_mode", "reasoning_mode", "corpus_file",
]


def append_csv(filepath: str, row: dict) -> None:
    """Append a single row to the CSV file, creating headers if needed."""
    write_header = not os.path.exists(filepath) or os.path.getsize(filepath) == 0
    with open(filepath, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(row)


# ---------------------------------------------------------------------------
# Visualization (preserved structure from original)
# ---------------------------------------------------------------------------

def visualize_results(
    stats_list: List[RequestStats], output_file: Optional[str] = None
) -> None:
    """Plot TTFT distribution and timeline.  Requires matplotlib."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed -- skipping visualization")
        return

    successful = [s for s in stats_list if s.error is None and s.ttft > 0]
    if not successful:
        print("No successful requests to visualize.")
        return

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # 1. TTFT histogram
    ttfts = [s.ttft for s in successful]
    hit_ttfts = [s.ttft for s in successful if s.is_cache_hit]
    miss_ttfts = [s.ttft for s in successful if not s.is_cache_hit]

    if hit_ttfts:
        axes[0].hist(hit_ttfts, bins=30, alpha=0.7, label="hit", color="green")
    if miss_ttfts:
        axes[0].hist(miss_ttfts, bins=30, alpha=0.7, label="miss", color="red")
    if not miss_ttfts:
        axes[0].hist(ttfts, bins=30, alpha=0.7, label="all", color="steelblue")
    axes[0].set_xlabel("TTFT (s)")
    axes[0].set_ylabel("Count")
    axes[0].set_title("TTFT Distribution")
    axes[0].legend()

    # 2. TTFT over time
    base_time = min(s.start_time for s in successful)
    x = [s.start_time - base_time for s in successful]
    y = [s.ttft for s in successful]
    colors = ["green" if s.is_cache_hit else "red" for s in successful]
    axes[1].scatter(x, y, c=colors, alpha=0.6, s=15)
    axes[1].set_xlabel("Time since start (s)")
    axes[1].set_ylabel("TTFT (s)")
    axes[1].set_title("TTFT Over Time")

    # 3. CDF
    sorted_ttfts = sorted(ttfts)
    cdf = np.arange(1, len(sorted_ttfts) + 1) / len(sorted_ttfts)
    axes[2].plot(sorted_ttfts, cdf, linewidth=2, color="steelblue")
    axes[2].set_xlabel("TTFT (s)")
    axes[2].set_ylabel("CDF")
    axes[2].set_title("TTFT CDF")
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    dest = output_file or "bench_kvcache_results.png"
    plt.savefig(dest, dpi=150)
    print(f"Saved visualization to {dest}")
    plt.close()


# ---------------------------------------------------------------------------
# Run phases
# ---------------------------------------------------------------------------

async def run_phase(
    label: str,
    client: AsyncOpenAI,
    model: str,
    prompts: List[str],
    concurrency: int,
    max_tokens: int,
    is_completions: bool,
    is_reasoning: bool,
    is_cache_hit_flags: Optional[List[bool]] = None,
) -> Tuple[List[RequestStats], float]:
    """Run all prompts through the API and return stats + wall time."""
    semaphore = asyncio.Semaphore(concurrency)

    if is_cache_hit_flags is None:
        is_cache_hit_flags = [True] * len(prompts)

    print(f"[{label}] Sending {len(prompts)} requests (concurrency={concurrency}) ...")
    t0 = time.perf_counter()

    tasks = [
        process_single_prompt(
            client=client,
            model=model,
            prompt=p,
            prompt_index=i,
            semaphore=semaphore,
            max_tokens=max_tokens,
            is_completions=is_completions,
            is_reasoning=is_reasoning,
            is_cache_hit=is_cache_hit_flags[i],
        )
        for i, p in enumerate(prompts)
    ]
    stats_list = await asyncio.gather(*tasks)

    wall_time = time.perf_counter() - t0
    print(f"[{label}] Done in {wall_time:.3f}s")
    return list(stats_list), wall_time


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="KV-cache benchmark with realistic document generation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Connection
    p.add_argument("--base-url", type=str, default="http://localhost:8000/v1",
                    help="Base URL for OpenAI-compatible API")
    p.add_argument("--model", type=str, default="default-model",
                    help="Model name to use")
    p.add_argument("--api-key", type=str, default="EMPTY",
                    help="API key (use EMPTY for local servers)")

    # Document generation
    p.add_argument("--num-documents", type=int, default=1,
                    help="Number of unique base documents to generate")
    p.add_argument("--document-length", type=int, default=10000,
                    help="Target token count per document")
    p.add_argument("--doc-style", type=str, default="mixed",
                    choices=["mixed", "technical", "conversation", "legal", "narrative"],
                    help="Style of generated documents")
    p.add_argument("--seed", type=int, default=42,
                    help="Random seed for deterministic document generation")

    # Request count and repetition
    p.add_argument("--num-requests", type=int, default=10,
                    help="Total number of query-phase requests")
    p.add_argument("--repeat-mode", type=str, default="tile",
                    choices=["tile", "interleave", "random"],
                    help="How to repeat documents across requests")

    # Concurrency
    p.add_argument("--warmup-concurrency", type=int, default=1,
                    help="Max inflight requests during warmup")
    p.add_argument("--query-concurrency", type=int, default=4,
                    help="Max inflight requests during query round")
    p.add_argument("--max-inflight-requests", type=int, default=None,
                    help="Alias for --query-concurrency (backward compat)")

    # Warmup control
    p.add_argument("--skip-warmup", action="store_true",
                    help="Skip warmup phase (assume cache is already warm)")
    p.add_argument("--skip-pre-warmup", action="store_true",
                    help="Skip the initial 5-request pre-warmup")

    # Generation
    p.add_argument("--max-tokens", type=int, default=1,
                    help="Max tokens to generate per request")
    p.add_argument("--completions", action="store_true",
                    help="Use completions API instead of chat completions")
    p.add_argument("--reasoning", action="store_true",
                    help="Enable reasoning content extraction")

    # Hit/miss ratio
    p.add_argument("--hit-ratio", type=float, default=1.0,
                    help="Fraction of requests that should be cache hits (0.0-1.0)")

    # Question
    p.add_argument("--question", type=str,
                    default="Summarize the key points of this document.",
                    help="Question to append to each document")

    # Corpus file
    p.add_argument("--corpus-file", type=str, default=None,
                    help="Path to JSONL corpus file (e.g. corpus/medical/medical_docs_10000.jsonl "
                         "or corpus/legal/legal_docs_10000.jsonl). Each line must have a 'document' "
                         "field. Overrides --num-documents, --document-length, and --doc-style.")

    # Output
    p.add_argument("--csv", type=str, default=None,
                    help="Append results as CSV rows to this file")
    p.add_argument("--visualize", type=str, default=None,
                    help="Save visualization plot to this file")

    return p


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Handle backward-compat alias
    if args.max_inflight_requests is not None:
        args.query_concurrency = args.max_inflight_requests

    # Build client
    client = AsyncOpenAI(base_url=args.base_url, api_key=args.api_key)

    # Generate or load documents
    if args.corpus_file:
        import json
        documents = []
        with open(args.corpus_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    obj = json.loads(line)
                    documents.append(obj["document"])
        args.num_documents = len(documents)
        print(f"Loaded {len(documents)} document(s) from {args.corpus_file}")
    else:
        print(f"Generating {args.num_documents} document(s) "
              f"(~{args.document_length} tokens each, style={args.doc_style}) ...")
        documents = [
            _generate_document(args.document_length, i, args.doc_style, args.seed)
            for i in range(args.num_documents)
        ]

    # Build prompts: document + question
    base_prompts = [f"{doc}\n\n{args.question}" for doc in documents]

    # Expand to num_requests
    query_prompts = repeat_prompts(base_prompts, args.num_requests, args.repeat_mode)

    # Apply hit/miss ratio
    query_prompts, hit_flags = add_cache_misses(
        query_prompts,
        args.hit_ratio,
        args.document_length,
        args.doc_style,
        args.seed,
    )

    all_query_stats: List[RequestStats] = []
    csv_config = {
        "model": args.model,
        "base_url": args.base_url,
        "num_documents": args.num_documents,
        "document_length": args.document_length,
        "doc_style": args.doc_style,
        "num_requests": args.num_requests,
        "warmup_concurrency": args.warmup_concurrency,
        "query_concurrency": args.query_concurrency,
        "max_tokens": args.max_tokens,
        "repeat_mode": args.repeat_mode,
        "hit_ratio": args.hit_ratio,
        "completions_mode": args.completions,
        "reasoning_mode": args.reasoning,
        "corpus_file": args.corpus_file,
    }

    # ---------------------------------------------------------------
    # Pre-warmup: 5 short requests to ensure server is responsive
    # ---------------------------------------------------------------
    if not args.skip_warmup and not args.skip_pre_warmup:
        pre_warmup_prompts = repeat_prompts(base_prompts, min(5, len(base_prompts)), "tile")
        pre_stats, pre_wall = await run_phase(
            label="Pre-Warmup",
            client=client,
            model=args.model,
            prompts=pre_warmup_prompts,
            concurrency=1,
            max_tokens=args.max_tokens,
            is_completions=args.completions,
            is_reasoning=args.reasoning,
        )
        pre_summary = print_phase_stats("Pre-Warmup", pre_stats, pre_wall)

    # ---------------------------------------------------------------
    # Warmup: send each unique document once to populate cache
    # ---------------------------------------------------------------
    if not args.skip_warmup:
        warmup_prompts = base_prompts[:]
        warmup_stats, warmup_wall = await run_phase(
            label="Warmup",
            client=client,
            model=args.model,
            prompts=warmup_prompts,
            concurrency=args.warmup_concurrency,
            max_tokens=args.max_tokens,
            is_completions=args.completions,
            is_reasoning=args.reasoning,
        )
        warmup_summary = print_phase_stats("Warmup", warmup_stats, warmup_wall)

        if args.csv:
            row = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
            row.update(warmup_summary)
            row.update(csv_config)
            append_csv(args.csv, row)
    else:
        print("[Warmup] Skipped (--skip-warmup)")

    # ---------------------------------------------------------------
    # Query round
    # ---------------------------------------------------------------
    query_stats, query_wall = await run_phase(
        label="Query",
        client=client,
        model=args.model,
        prompts=query_prompts,
        concurrency=args.query_concurrency,
        max_tokens=args.max_tokens,
        is_completions=args.completions,
        is_reasoning=args.reasoning,
        is_cache_hit_flags=hit_flags,
    )
    query_summary = print_phase_stats("Query", query_stats, query_wall)
    all_query_stats.extend(query_stats)

    if args.csv:
        row = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
        row.update(query_summary)
        row.update(csv_config)
        append_csv(args.csv, row)

    # ---------------------------------------------------------------
    # Hit vs miss breakdown (if applicable)
    # ---------------------------------------------------------------
    if args.hit_ratio < 1.0:
        hits = [s for s in all_query_stats if s.is_cache_hit and s.error is None]
        misses = [s for s in all_query_stats if not s.is_cache_hit and s.error is None]
        hit_ttfts = [s.ttft for s in hits if s.ttft > 0]
        miss_ttfts = [s.ttft for s in misses if s.ttft > 0]

        print("-" * 60)
        print("  Hit/Miss Breakdown")
        print("-" * 60)
        if hit_ttfts:
            print(f"  Hits  ({len(hit_ttfts)}): mean={np.mean(hit_ttfts):.4f}s  "
                  f"p50={_percentile(hit_ttfts, 50):.4f}s  "
                  f"p99={_percentile(hit_ttfts, 99):.4f}s")
        if miss_ttfts:
            print(f"  Misses({len(miss_ttfts)}): mean={np.mean(miss_ttfts):.4f}s  "
                  f"p50={_percentile(miss_ttfts, 50):.4f}s  "
                  f"p99={_percentile(miss_ttfts, 99):.4f}s")
        print()

    # ---------------------------------------------------------------
    # Visualization
    # ---------------------------------------------------------------
    if args.visualize:
        visualize_results(all_query_stats, args.visualize)

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
