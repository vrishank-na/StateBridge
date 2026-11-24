StateBridge
Deterministic, Model-Agnostic Cross-Session State Compiler for Long LLM Engineering Conversations

Long-running coding sessions with LLMs are vulnerable to context rot. As a conversation grows, important rules can be forgotten, abandoned libraries can reappear, resolved errors can remain as noise, and API latency and costs can increase. Asking an LLM to summarize the conversation often produces unpredictable prose that may omit edge-case constraints or exceed a target token budget.

StateBridge addresses this problem by treating conversation memory as a state machine. It separates semantic extraction, performed incrementally by an LLM, from state mutation and token budgeting, handled deterministically in pure Python. It compiles large, multi-turn chat transcripts into a concise, size-bounded handoff prompt that can be used with Gemini, Claude, ChatGPT, or a local model.
Core architecture
StateBridge processes raw transcripts through a six-stage modular pipeline:
Raw Chat Transcript (JSON / Labeled / Plain Text)
        |
        v
+---------------------+
| 1. Parser           | Splits turns with regex and chunks them into batches
|                     | (default: 4 turns; token counting via tiktoken)
+----------+----------+
           |
           v
+---------------------+
| 2. Extractor        | Extracts structured StateDelta changes using Gemini
|                     | Structured Outputs, with model fallback and mock mode
+----------+----------+
           |
           v
+---------------------+
| 3. Reducer          | Applies deterministic state transitions in pure Python
|                     | Deduplicates rules and clears deprecated/resolved state
+----------+----------+
           |
           v
+---------------------+
| 4. Compiler         | Renders a Markdown handoff prompt and enforces a token budget
|                     | while preserving the core goal and hard constraints
+----------+----------+
           |
           v
       CLI / REST API
           |
           v
Portable handoff prompt for a fresh LLM session
Pipeline components
1. Schema (src/schema.py) — Strict Pydantic v2 models, ProjectState and StateDelta, define typed state mutations instead of relying on unstructured text.
2. Parser and chunker (src/parser.py) — Detects OpenAI/Anthropic JSON message arrays ([{"role": ..., "content": ...}]), labeled transcripts (such as User: / Assistant: and You said: / ChatGPT said:), or unlabeled plain text. It splits the transcript into configurable batches and counts tokens with tiktoken using cl100k_base.
3. LLM delta extractor (src/extractor.py) — Evaluates each four-turn window against the current ProjectState and extracts a structured StateDelta using Google GenAI Structured Outputs (response_schema=StateDelta). It supports automatic model fallback and a deterministic offline --mock mode for development and CI.
4. Deterministic state reducer (src/reducer.py) — Implements pure-Python state transitions through apply_delta. It handles case-insensitive deduplication, moves abandoned tools from tech_stack to deprecated_approaches, and clears resolved bugs using substring matching.
5. Token-budgeted prompt compiler (src/compiler.py) — Compiles ProjectState into a structured Markdown handoff prompt and enforces compiled_tokens <= budget. When the prompt is too large, it removes lower-priority information first, in this order: deprecated_approaches, next_steps, active_bugs, and tech_stack. The core goal and hard constraints are preserved.
6. Interfaces (src/cli.py, src/api.py) — Provides a Typer + Rich command-line interface and a FastAPI microservice with a POST /compile endpoint for integration into AI coding agents and chat pipelines.
Features
- Structured state: Pydantic models represent project state and incremental state changes.
- Incremental extraction: Processes conversation history in small batches against the state accumulated so far.
- Deterministic reduction: Python controls how extracted changes are merged, deduplicated, deprecated, and cleared.
- Token-budget enforcement: Produces a compiled prompt within the requested budget while preserving the core goal and hard constraints.
- Model portability: Produces Markdown that can be handed to Gemini, Claude, ChatGPT, or local models.
- Offline mode: Supports deterministic mock extraction without external API calls.
- Multiple interfaces: Use the CLI for local transcripts or the REST API for programmatic integration.
System setup and installation
Prerequisites
- Python 3.10 or later
- Git
- A Gemini API key from Google AI Studio (optional when using offline mock mode)
1. Clone the repository
Replace <your-username> with the GitHub account or organization that hosts the repository.
git clone https://github.com/<your-username>/StateBridge.git
cd StateBridge
2. Create and activate a virtual environment
Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1
If PowerShell blocks script activation, run the following once, or activate the environment from Command Prompt instead:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
Windows (Command Prompt):
venv\Scripts\activate.bat
macOS / Linux:
python3 -m venv venv
source venv/bin/activate
3. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
4. Configure environment variables
Create a .env file in the repository root and add your Gemini API key.

