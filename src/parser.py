import re
from pathlib import Path
from typing import List, Tuple
import tiktoken


def count_tokens(text: str, model_encoding: str = "cl100k_base") -> int:
    """
    Counts the exact number of tokens in a string using tiktoken.
    'cl100k_base' is the standard BPE tokenizer used by modern LLMs.
    """
    if not text:
        return 0
    encoding = tiktoken.get_encoding(model_encoding)
    return len(encoding.encode(text))


def parse_raw_chat(raw_text: str) -> List[str]:
    """
    Splits a raw pasted chat log into individual conversation turns.
    Handles common prefixes like 'User:', 'You:', 'Assistant:', 'ChatGPT:', 'Gemini:', 'Claude:'.
    """
    cleaned_text = raw_text.strip()
    if not cleaned_text:
        return []

    # Split whenever a new speaker label starts on a new line
    pattern = r"(?=\n(?:User|You|Human|Assistant|ChatGPT|Gemini|Claude|AI)\s*:)"
    turns = re.split(pattern, cleaned_text, flags=re.IGNORECASE)

    # Strip extra whitespace and drop any empty blocks
    return [turn.strip() for turn in turns if turn.strip()]


def chunk_turns(turns: List[str], batch_size: int = 4) -> List[List[str]]:
    """
    Groups a flat list of conversation turns into smaller batches of `batch_size` (default 4).
    """
    batches: List[List[str]] = []
    for i in range(0, len(turns), batch_size):
        batch = turns[i : i + batch_size]
        batches.append(batch)
    return batches


def load_and_prepare_chat(file_path: str, batch_size: int = 4) -> Tuple[List[List[str]], int]:
    """
    End-to-end helper for Phase 2:
    Reads a chat file, counts original tokens, parses turns, and returns (batches, raw_token_count).
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Chat file not found: {file_path}")

    raw_text = path.read_text(encoding="utf-8")
    raw_tokens = count_tokens(raw_text)
    turns = parse_raw_chat(raw_text)
    batches = chunk_turns(turns, batch_size=batch_size)

    return batches, raw_tokens