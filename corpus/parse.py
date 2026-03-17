#!/usr/bin/env python3
"""Split a JSONL document corpus into individual readable files.

Entry point: parse-corpus (after ``uv sync``)

Takes JSONL corpus output (medical, legal, or any domain) and produces:
  1. One .md file per document in a docs/ subdirectory
  2. A manifest.csv summarizing all documents (metadata, sections, word counts)

Usage:
    parse-corpus corpus/medical/medical_docs_10000.jsonl
    parse-corpus corpus/legal/legal_docs_10000.jsonl
    parse-corpus corpus.jsonl --output-dir ./parsed --manifest manifest.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------

def extract_patient_name(text: str) -> str:
    """Pull patient name from common EHR header patterns.

    Looks for "Patient Name:" or "PATIENT NAME:" in the first 1000 chars,
    handling both markdown bold (**Patient Name:**) and plain text formats.
    Returns empty string if no match found.
    """
    for pattern in [
        r'\*\*(?:PATIENT NAME|Patient Name)[:\*]*\s*\*?\*?\s*(.+?)(?:\s{2,}|\n)',
        r'(?:PATIENT NAME|Patient Name)[:\s]+([A-Z][a-zA-Z\s."]+?)(?:\s{2,}|\n)',
    ]:
        m = re.search(pattern, text[:1000])
        if m:
            return m.group(1).strip().strip("*").strip()
    return ""


def extract_sections(text: str) -> str:
    """Extract section headings from the document.

    Finds both markdown headings (## Section Name) and bold-text section
    headers (**SECTION NAME**) commonly used in clinical documents.
    Returns a semicolon-separated string of up to 20 unique section names.
    """
    # Markdown headings: ## Section Name
    headings = re.findall(
        r'(?:^|\n)#{1,4}\s+\*?\*?(.+?)\*?\*?\s*$', text, re.MULTILINE
    )
    # Bold section headers: **CHIEF COMPLAINT**, **ASSESSMENT AND PLAN**
    bold_sections = re.findall(
        r'(?:^|\n)\*\*([A-Z][A-Z /&\-]+(?:\([^)]+\))?)\*?\*?', text
    )

    # Deduplicate while preserving order
    seen = set()
    sections = []
    for h in headings + bold_sections:
        h = h.strip().strip("*").strip(":")
        key = h.upper()
        if key not in seen and len(h) > 2:
            seen.add(key)
            sections.append(h)
    return "; ".join(sections[:20])


def word_count(text: str) -> int:
    """Simple whitespace-based word count."""
    return len(text.split())


# ---------------------------------------------------------------------------
# Main parsing logic
# ---------------------------------------------------------------------------

def parse_corpus(input_path: str, output_dir: Path, manifest_path: Path | None):
    """Parse JSONL corpus into individual .md files and optional manifest CSV.

    For each document in the JSONL:
      1. Extracts the document text from the "document" field
      2. Writes it as a .md file named after the document ID
      3. Collects metadata (patient name, sections, word count, etc.)
      4. Optionally writes a manifest.csv with all metadata

    Args:
        input_path: Path to the JSONL corpus file
        output_dir: Directory to write individual .md files into
        manifest_path: Optional path for the manifest CSV (None = skip)
    """
    docs_dir = output_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows = []

    with open(input_path) as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            doc = json.loads(line)

            doc_id = doc["id"]
            # Sanitize filename: replace slashes and spaces with underscores
            safe_filename = doc_id.replace("/", "_").replace(" ", "_") + ".md"
            doc_path = docs_dir / safe_filename
            content = doc["document"]

            # Write the raw clinical document as a markdown file
            doc_path.write_text(content, encoding="utf-8")

            # Collect metadata for the manifest
            manifest_rows.append({
                "index": i,
                "id": doc_id,
                "filename": f"docs/{safe_filename}",
                "doc_type": doc.get("doc_type", ""),
                "scenario_id": doc.get("scenario_id", ""),
                "scenario_title": doc.get("scenario_title", ""),
                "token_target": doc.get("token_target", ""),
                "actual_tokens": doc.get("actual_tokens", ""),
                "patient_name": extract_patient_name(content),
                "sections": extract_sections(content),
                "word_count": word_count(content),
                "char_count": len(content),
            })

    # Write manifest CSV if requested
    if manifest_path and manifest_rows:
        fieldnames = [
            "index", "id", "filename", "doc_type", "scenario_id",
            "scenario_title", "token_target", "actual_tokens",
            "patient_name", "sections", "word_count", "char_count",
        ]
        with open(manifest_path, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(manifest_rows)
        print(f"Manifest: {manifest_path}")

    # Print summary
    print(f"Wrote {len(manifest_rows)} documents to {docs_dir}/")
    for row in manifest_rows:
        print(
            f"  {row['id']:50s}  {row['doc_type']:25s}  "
            f"{row['patient_name']:30s}  {row['word_count']:>6} words"
        )

    return manifest_rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split a JSONL document corpus into individual readable files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  parse-corpus corpus/medical/medical_docs_10000.jsonl
  parse-corpus corpus/legal/legal_docs_10000.jsonl
  parse-corpus corpus.jsonl --output-dir ./parsed --manifest manifest.csv
""",
    )
    parser.add_argument(
        "corpus",
        help="Path to JSONL corpus file",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to write output into (default: same directory as the JSONL file)",
    )
    parser.add_argument(
        "--manifest",
        default="manifest.csv",
        help="Filename for the manifest CSV (default: manifest.csv). "
             "Use --no-manifest to skip.",
    )
    parser.add_argument(
        "--no-manifest",
        action="store_true",
        help="Skip writing the manifest CSV",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    corpus_path = Path(args.corpus)
    if not corpus_path.exists():
        print(f"ERROR: File not found: {corpus_path}", file=sys.stderr)
        sys.exit(1)

    # Default output dir = same directory as the JSONL file
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = corpus_path.parent

    # Manifest path (in the output directory)
    manifest_path = None
    if not args.no_manifest:
        manifest_path = output_dir / args.manifest

    rows = parse_corpus(str(corpus_path), output_dir, manifest_path)
    if not rows:
        print("No documents found in corpus.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
