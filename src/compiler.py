from dataclasses import dataclass
from typing import List
from src.schema import ProjectState
from src.parser import count_tokens


@dataclass
class CompiledHandoff:
    """Holds the final compiled prompt along with exact token compression metrics."""
    prompt: str
    raw_tokens: int
    compiled_tokens: int
    budget: int
    compression_ratio: float  # Percentage of tokens saved (e.g., 64.5)
    was_trimmed: bool


def _render_markdown(state: ProjectState) -> str:
    """Formats a ProjectState object into a clean, LLM-agnostic Markdown handoff block."""
    def fmt_list(items: List[str]) -> str:
        if not items:
            return "- None"
        return "\n".join(f"- {item}" for item in items)

    return (
        "# PROJECT HANDOFF STATE\n"
        "Continue this engineering session using the verified state below. "
        "Strictly obey all Hard Constraints and DO NOT suggest anything listed under Deprecated Approaches.\n\n"
        f"## 1. Core Goal\n{state.goal}\n\n"
        f"## 2. Hard Constraints (STRICT RULES)\n{fmt_list(state.hard_constraints)}\n\n"
        f"## 3. Active Tech Stack\n{fmt_list(state.tech_stack)}\n\n"
        f"## 4. Deprecated Approaches (DO NOT USE)\n{fmt_list(state.deprecated_approaches)}\n\n"
        f"## 5. Active Bugs / Blockers\n{fmt_list(state.active_bugs)}\n\n"
        f"## 6. Immediate Next Steps\n{fmt_list(state.next_steps)}\n"
    )


def compile_handoff(
    state: ProjectState,
    raw_tokens: int,
    max_tokens: int = 500,
) -> CompiledHandoff:
    """
    Compiles ProjectState into a Markdown prompt guaranteed to fit within `max_tokens`.
    If over budget, trims lowest-priority items first while preserving Core Goal and Hard Constraints.
    """
    # Work on a deep copy so we never mutate the caller's ProjectState
    working = state.model_copy(deep=True)
    was_trimmed = False

    prompt = _render_markdown(working)
    current_tokens = count_tokens(prompt)

    # Priority-based trimming loop if prompt exceeds max_tokens
    trim_order = [
        "deprecated_approaches",
        "next_steps",
        "active_bugs",
        "tech_stack",
    ]

    for field_name in trim_order:
        field_list: List[str] = getattr(working, field_name)
        while current_tokens > max_tokens and len(field_list) > 0:
            # Drop the oldest item (index 0) first
            field_list.pop(0)
            was_trimmed = True
            prompt = _render_markdown(working)
            current_tokens = count_tokens(prompt)

    # Calculate compression savings percentage
    if raw_tokens > 0:
        saved = max(0, raw_tokens - current_tokens)
        ratio = round((saved / raw_tokens) * 100, 1)
    else:
        ratio = 0.0

    return CompiledHandoff(
        prompt=prompt,
        raw_tokens=raw_tokens,
        compiled_tokens=current_tokens,
        budget=max_tokens,
        compression_ratio=ratio,
        was_trimmed=was_trimmed,
    )