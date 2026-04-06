"""
tool_calling.py -- Test basic tool/function calling capability.

Simpler than BFCLv3. Tests whether models can generate correct function
calls when given tool definitions. Uses Inspect's built-in tool support.

Usage:
  export VLLM_BASE_URL=http://localhost:3000/v1
  inspect eval evals/tool_calling.py --model vllm/google/gemma-4-E2B-it
"""

from inspect_ai import Task, task
from inspect_ai.dataset import Sample, MemoryDataset
from inspect_ai.scorer import Score, Target, accuracy, scorer, stderr, CORRECT, INCORRECT
from inspect_ai.solver import generate, system_message, use_tools, TaskState
from inspect_ai.tool import Tool, tool


# ---- Tools ----

@tool
def get_weather():
    """Get the current weather for a city."""

    async def execute(city: str) -> str:
        """Get weather for a city.

        Args:
            city: The city name to get weather for.
        """
        # Simulated responses
        weather_data = {
            "london": "15C, cloudy",
            "tokyo": "22C, sunny",
            "new york": "18C, partly cloudy",
            "sydney": "25C, clear",
        }
        return weather_data.get(city.lower(), f"Weather data not available for {city}")

    return execute


@tool
def calculate():
    """Perform a mathematical calculation."""

    async def execute(expression: str) -> str:
        """Evaluate a math expression.

        Args:
            expression: A mathematical expression to evaluate (e.g., '2 + 3 * 4').
        """
        try:
            result = eval(expression, {"__builtins__": {}})
            return str(result)
        except Exception as e:
            return f"Error: {e}"

    return execute


@tool
def search_database():
    """Search a database of programming languages."""

    async def execute(query: str) -> str:
        """Search for programming language information.

        Args:
            query: The programming language to look up.
        """
        db = {
            "python": {"year": 1991, "creator": "Guido van Rossum", "typing": "dynamic"},
            "rust": {"year": 2010, "creator": "Graydon Hoare", "typing": "static"},
            "go": {"year": 2009, "creator": "Robert Griesemer, Rob Pike, Ken Thompson", "typing": "static"},
        }
        lang = query.lower().strip()
        if lang in db:
            info = db[lang]
            return f"{query}: created {info['year']} by {info['creator']}, {info['typing']}ly typed"
        return f"No data found for {query}"

    return execute


# ---- Dataset ----

TOOL_SAMPLES = [
    Sample(
        input="What is the weather in London?",
        target="15C",
        metadata={"tools": ["get_weather"]},
    ),
    Sample(
        input="What is the weather in Tokyo?",
        target="22C",
        metadata={"tools": ["get_weather"]},
    ),
    Sample(
        input="Calculate 15 * 7 + 3",
        target="108",
        metadata={"tools": ["calculate"]},
    ),
    Sample(
        input="What is 2 to the power of 10?",
        target="1024",
        metadata={"tools": ["calculate"]},
    ),
    Sample(
        input="Look up information about Rust in the database.",
        target="Graydon Hoare",
        metadata={"tools": ["search_database"]},
    ),
    Sample(
        input="When was Python created? Check the database.",
        target="1991",
        metadata={"tools": ["search_database"]},
    ),
]


# ---- Scorer ----

@scorer(metrics=[accuracy(), stderr()])
def tool_output_scorer():
    async def score(state: TaskState, target: Target):
        output = state.output.completion.lower() if state.output.completion else ""
        target_text = target.text.lower()

        if target_text in output:
            return Score(value=CORRECT, answer=state.output.completion[:200])
        else:
            return Score(
                value=INCORRECT,
                answer=state.output.completion[:200],
                explanation=f"Expected '{target.text}' in output",
            )

    return score


# ---- Task ----

@task
def tool_calling():
    """Test basic tool calling: weather, math, database lookup."""
    return Task(
        dataset=MemoryDataset(TOOL_SAMPLES),
        solver=[
            system_message("You have access to tools. Use them to answer questions. Be concise."),
            use_tools([get_weather(), calculate(), search_database()]),
            generate(),
        ],
        scorer=tool_output_scorer(),
    )
