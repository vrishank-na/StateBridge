import json
import re
from pathlib import Path
from typing import List, Tuple
import tiktoken

# Matches standard speaker labels including browser copy-pastes ("You said:", "ChatGPT said:", etc.)
SPEAKER_PATTERN = re.compile(
    r"(?m)^(?:\*{0,2})(User|Assistant|Human|Claude|ChatGPT|Gemini|You(?: said)?|Model)(?:\*{0,2})\s*:\s*",
    re.IGNORECASE,
)


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """Returns exact token count using OpenAI's cl100k_base tokenizer."""
    if not text:
        return 0
    enc = tiktoken.get_encoding(encoding_name)
    return len(enc.encode(text))


def _normalize_speaker(raw_label: str) -> str:
    """Maps browser-specific labels (You, ChatGPT, Claude, Gemini) to canonical User/Assistant."""
    low = raw_label.strip().lower()
    if low.startswith("user") or low.startswith("human") or low.startswith("you"):
        return "User"
    return "Assistant"


def parse_raw_chat(raw_text: str) -> List[str]:
    """
    Auto-detects input format and converts raw chat text into normalized turns:
      1. JSON message arrays: [{"role": "user", "content": "..."}]
      2. Labeled transcripts: User:/Assistant:, You said:/ChatGPT said:, Human:/Claude:
      3. Unlabeled plain text: paragraphs separated by blank lines (alternates User/Assistant)
    """
    cleaned = raw_text.strip()
    if not cleaned:
        return []

    # Format 1: JSON array of role/content messages
    if cleaned.startswith("["):
        try:
            data = json.loads(cleaned)
            if isinstance(data, list) and all(isinstance(m, dict) and "content" in m for m in data):
                turns = []
                for idx, msg in enumerate(data):
                    role = _normalize_speaker(str(msg.get("role", "user" if idx % 2 == 0 else "assistant")))
                    content = str(msg["content"]).strip()
                    if content:
                        turns.append(f"{role}: {content}")
                return turns
        except json.JSONDecodeError:
            pass  # Fall through to text parsing if not valid JSON

    # Format 2: Explicit speaker prefixes (User:, You said:, ChatGPT:, etc.)
    matches = list(SPEAKER_PATTERN.finditer(cleaned))
    if matches:
        turns = []
        for i, match in enumerate(matches):
            speaker = _normalize_speaker(match.group(1))
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(cleaned)
            content = cleaned[start:end].strip()
            if content:
                turns.append(f"{speaker}: {content}")
        return turns

    # Format 3: Unlabeled raw copy-paste (split on blank lines and alternate speakers)
    blocks = [b.strip() for b in re.split(r"\n\s*\n", cleaned) if b.strip()]
    turns = []
    for idx, block in enumerate(blocks):
        speaker = "User" if idx % 2 == 0 else "Assistant"
        turns.append(f"{speaker}: {block}")
    return turns


def chunk_turns(turns: List[str], batch_size: int = 4) -> List[List[str]]:
    """Groups normalized turns into sequential batches of `batch_size`."""
    if batch_size <= 0:
        raise ValueError("batch_size must be at least 1")
    return [turns[i : i + batch_size] for i in range(0, len(turns), batch_size)]


def load_and_prepare_chat(file_path: str, batch_size: int = 4) -> Tuple[List[List[str]], int]:
    """Reads a chat file from disk, computes raw token count, and returns batched turns."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Chat file not found: {file_path}")
    raw_text = path.read_text(encoding="utf-8")
    raw_tokens = count_tokens(raw_text)
    turns = parse_raw_chat(raw_text)
    batches = chunk_turns(turns, batch_size=batch_size)
    return batches, raw_tokens