Windows (PowerShell):
Set-Content -Path .env -Value "GEMINI_API_KEY=your_gemini_api_key_here"
macOS / Linux:
echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env
Keep .env out of version control. Do not commit API keys or other secrets.
How to use StateBridge
1. REST API integration
In an agent or application workflow, StateBridge can be called when the conversation history reaches a chosen token threshold. The API accepts a transcript and a target output budget, then returns a compiled handoff prompt.

Start the FastAPI server from the repository root:
uvicorn src.api:app --reload
Send a request to POST /compile:
curl -X POST "http://127.0.0.1:8000/compile" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_chat": "[{\"role\": \"user\", \"content\": \"Build a FastAPI service with PostgreSQL. Never use an ORM.\"}]",
    "budget": 300,
    "use_mock": false
  }'
The example sends a single user message and requests a 300-token compiled prompt. Set use_mock to true to use the offline mock extractor.

Interactive API documentation is available at:
http://127.0.0.1:8000/docs
2. Command-line interface
Use the CLI to compile saved session logs, exported JSON chats, or clipboard transcripts into a token-budgeted Markdown file. The output can be used as a handoff prompt or adapted for files such as .cursorrules and CLAUDE.md.

Compile a transcript using live Gemini extraction:
python -m src.cli benchmarks/enterprise_session.txt --budget 300
Save the compiled prompt to a file:
python -m src.cli benchmarks/enterprise_session.txt --budget 300 --out handoff.md
Run offline with the deterministic mock extractor:
python -m src.cli benchmarks/enterprise_session.txt --budget 300 --mock
Read a transcript from the system clipboard:
python -m src.cli --clipboard --budget 300 --mock
CLI options
Option	Default	Description
CHAT_FILE	None	Path to a .txt, .md, or .json transcript
--clipboard, -c	False	Read input directly from the system clipboard
--budget, -b	500	Maximum token count for the compiled output prompt
--batch-size	4	Number of conversation turns processed in each delta batch
--model, -m	gemini-3.1-flash-lite	Primary Gemini model used for delta extraction
--mock	False	Use the local deterministic extractor without external API calls
--out, -o	None	Optional path for saving the compiled Markdown prompt


3. Run tests and benchmarks
Run the unit test suite:
pytest -v
Run compression benchmarks over the sample transcripts in benchmarks/:
python -m benchmarks.evaluate --budget 300
Run the benchmarks with live Gemini extraction:
python -m benchmarks.evaluate --budget 300 --live
The tests cover deterministic state reduction, including deduplication, deprecation, and bug resolution, as well as token-budget enforcement and priority-based trimming. The benchmark runner evaluates compression across multiple sample transcripts.
Project structure
StateBridge/
├── benchmarks/
│   ├── evaluate.py              # Multi-file token compression benchmark runner
│   ├── sample_chat.txt           # Short baseline conversation transcript
│   ├── long_session.txt          # Multi-turn webhook service debugging session
│   └── enterprise_session.txt    # 44-turn IoT ingestion session with 4 stack pivots
├── src/
│   ├── schema.py                 # ProjectState and StateDelta Pydantic v2 schemas
│   ├── parser.py                 # Transcript detection, turn splitting, batching, token counting
│   ├── extractor.py              # Gemini structured-output extractor and offline fallback
│   ├── reducer.py                # Deterministic state merge, deprecation, and bug clearance
│   ├── compiler.py               # Priority-trimmed Markdown prompt compiler
│   ├── cli.py                    # Typer + Rich command-line interface
│   └── api.py                    # FastAPI microservice (POST /compile)
├── tests/
│   ├── test_reducer.py           # Tests for deduplication, deprecation, and bug resolution
│   └── test_compiler.py          # Tests for token-budget enforcement and priority trimming
├── requirements.txt
└── README.md
Design principles
- LLMs interpret; Python enforces. The extractor proposes structured changes, while deterministic code applies those changes and enforces the output budget.
- Preserve critical project context. The compiler prioritizes the core goal and hard constraints over lower-priority context when trimming.
- Keep state portable. The compiled output is Markdown, so it can be passed into a new session or a different model without requiring a model-specific memory format.
- Support reproducible local testing. Mock mode allows the pipeline to be exercised without a Gemini API key or network calls.
License
Add the license and attribution details for this project here before publishing or distributing it.