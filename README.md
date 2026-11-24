# StateBridge

**Deterministic, Model-Agnostic Cross-Session State Compiler for Long LLM Engineering Conversations.**

Long-running coding sessions with LLMs suffer from **context rot**: as message history grows into thousands of tokens, strict rules get forgotten, abandoned libraries resurface, resolved errors linger as noise, and API latency and costs climb.

Asking an LLM to simply "summarize the chat" produces unpredictable prose that still drops edge-case constraints and ignores token limits.

**StateBridge** solves this by treating conversation memory like a **state machine**. Instead of relying on free-form LLM summaries, it separates:

- **Semantic extraction:** Handled incrementally by an LLM.
- **State mutation and token budgeting:** Handled deterministically in pure Python.

It compiles bloated multi-turn chat transcripts into a crisp, guaranteed-size handoff prompt portable across Gemini, Claude, ChatGPT, or any local model.

## Core Architecture

StateBridge processes raw transcripts through a 6-stage modular pipeline:

```text
Raw Chat Transcript (JSON / Labeled / Plain Text)
        │
        ▼
┌───────────────────┐
│  1. Parser        │  Splits turns via regex & chunks into 4-turn batches (tiktoken)
└────────┬──────────┘
         ▼
┌───────────────────┐
│  2. Extractor     │  Extracts structured StateDelta diffs via Gemini Structured Outputs
└────────┬──────────┘  (with multi-model fallback & deterministic --mock offline mode)
         ▼
┌───────────────────┐
│  3. Reducer       │  Pure Python state engine: deduplicates rules, evicts deprecated
└────────┬──────────┘  tech from active stack, and clears resolved bugs
         ▼
┌───────────────────┐
│  4. Compiler      │  Renders Markdown handoff & enforces max_tokens via priority
└────────┬──────────┘  trimming (never drops Core Goal or Hard Constraints)
         ▼
    CLI / REST API
         │
         ▼
Portable handoff prompt ready for any fresh LLM session
```

### Schema (`src/schema.py`)

Strict Pydantic v2 models (`ProjectState` and `StateDelta`) defining typed state mutations rather than unstructured text.

### Parser & Chunker (`src/parser.py`)

Auto-detects:

- OpenAI/Anthropic JSON message arrays (`[{"role": ..., "content": ...}]`)
- Labeled transcripts (`User:` / `Assistant:`, `You said:` / `ChatGPT said:`)
- Unlabeled plain text

Splits conversations into batches and counts exact tokens using `tiktoken` with `cl100k_base`.

### LLM Delta Extractor (`src/extractor.py`)

Evaluates 4-turn windows against the current `ProjectState` using Google GenAI Structured Outputs (`response_schema=StateDelta`).

Features:

- Automatic model fallback.
- Deterministic local `--mock` extractor.
- Offline testing and CI support without external API calls.

### Deterministic State Reducer (`src/reducer.py`)

Pure Python state transition logic (`apply_delta`) handling:

- Case-insensitive deduplication.
- Automatic migration of abandoned tools from `tech_stack` to `deprecated_approaches`.
- Substring-matched bug clearance.

### Token-Budgeted Prompt Compiler (`src/compiler.py`)

Compiles `ProjectState` into a structured Markdown prompt guaranteed to satisfy:

`compiled_tokens <= budget`

When over budget, it drops lowest-priority items first:

1. `deprecated_approaches`
2. `next_steps`
3. `active_bugs`
4. `tech_stack`

It strictly preserves the core goal and hard constraints.

### Interfaces (`src/cli.py`, `src/api.py`)

- **CLI:** Typer + Rich terminal interface.
- **REST API:** FastAPI microservice exposing `POST /compile`.

Designed for automated integration into AI coding agents and chat pipelines.

## System Setup & Installation

### Prerequisites

- Python 3.10+ (`python --version`)
- Git (`git --version`)
- A Gemini API Key from Google AI Studio (optional if running in offline `--mock` mode)

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/StateBridge.git
cd StateBridge
```

### 2. Create & Activate a Virtual Environment

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks script activation, run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Alternatively, use Command Prompt:

```cmd
venv\Scripts\activate.bat
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root `StateBridge/` directory with your API key.

**Windows (PowerShell):**

```powershell
Set-Content -Path .env -Value "GEMINI_API_KEY=your_gemini_api_key_here"
```

