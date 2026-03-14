# Medical Document Corpus Generator (v2)

Synthetic medical document corpus for benchmarking KV cache offloading in vLLM + LMCache. Documents are LLM-generated clinical notes that look like real EHR records, with **exact token count control** for reproducible benchmarks.

## Motivation

### The default benchmark document

LMCache ships with a long-document QA benchmark (`long_doc_qa.py`) for measuring KV cache offloading performance. When run without a corpus file, it generates documents like this:

```python
warmup_prompts = [
    str(i) + " " + " ".join(["hi"] * args.document_length)
    for i in range(args.num_documents)
]
```

A "10,000-token document" is literally:

```
0 hi hi hi hi hi hi hi hi hi hi hi hi hi hi hi hi hi hi hi hi hi hi ...
```

The token count is accurate — the Qwen3-8B tokenizer encodes `"hi"` as a single token, so 10,000 repetitions produce 10,001 tokens (10,000 `hi` + 1 prefix digit). That's close enough for benchmarking purposes.

The problem is what the tokens represent. The entire 10,001-token document contains only **2 unique tokens**. This matters for KV cache benchmarks because:

- **Compression ratios**: KV cache connectors compress tensors (typically with zstd) before sending them to remote storage. A document with 2 unique tokens produces highly regular tensors that compress to nearly nothing. A medical note with 1,329 unique tokens across varied clinical vocabulary compresses very differently.
- **KV tensor diversity**: The key-value tensors produced by the attention mechanism reflect the input tokens. A monotonic `hi hi hi` sequence produces uniform tensors; clinical text with varied structure, numbers, medical terminology, and formatting produces tensors with much more variance.
- **Cache access patterns**: Real workloads involve documents with different prefixes, shared terminology, and overlapping but not identical content. The `hi hi hi` pattern shares nothing meaningful between documents except the same two tokens.

Measured on Qwen3-8B-FP8 with 10,000-token documents:

| Metric              | Default (`hi hi hi...`) | Medical corpus |
|---------------------|------------------------:|---------------:|
| Tokens              |                  10,001 |         10,000 |
| Unique tokens       |                       2 |          1,329 |
| Token diversity     |                   0.02% |          13.3% |
| Characters          |                  30,001 |         38,202 |
| Chars/token         |                    3.00 |           3.82 |

Benchmarking KV cache offloading with `hi hi hi` is like benchmarking a database with `SELECT 1` — the numbers come back fast, but they don't tell you how the system performs under realistic load.

## Model choice

