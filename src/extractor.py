import os
import re
from typing import List
from dotenv import load_dotenv
from google import genai
from google.genai import types
from src.schema import ProjectState, StateDelta

load_dotenv()

FALLBACK_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.8-flash",
    "gemma-4-31b-it",
]


def get_gemini_client() -> genai.Client:
    """Initializes the Google GenAI client with a fast 10-second timeout."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing. Please add it to your .env file.")
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=10000),
    )


def _mock_extract_delta(batch: List[str], current_state: ProjectState) -> StateDelta:
    """
    Offline deterministic fallback extractor for testing/demos when external APIs
    experience 503 outages or rate limits.
    """
    text = "\n".join(batch)
    text_low = text.lower()

    updated_goal = None
    if current_state.goal == "Not yet defined" and ("build" in text_low or "want to" in text_low):
        first_line = batch[0].split(":", 1)[-1].strip()
        updated_goal = first_line

    known_tools = ["Python", "FastAPI", "SQLite", "PostgreSQL", "asyncpg", "React", "Docker", "Redis", "Flask"]
    added_tech = []
    deprecated_tech = []

    for tool in known_tools:
        t_low = tool.lower()
        if f"scratch {t_low}" in text_low or f"drop {t_low}" in text_low or f"replace {t_low}" in text_low:
            deprecated_tech.append(tool)
        elif t_low in text_low:
            added_tech.append(tool)

    added_constraints = []
    for line in batch:
        if "rule:" in line.lower() or "never " in line.lower() or "must " in line.lower():
            clean_rule = line.split(":", 1)[-1].strip()
            added_constraints.append(clean_rule)

    new_bugs = []
    resolved_bugs = []
    error_matches = re.findall(r"([A-Za-z0-9_.]+Error[^\n`]*)", text)
    for err in error_matches:
        if "fixed" in text_low or "resolved" in text_low:
            resolved_bugs.append(err.strip())
        else:
            new_bugs.append(err.strip())

    next_steps = []
    for line in batch:
        if "need to " in line.lower():
            next_steps.append(line.split(":", 1)[-1].strip())

    return StateDelta(
        updated_goal=updated_goal,
        added_constraints=added_constraints,
        added_tech=added_tech,
        deprecated_tech=deprecated_tech,
        new_bugs=new_bugs,
        resolved_bugs=resolved_bugs,
        updated_next_steps=next_steps,
    )


def extract_delta(
    batch: List[str],
    current_state: ProjectState,
    model_name: str = "gemini-3.1-flash-lite",
    use_mock: bool = False,
) -> StateDelta:
    """
    Sends a single 4-turn batch of conversation + current ProjectState to Gemini,
    returning a validated StateDelta object. Set `use_mock=True` for offline mode.
    """
    if use_mock:
        return _mock_extract_delta(batch, current_state)

    client = get_gemini_client()

    conversation_chunk = "\n\n".join(batch)
    current_state_json = current_state.model_dump_json(indent=2)

    system_instruction = (
        "You are a precise state extraction engine for software engineering conversations. "
        "Read the 4-turn conversation snippet alongside the current ProjectState "
        "and extract ONLY the concrete state mutations (StateDelta) that occurred in this snippet.\n"
        "Rules:\n"
        "- Only set `updated_goal` if the core objective explicitly changed.\n"
        "- If the user abandons or replaces a tool (e.g., 'scratch SQLite, use Postgres'), "
        "put the abandoned tool in `deprecated_tech` and the new tool in `added_tech`.\n"
        "- If an active bug from ProjectState is confirmed fixed in this snippet, list it in `resolved_bugs`.\n"
        "- Do not invent or assume information not present in the snippet."
    )

    user_prompt = (
        f"CURRENT PROJECT STATE:\n{current_state_json}\n\n"
        f"NEW CONVERSATION SNIPPET ({len(batch)} turns):\n{conversation_chunk}"
    )

    models_to_try = [model_name] + [m for m in FALLBACK_MODELS if m != model_name]
    last_error = None

    for candidate_model in models_to_try:
        try:
            response = client.models.generate_content(
                model=candidate_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=StateDelta,
                    temperature=0.0,
                ),
            )
            return StateDelta.model_validate_json(response.text)
        except Exception as err:
            last_error = err

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")