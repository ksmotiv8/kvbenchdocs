"""
pipeline_latency.py -- Test whether multi-step LLM pipelines work at interactive speed.

The thesis: when inference latency drops below ~200ms, you can chain multiple
LLM calls inside a single user interaction. This eval tests that claim by
running 2-step and 4-step pipelines and measuring both quality and total time.

Usage:
  # Against Bonsai on llama.cpp
  export LLAMA_CPP_PYTHON_BASE_URL=http://localhost:3001/v1
  inspect eval evals/pipeline_latency.py --model llama-cpp-python/bonsai

  # Against Gemma 4 on vLLM
  export VLLM_BASE_URL=http://localhost:3000/v1
  inspect eval evals/pipeline_latency.py --model vllm/google/gemma-4-E2B-it

  # Against Qwen on SGLang
  export SGLANG_BASE_URL=http://localhost:3000/v1
  inspect eval evals/pipeline_latency.py --model sglang/default
"""

import time
from inspect_ai import Task, task
from inspect_ai.dataset import Sample, MemoryDataset
from inspect_ai.scorer import Score, Target, accuracy, scorer, stderr, CORRECT, INCORRECT
from inspect_ai.solver import (
    Generate,
    Solver,
    TaskState,
    chain,
    generate,
    solver,
    system_message,
)


# ---- Dataset: tasks that benefit from multi-step processing ----

PIPELINE_SAMPLES = [
    Sample(
        input="add error handling to: def divide(a, b): return a / b",
        target="ZeroDivisionError",
        metadata={"category": "rewrite", "steps": 2},
    ),
    Sample(
        input="convert var x = 5; var y = 10; var z = x + y; to use const",
        target="const",
        metadata={"category": "transform", "steps": 2},
    ),
    Sample(
        input="What sorting algorithm is best for nearly-sorted data?",
        target="insertion sort",
        metadata={"category": "classify_then_answer", "steps": 2},
    ),
    Sample(
        input="Write a function to check if a string is a palindrome, then write 3 test cases for it",
        target="def",
        metadata={"category": "generate_then_verify", "steps": 2},
    ),
    Sample(
        input="Explain what a KV cache does in LLM inference, then list 3 ways to optimize it",
        target="cache",
        metadata={"category": "explain_then_elaborate", "steps": 2},
    ),
    Sample(
        input="Debug this: def fib(n): return fib(n-1) + fib(n-2)",
        target="base case",
        metadata={"category": "analyze_then_fix", "steps": 4},
    ),
    Sample(
        input="Design a rate limiter for an API. Requirements: token bucket, configurable limits, Redis backend.",
        target="token",
        metadata={"category": "design", "steps": 4},
    ),
    Sample(
        input="Refactor this to be async: import requests; def get_data(url): return requests.get(url).json()",
        target="async",
        metadata={"category": "refactor", "steps": 4},
    ),
]


# ---- Custom solver: two-step pipeline (classify then execute) ----

@solver
def two_step_pipeline():
    """Step 1: Classify the task. Step 2: Execute with a targeted prompt."""

    async def solve(state: TaskState, generate: Generate):
        # Step 1: Classify
        state.messages.append(
            {"role": "system", "content": "Classify this task as one of: CODE_EDIT, EXPLANATION, DESIGN. Respond with just the category."}
        )
        state = await generate(state)

        classification = state.output.completion.strip()

        # Step 2: Execute with targeted system prompt based on classification
        prompts = {
            "CODE_EDIT": "You are a code editor. Make the requested change. Output only the modified code.",
            "EXPLANATION": "You are a technical writer. Explain concisely and accurately.",
            "DESIGN": "You are a system architect. Provide a concrete, implementable design.",
        }
        system = prompts.get(classification, prompts["EXPLANATION"])

        # Reset and re-prompt with targeted instructions
        original_input = state.messages[0]["content"] if state.messages else ""
        state.messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": original_input},
        ]
        state = await generate(state)

        return state

    return solve


# ---- Custom solver: four-step pipeline ----

@solver
def four_step_pipeline():
    """Step 1: Classify. Step 2: Plan. Step 3: Execute. Step 4: Verify."""

    async def solve(state: TaskState, generate: Generate):
        original_input = state.messages[0]["content"] if state.messages else ""

        # Step 1: Classify
        state.messages = [
            {"role": "system", "content": "Classify this task: CODE_EDIT, EXPLANATION, or DESIGN. One word."},
            {"role": "user", "content": original_input},
        ]
        state = await generate(state, max_tokens=8)

        # Step 2: Plan
        state.messages = [
            {"role": "system", "content": "Create a 3-step plan for this task. Be specific. Under 50 words."},
            {"role": "user", "content": original_input},
        ]
        state = await generate(state, max_tokens=64)
        plan = state.output.completion.strip()

        # Step 3: Execute
        state.messages = [
            {"role": "system", "content": f"Execute this plan:\n{plan}\n\nBe concise and complete."},
            {"role": "user", "content": original_input},
        ]
        state = await generate(state, max_tokens=256)

        # Step 4: Verify
        execution = state.output.completion.strip()
        state.messages = [
            {"role": "system", "content": "Review this output for correctness. If it has errors, fix them. If correct, output it unchanged."},
            {"role": "user", "content": f"Task: {original_input}\n\nOutput:\n{execution}"},
        ]
        state = await generate(state, max_tokens=256)

        return state

    return solve


# ---- Scorer: checks if target appears in final output ----

@scorer(metrics=[accuracy(), stderr()])
def contains_target():
    async def score(state: TaskState, target: Target):
        output = state.output.completion.lower() if state.output.completion else ""
        target_text = target.text.lower() if target.text else ""

        if target_text in output:
            return Score(value=CORRECT, answer=state.output.completion[:200])
        else:
            return Score(
                value=INCORRECT,
                answer=state.output.completion[:200],
                explanation=f"Expected '{target.text}' in output",
            )

    return score


# ---- Tasks ----

@task
def pipeline_2step():
    """Two-step pipeline: classify then execute."""
    return Task(
        dataset=MemoryDataset(
            [s for s in PIPELINE_SAMPLES if s.metadata["steps"] == 2]
        ),
        solver=two_step_pipeline(),
        scorer=contains_target(),
    )


@task
def pipeline_4step():
    """Four-step pipeline: classify, plan, execute, verify."""
    return Task(
        dataset=MemoryDataset(
            [s for s in PIPELINE_SAMPLES if s.metadata["steps"] == 4]
        ),
        solver=four_step_pipeline(),
        scorer=contains_target(),
    )