We use [Qwen/Qwen3-8B-FP8](https://huggingface.co/Qwen/Qwen3-8B-FP8), an open-weight model, for both document generation and benchmarking. Using an open model means anyone can reproduce the corpus exactly — same tokenizer, same generation behavior, same KV cache tensor shapes — without depending on a proprietary API. The FP8-quantized variant fits comfortably on a single NVIDIA L4 (24 GB) GPU.

### Setting up the model

```bash
# Install vLLM (0.15.0 was used for corpus generation)
pip install vllm

# Start the model server (single GPU, ~21 GB VRAM)
vllm serve Qwen/Qwen3-8B-FP8 \
    --tensor-parallel-size 1 \
    --gpu-memory-utilization 0.9

# Verify it's running
curl http://localhost:8000/health
```

The model weights are downloaded automatically from HuggingFace on first run. The server exposes an OpenAI-compatible API at `http://localhost:8000/v1` — the generation script connects to this endpoint.

For the corpus included in this repo, we ran on an AWS `g6.8xlarge` instance (NVIDIA L4, 24 GB VRAM). Any GPU with 24+ GB VRAM should work. Generation takes ~7 minutes per 10K-token document.

## How it works

### Two-stage generation (`gen_medical_docs.py`)

The generator connects to the running vLLM instance and works in two stages. First, it asks the LLM to act as a health informatics expert and produce a realistic distribution of clinical document types — the kind of mix you'd see in a real hospital EHR system. Then, for each document type in that distribution, it prompts the LLM to write a complete clinical document, continuing and trimming until it hits the exact target token count.

#### Stage 1 — Scenario generation

The script sends a single prompt asking the model to define the corpus structure:

```
You are a health informatics expert. Generate a JSON array of medical document
scenarios that represent the mix of clinical documents in a typical US hospital
EHR system. For each scenario provide:

- "scenario_id": short snake_case identifier
- "title": human-readable title
- "doc_type": the clinical document type (e.g. "ED Note", "Discharge Summary")
- "setting": clinical setting (e.g. "Emergency Department", "Primary Care")
- "weight": estimated proportion of all clinical documents (floats summing to 1.0)

Include at least 12 scenario types spanning inpatient, outpatient, emergency,
surgical, imaging, lab, specialty, and behavioral health settings.

Return ONLY the JSON array, no markdown fences, no explanation.
```

The model returns a JSON array of 12+ scenarios with weights. These weights are normalized to sum to 1.0, then used to allocate the requested number of documents across scenarios proportionally (e.g., if you ask for 15 docs and inpatient progress notes have weight 0.15, that scenario gets 2-3 documents).

#### Stage 2 — Document generation

For each allocated document, the script sends a generation prompt:

```
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
- Write continuously until you have produced a detailed, complete document of
  approximately {token_target} tokens.
- This is document #{doc_number} for this scenario — make it distinct from others.
```

If the first response doesn't reach the target token count, the script sends the partial text back as assistant context along with a continuation prompt:

```
Continue writing the {doc_type} from exactly where you left off. Do NOT repeat
any content already written. Keep the same patient, same case, same formatting.
Write at least {remaining_tokens} more tokens of additional clinical detail —
expand on findings, add more lab results, imaging reads, nursing notes, consult
responses, or follow-up documentation. Output ONLY the continuation text, no
preamble.
```

This loop repeats until the accumulated text reaches the target (within 2% tolerance), at which point it's trimmed to the exact token count.

### Solving the token count accuracy problem

The `hi hi hi` approach gets token counts right trivially — one word, one token, repeat N times. But when we started generating real clinical documents with an LLM, token count accuracy became a significant problem.

The first version of this generator (v1) asked the LLM to write documents of approximately 10,000 tokens, then relied on the API's `completion_tokens` field to track how many tokens had been generated. The resulting documents were consistently oversized:

| Doc  | Type                 | Actual tokens | Target | Diff    |
|-----:|----------------------|--------------:|-------:|--------:|
|    0 | ED Admission Note    |        14,333 | 10,000 |  +43.3% |
|    1 | ED Admission Note    |        12,598 | 10,000 |  +26.0% |
|    2 | ED Discharge Summary |        14,180 | 10,000 |  +41.8% |
|    5 | Inpatient Order Set  |        19,574 | 10,000 |  +95.7% |
|    6 | Outpatient Visit     |        10,655 | 10,000 |   +6.6% |
|      | ...                  |               |        |         |
|      | **Mean (15 docs)**   |    **12,763** | 10,000 | **+27.6%** |

The root causes:

1. **Thinking tokens counted as content.** Qwen3 models emit `<think>...</think>` reasoning blocks before generating text. The API's `completion_tokens` counts these thinking tokens, but the script strips them from the final document. So a response reported as 8,000 tokens might only contribute 4,000 tokens of actual document text after stripping.

2. **Character-ratio heuristics.** The v1 script tried to compensate by estimating how many "real" tokens remained after stripping `<think>` blocks, using a characters-per-token ratio. This heuristic was unreliable — medical text has highly variable token density (abbreviations like "CBC" are 1 token, drug names like "acetaminophen" are 3-4 tokens).

3. **No final verification.** The script never tokenized the accumulated document text to verify the count. It just summed up estimated per-response counts and hoped for the best.

### How v2 fixes this

The v2 generator loads the model's own HuggingFace tokenizer at startup and uses it for all counting:

1. **Local tokenizer.** `transformers.AutoTokenizer` gives exact token counts by tokenizing the actual document text, not by trusting API response metadata.

2. **Thinking disabled at API level.** Instead of stripping `<think>` blocks after the fact, v2 passes `chat_template_kwargs: {"enable_thinking": False}` via `extra_body`. This tells the model's chat template to skip reasoning entirely — more reliable than the in-prompt `/no_think` directive, which the model sometimes ignores.

3. **Full-text re-counting.** After each continuation, the script tokenizes the entire accumulated document, not just the new chunk. This avoids drift from summing per-response estimates.

4. **Encode-slice-decode trimming.** Once the document reaches or exceeds the target, it's trimmed to exactly `token_target` tokens: encode to token IDs, slice to target length, decode back to text.

The result:

| Metric              | v1 corpus | v2 corpus            |
|---------------------|----------:|---------------------:|
| Mean diff from target |    +27.6% |                 0.0% |
| Min diff            |     +6.6% | -0.0% (9,999/10,000) |
| Max diff            |    +95.7% |                 0.0% |

### Generated corpus overview

The included corpus (`medical_docs_10000.jsonl`) contains 10 documents totaling 99,999 tokens. Stage 1 produced 12 scenarios; with 10 documents to allocate, the proportional weighting resulted in the following distribution:

- **Emergency Department** (2 docs): An ED initial assessment for a 41-year-old male presenting with severe abdominal pain, and a discharge summary for a patient treated for chest pain with cardiac workup.
- **Inpatient** (3 docs): Two daily progress notes tracking different patients through multi-day hospital stays, plus a medication reconciliation document listing current and home medications with dosage adjustments.
- **Outpatient** (1 doc): A primary care follow-up note for chronic disease management with lab review and medication titration.
- **Surgical** (1 doc): A preoperative evaluation for an elective procedure, including anesthesia risk assessment and surgical planning.
- **Diagnostics** (2 docs): A multi-modality imaging report (CT, MRI, X-ray findings) and a comprehensive laboratory result report spanning CBC, CMP, coagulation, thyroid, and specialty panels.
- **Specialty** (1 doc): A specialty clinical consultation note with detailed examination findings and treatment recommendations.

Each document reads like a real clinical note — formatted with standard EHR section headers, realistic vital signs, medication dosages, lab values, and clinical reasoning. The documents are individual `.md` files in the `corpus/` subdirectory if you want to browse them.

### Token count and diversity

All 10 documents verified with `verify_tokens.py` using the Qwen3-8B-FP8 tokenizer:

| Doc | Type                      | Tokens | Unique tokens | Diversity | Chars  | Chars/tok |
|----:|---------------------------|-------:|--------------:|----------:|-------:|----------:|
|   0 | ED Note                   | 10,000 |         1,329 |     13.3% | 38,202 |      3.82 |
|   1 | Discharge Summary         | 10,000 |         1,545 |     15.4% | 39,466 |      3.95 |
|   2 | Progress Note             | 10,000 |         1,233 |     12.3% | 32,571 |      3.26 |
|   3 | Progress Note             | 10,000 |           997 |     10.0% | 32,451 |      3.25 |
|   4 | Medication Reconciliation |  9,999 |           938 |      9.4% | 27,787 |      2.78 |
|   5 | Progress Note             | 10,000 |         1,277 |     12.8% | 36,548 |      3.65 |
|   6 | Preoperative Note         | 10,000 |           989 |      9.9% | 28,426 |      2.84 |
|   7 | Imaging Report            | 10,000 |         1,466 |     14.7% | 37,667 |      3.77 |
|   8 | Lab Report                | 10,000 |         1,652 |     16.5% | 33,063 |      3.31 |
|   9 | Clinical Note             | 10,000 |         1,392 |     13.9% | 39,090 |      3.91 |
|     | **Mean**                  | **9,999** |     **1,281** | **12.8%** | **34,527** | **3.45** |

Token diversity ranges from 9.4% (medication reconciliation — heavy on repeated drug names and dosages) to 16.5% (lab report — many distinct test names and numeric values). All documents are 640x more diverse than the `hi hi hi` baseline (0.02%).

Characters per token varies from 2.78 (medication reconciliation, with many short abbreviations and numbers) to 3.95 (discharge summary, with more natural prose). This variance is itself representative of real clinical text — different document types have different mixes of medical abbreviations, drug names, numeric lab values, and narrative text.

## What's in this folder

```
kvbenchdocs/
├── README.md                        # This file
├── gen_medical_docs.py              # Stage 1+2: LLM-based document generator
├── parse_corpus.py                  # JSONL → individual .md files + manifest
├── verify_tokens.py                 # Independent token count verification
├── medical_docs_10000.jsonl         # Generated corpus (10 docs × 10K tokens)
├── manifest.csv                     # Metadata for all documents
├── corpus/                          # Individual documents as readable .md files
│   ├── ed_initial_note-10000-0.md
│   ├── ed_discharge_summary-10000-1.md
│   ├── inpatient_progress_note-10000-2.md
│   └── ...
└── docs/                            # Blog website (served via GitHub Pages)
    ├── index.html
    ├── styles.css
    └── script.js
```

## Usage

### Prerequisites

```bash
pip install openai transformers
```

A running vLLM instance (see [Setting up the model](#setting-up-the-model) above).

### Generate a corpus

```bash
# 15 documents at exactly 10,000 tokens each
python gen_medical_docs.py \
    --api-base http://localhost:8000/v1 \
    --sizes 10000 \
    --docs-per-size 15

# Multiple sizes (e.g., for testing different document lengths)
python gen_medical_docs.py \
    --api-base http://GPU_HOST:8000/v1 \
    --sizes 1000,5000,10000 \
    --docs-per-size 10 \
    --output-dir ./corpus
```

Output: `medical_docs/medical_docs_10000.jsonl` (one JSON object per line).

Each line contains:
```json
{
  "id": "ed_initial_note-10000-0",
  "token_target": 10000,
  "actual_tokens": 10000,
  "scenario_id": "ed_initial_note",
  "scenario_title": "Emergency Department Initial Note",
  "doc_type": "ED Note",
  "document": "**ED Note**\n\n**Patient Name:** James M. Harper\n..."
}
```

Generation takes ~7 minutes per document at 10K tokens on an L4 GPU.

### Verify token counts

```bash
# Verify with the same tokenizer used for generation
python verify_tokens.py medical_docs_10000.jsonl

# Use a different model's tokenizer
python verify_tokens.py medical_docs_10000.jsonl --model meta-llama/Llama-3-8B

# Include the benchmark prompt wrapper (as long_doc_qa.py sends it)
python verify_tokens.py medical_docs_10000.jsonl --include-prompt

# CSV output for spreadsheets
python verify_tokens.py medical_docs_10000.jsonl --csv > report.csv
```

### Parse into individual documents

```bash
# Default: writes docs/ and manifest.csv next to the JSONL file
python parse_corpus.py medical_docs_10000.jsonl

# Custom output directory
python parse_corpus.py medical_docs_10000.jsonl --output-dir ./parsed

# Skip the manifest CSV
python parse_corpus.py medical_docs_10000.jsonl --no-manifest
```

The individual `.md` files are formatted markdown that reads like real clinical notes — complete with patient demographics, vital signs, lab values, medication lists, imaging reports, and clinical assessments.

## Benchmark integration

The JSONL corpus is consumed directly by LMCache's `long_doc_qa.py` benchmark via the `--corpus-file` flag:

```bash
python benchmarks/long_doc_qa/long_doc_qa.py \
    --model Qwen/Qwen3-8B-FP8 \
    --corpus-file /path/to/medical_docs_10000.jsonl \
    --num-documents 15 \
    --document-length 10000 \
    --output-len 100 \
    --repeat-count 1 \
    --repeat-mode tile \
    --max-inflight-requests 4
```

This replaces the default `hi hi hi...` generator with real medical documents, producing realistic KV cache access patterns for meaningful offloading benchmarks.

## Document types in the corpus

The LLM generates a realistic mix of clinical document types. A typical run produces:

| Document Type               | Setting              | Proportion |
|-----------------------------|----------------------|-----------:|
| ED Initial Note             | Emergency Department |       ~12% |
| ED Discharge Summary        | Emergency Department |        ~8% |
| Inpatient Progress Note     | Inpatient            |       ~15% |
| Medication Reconciliation   | Inpatient            |        ~7% |
| Outpatient Progress Note    | Primary Care         |       ~10% |
| Surgical Preoperative Note  | Surgery              |        ~6% |
| Surgical Postoperative Note | Surgery              |        ~5% |
| Imaging Report              | Radiology            |        ~9% |
| Laboratory Result Report    | Lab                  |        ~8% |
| Specialty Clinical Note     | Specialty            |        ~7% |
| Behavioral Health Intake    | Behavioral Health    |        ~5% |
| Discharge Instructions      | Inpatient            |        ~5% |

The exact mix varies per run since Stage 1 is stochastic, but proportions approximate real-world EHR distributions.