**macOS / Linux:**

```bash
echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env
```

## How to Use StateBridge

### 1. Programmatic / Agent Integration via REST API (`src/api.py`)

In production, AI coding assistants and agentic workflows can call StateBridge automatically whenever conversation history exceeds a token threshold.

Start the FastAPI server:

```bash
uvicorn src.api:app --reload
```

Send a `POST /compile` request with your conversation transcript and target token budget:

```bash
curl -X POST "http://127.0.0.1:8000/compile" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_chat": "[{\"role\": \"user\", \"content\": \"Build a FastAPI service with PostgreSQL. Never use an ORM.\"}]",
    "budget": 300,
    "use_mock": false
  }'
```

You can also explore and test the API interactively through Swagger UI:

[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 2. Command-Line Interface (`src/cli.py`)

Use the CLI to compile saved session logs, exported JSON chats, or clipboard transcripts into a token-budgeted handoff file (such as `.cursorrules` or `CLAUDE.md`).

**Compile a conversation log using live Gemini extraction:**

```bash
python -m src.cli benchmarks/enterprise_session.txt --budget 300
```

**Save the compiled handoff prompt directly to a file:**

```bash
python -m src.cli benchmarks/enterprise_session.txt --budget 300 --out handoff.md
```

**Run completely offline using the deterministic fallback extractor:**

```bash
python -m src.cli benchmarks/enterprise_session.txt --budget 300 --mock
```

**Read a transcript directly from your OS clipboard:**

```bash
python -m src.cli --clipboard --budget 300 --mock
```

### CLI Options

| Option | Default | Description |
|---|---|---|
| `CHAT_FILE` | `None` | Path to a `.txt`, `.md`, or `.json` chat transcript |
| `--clipboard`, `-c` | `False` | Read input transcript directly from the OS clipboard |
| `--budget`, `-b` | `500` | Maximum allowed tokens in the compiled output prompt |
| `--batch-size` | `4` | Number of conversation turns processed per delta batch |
| `--model`, `-m` | `gemini-3.1-flash-lite` | Primary Gemini model used for delta extraction |
| `--mock` | `False` | Use the local deterministic extractor without external API calls |
| `--out`, `-o` | `None` | Optional file path to save the compiled Markdown prompt |


### 3. Run Benchmarks & Unit Tests

Verify deterministic state reduction, token-budget priority trimming, and multi-file compression ratios.

**Run the pytest unit test suite:**

```bash
pytest -v
```

**Run compression benchmarks across all sample transcripts in `benchmarks/`:**

```bash
python -m benchmarks.evaluate --budget 300
```

**Run benchmarks with live Gemini extraction:**

```bash
python -m benchmarks.evaluate --budget 300 --live
```

## Project Structure

```text
StateBridge/
├── benchmarks/
│   ├── evaluate.py              # Multi-file token compression benchmark runner
│   ├── sample_chat.txt          # Short baseline conversation transcript
│   ├── long_session.txt         # Multi-turn webhook service debugging session
│   └── enterprise_session.txt   # 44-turn IoT ingestion session with 4 stack pivots
│
├── src/
│   ├── schema.py                # ProjectState & StateDelta Pydantic v2 schemas
│   ├── parser.py                # Auto-detecting turn splitter, batch chunker & tiktoken counter
│   ├── extractor.py             # Gemini structured output delta extractor + offline fallback
│   ├── reducer.py               # Deterministic state merge, deprecation & bug-clearance engine
│   ├── compiler.py              # Priority-trimmed Markdown prompt compiler
│   ├── cli.py                   # Typer + Rich terminal CLI
│   └── api.py                   # FastAPI microservice (POST /compile)
│
├── tests/
│   ├── test_reducer.py          # Unit tests for deduplication, deprecation & bug resolution
│   └── test_compiler.py         # Unit tests for token-budget enforcement & priority trimming
│
├── requirements.txt
└── README.md
```

---

## Design Philosophy

StateBridge follows one central principle:

**LLMs extract meaning. Deterministic code manages state.**

By separating probabilistic semantic understanding from deterministic state management, StateBridge aims to make long-running LLM engineering workflows more predictable, portable, and efficient.

The result is a compact, structured handoff that preserves essential project context without carrying the entire conversation history into every new session.