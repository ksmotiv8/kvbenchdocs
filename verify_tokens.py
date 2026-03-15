#!/usr/bin/env python3
"""
verify_tokens.py — Verify token counts in a JSONL document corpus.

Tokenizes each document using the target model's tokenizer and reports
actual token counts vs recorded estimates. Works with any JSONL corpus
that has a "document" or "messages" field.

Usage:
    # Basic — uses Qwen3-8B-FP8 tokenizer by default:
    python verify_tokens.py medical_docs_10000.jsonl

    # Specify a different model tokenizer:
    python verify_tokens.py corpus.jsonl --model meta-llama/Llama-3-8B

    # Include the system/user prompt wrapper (as the benchmark sees it):
    python verify_tokens.py corpus.jsonl --include-prompt

    # CSV output for further analysis:
    python verify_tokens.py corpus.jsonl --csv > report.csv
"""

import argparse
import json
import sys
from typing import List, Optional, Tuple


def load_tokenizer(model_name: str):
    """Load tokenizer from HuggingFace, with clear error on missing deps."""
    try:
        from transformers import AutoTokenizer
    except ImportError:
        print(
            "ERROR: transformers not installed. Run: pip install transformers",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"Loading tokenizer: {model_name} ...", file=sys.stderr)
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    print(f"  vocab_size={tokenizer.vocab_size}", file=sys.stderr)
    return tokenizer


def extract_text(item: dict) -> str:
    """Extract the document text from a JSONL item.

    Supports formats:
      - {"document": "..."}               (legacy JSONL format)
      - {"messages": [{"role":..., "content":...}, ...]}  (gen_domain_docs.py)
      - {"text": "..."}                   (generic)
      - {"content": "..."}               (generic)
    """
    if "document" in item:
        return item["document"]
    if "messages" in item:
        # Concatenate all message contents (system + user)
        parts = []
        for msg in item["messages"]:
            if "content" in msg:
                parts.append(msg["content"])
        return "\n\n".join(parts)
    if "text" in item:
        return item["text"]
    if "content" in item:
        return item["content"]
    return ""


def make_benchmark_prompt(text: str) -> str:
    """Wrap text as the benchmark's long_doc_qa.py would present it to the model."""
    return (
        "Please read the document below. "
        "You may be asked questions about it later.\n\n"
        + text
    )


def verify_corpus(
    path: str,
    tokenizer,
    include_prompt: bool = False,
) -> List[dict]:
    """Tokenize each doc and return per-doc stats."""
    results = []
    with open(path) as f:
        for i, line in enumerate(f):
            item = json.loads(line)
            text = extract_text(item)
            if not text:
                print(f"  WARNING: doc {i} has no extractable text", file=sys.stderr)
                continue

            if include_prompt:
                text = make_benchmark_prompt(text)

            token_ids = tokenizer.encode(text)
            actual = len(token_ids)

            recorded = item.get("actual_tokens") or item.get("token_count")
            target = item.get("token_target")
            doc_id = item.get("id", f"doc_{i}")
            scenario = item.get("scenario_id", "")
            chars = len(text)

            results.append({
                "index": i,
                "id": doc_id,
                "scenario": scenario,
                "chars": chars,
                "tokens": actual,
                "recorded": recorded,
                "target": target,
                "chars_per_token": round(chars / actual, 2) if actual else 0,
            })

    return results


def print_table(results: List[dict]) -> None:
    """Print a human-readable summary table."""
    print()
    print(f"{'#':>3}  {'id':<45}  {'chars':>7}  {'tokens':>7}  "
          f"{'recorded':>8}  {'target':>7}  {'chr/tok':>7}  {'vs_target':>9}")
    print("-" * 140)

    for r in results:
        recorded_str = str(r["recorded"]) if r["recorded"] else "-"
        target_str = str(r["target"]) if r["target"] else "-"

        if r["target"]:
            pct = (r["tokens"] - r["target"]) / r["target"] * 100
            vs_target = f"{pct:+.1f}%"
        else:
            vs_target = "-"

        print(
            f"{r['index']:>3}  {r['id']:<45}  {r['chars']:>7,}  {r['tokens']:>7,}  "
            f"{recorded_str:>8}  {target_str:>7}  {r['chars_per_token']:>7.2f}  {vs_target:>9}"
        )

    # Summary
    tokens = [r["tokens"] for r in results]
    chars = [r["chars"] for r in results]
    cpt = [r["chars_per_token"] for r in results]

    print("-" * 140)
    print(f"{'':>3}  {'SUMMARY':<45}  {sum(chars):>7,}  {sum(tokens):>7,}  "
          f"{'':>8}  {'':>7}  {sum(chars)/sum(tokens):>7.2f}")
    print()
    print(f"  Documents:       {len(results)}")
    print(f"  Total tokens:    {sum(tokens):,}")
    print(f"  Mean tokens/doc: {sum(tokens)/len(results):,.0f}")
    print(f"  Min tokens:      {min(tokens):,}")
    print(f"  Max tokens:      {max(tokens):,}")
    print(f"  Std dev:         {_std(tokens):,.0f}")
    print(f"  Mean chars/tok:  {sum(chars)/sum(tokens):.2f}")

    if any(r["target"] for r in results):
        targets = [(r["tokens"], r["target"]) for r in results if r["target"]]
        diffs = [(t - tgt) / tgt * 100 for t, tgt in targets]
        print(f"\n  vs target:")
        print(f"    Mean diff:     {sum(diffs)/len(diffs):+.1f}%")
        print(f"    Min diff:      {min(diffs):+.1f}%")
        print(f"    Max diff:      {max(diffs):+.1f}%")

    if any(r["recorded"] for r in results):
        recorded = [(r["tokens"], r["recorded"]) for r in results if r["recorded"]]
        diffs = [(t - rec) / rec * 100 for t, rec in recorded]
        print(f"\n  vs recorded:")
        print(f"    Mean diff:     {sum(diffs)/len(diffs):+.1f}%")
        print(f"    Min diff:      {min(diffs):+.1f}%")
        print(f"    Max diff:      {max(diffs):+.1f}%")


def print_csv(results: List[dict]) -> None:
    """Print CSV to stdout."""
    print("index,id,scenario,chars,tokens,recorded,target,chars_per_token,vs_target_pct")
    for r in results:
        vs = ""
        if r["target"]:
            vs = f"{(r['tokens'] - r['target']) / r['target'] * 100:.1f}"
        rec = r["recorded"] if r["recorded"] else ""
        tgt = r["target"] if r["target"] else ""
        print(f"{r['index']},{r['id']},{r['scenario']},{r['chars']},"
              f"{r['tokens']},{rec},{tgt},{r['chars_per_token']},{vs}")


def _std(values: list) -> float:
    mean = sum(values) / len(values)
    return (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify token counts in a JSONL document corpus.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("corpus", help="Path to JSONL corpus file")
    parser.add_argument(
        "--model",
        default="Qwen/Qwen3-8B-FP8",
        help="HuggingFace model name for tokenizer (default: Qwen/Qwen3-8B-FP8)",
    )
    parser.add_argument(
        "--include-prompt",
        action="store_true",
        help="Wrap each doc in the benchmark prompt template before tokenizing",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Output CSV instead of table",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tokenizer = load_tokenizer(args.model)
    results = verify_corpus(args.corpus, tokenizer, args.include_prompt)

    if not results:
        print("No documents found.", file=sys.stderr)
        sys.exit(1)

    if args.csv:
        print_csv(results)
    else:
        print_table(results)


if __name__ == "__main__":
    main()
