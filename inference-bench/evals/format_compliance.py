"""
format_compliance.py -- Test whether models produce machine-parseable output.

Our earlier tests showed Bonsai outputs raw JSON and executable code,
while Gemma 4 and Qwen wrap outputs in markdown fences. This eval
tests that behavior systematically across more prompts.

Usage:
  export LLAMA_CPP_PYTHON_BASE_URL=http://localhost:3001/v1
  inspect eval evals/format_compliance.py --model llama-cpp-python/bonsai
"""

import json
from inspect_ai import Task, task
from inspect_ai.dataset import Sample, MemoryDataset
from inspect_ai.scorer import Score, Target, accuracy, scorer, stderr, CORRECT, INCORRECT
from inspect_ai.solver import generate, system_message


# ---- Dataset ----

FORMAT_SAMPLES = [
    # JSON output tests
    Sample(
        input="Create a JSON object with keys 'name' set to 'Alice' and 'age' set to 30.",
        target="json_valid",
        metadata={"format": "json", "system": "Output only valid JSON. No markdown, no explanation, no code fences."},
    ),
    Sample(
        input="Create a JSON array with three items: 'red', 'green', 'blue'.",
        target="json_valid",
        metadata={"format": "json", "system": "Output only valid JSON. No markdown, no explanation, no code fences."},
    ),
    Sample(
        input="Create a JSON object with key 'models' containing an array of objects, each with 'name' and 'params' keys. Include entries for 'Bonsai' (8B) and 'Gemma' (2B).",
        target="json_valid",
        metadata={"format": "json", "system": "Output only valid JSON. No markdown, no explanation, no code fences."},
    ),
    # Code output tests (must be directly executable)
    Sample(
        input="Write a Python function called 'add' that takes two numbers and returns their sum.",
        target="code_executable",
        metadata={"format": "python", "system": "Output only the Python function. No markdown, no explanation, no code fences, no examples."},
    ),
    Sample(
        input="Write a Python function called 'is_even' that returns True if a number is even.",
        target="code_executable",
        metadata={"format": "python", "system": "Output only the Python function. No markdown, no explanation, no code fences, no examples."},
    ),
    Sample(
        input="Write a Python function called 'reverse_list' that reverses a list in place.",
        target="code_executable",
        metadata={"format": "python", "system": "Output only the Python function. No markdown, no explanation, no code fences, no examples."},
    ),
    # Exact format tests
    Sample(
        input="Is 7 a prime number?",
        target="exact_word",
        metadata={"format": "yes_no", "system": "Respond with exactly one word: yes or no. Nothing else."},
    ),
    Sample(
        input="Is 0 a positive number?",
        target="exact_word",
        metadata={"format": "yes_no", "system": "Respond with exactly one word: yes or no. Nothing else."},
    ),
    Sample(
        input="What is 15 + 27?",
        target="42",
        metadata={"format": "number_only", "system": "Respond with only the number. No words, no explanation."},
    ),
    Sample(
        input="What is 144 / 12?",
        target="12",
        metadata={"format": "number_only", "system": "Respond with only the number. No words, no explanation."},
    ),
]


# ---- Scorer ----

@scorer(metrics=[accuracy(), stderr()])
def format_scorer():
    async def score(state: TaskState, target: Target):
        output = state.output.completion.strip() if state.output.completion else ""
        fmt = state.metadata.get("format", "")

        if target.text == "json_valid":
            # Must parse as valid JSON without stripping markdown fences
            try:
                json.loads(output)
                return Score(value=CORRECT, answer=output[:100])
            except (json.JSONDecodeError, ValueError):
                # Check if it would pass after stripping markdown
                has_fence = "```" in output
                return Score(
                    value=INCORRECT,
                    answer=output[:100],
                    explanation=f"Invalid JSON. {'Wrapped in markdown fence.' if has_fence else 'Parse error.'}",
                )

        elif target.text == "code_executable":
            # Must not start with ``` or contain markdown fences
            if output.startswith("```") or "```python" in output:
                return Score(
                    value=INCORRECT,
                    answer=output[:100],
                    explanation="Code wrapped in markdown fences. Not directly executable.",
                )
            # Check if it contains a function definition
            if "def " in output:
                return Score(value=CORRECT, answer=output[:100])
            else:
                return Score(value=INCORRECT, answer=output[:100], explanation="No function definition found.")

        elif target.text == "exact_word":
            # Must be exactly "yes" or "no" (case-insensitive, no punctuation)
            clean = output.lower().strip().rstrip(".")
            if clean in ("yes", "no"):
                return Score(value=CORRECT, answer=output)
            else:
                return Score(value=INCORRECT, answer=output, explanation=f"Expected 'yes' or 'no', got '{output}'")

        else:
            # Number matching
            clean = output.strip().rstrip(".")
            if clean == target.text:
                return Score(value=CORRECT, answer=output)
            else:
                return Score(value=INCORRECT, answer=output, explanation=f"Expected '{target.text}', got '{output}'")

    return score


# Need this import for the scorer
from inspect_ai.solver import TaskState


# ---- Task ----

@task
def format_compliance():
    """Test whether models produce machine-parseable output without markdown wrapping."""
    samples = []
    for s in FORMAT_SAMPLES:
        s_copy = Sample(
            input=s.input,
            target=s.target,
            metadata=s.metadata,
        )
        samples.append(s_copy)

    return Task(
        dataset=MemoryDataset(samples),
        solver=[
            system_message("{system}"),
            generate(),
        ],
        scorer=format_scorer(),
    )
