from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.schema import ProjectState
from src.parser import count_tokens, parse_raw_chat, chunk_turns
from src.extractor import extract_delta
from src.reducer import apply_delta
from src.compiler import compile_handoff

app = FastAPI(
    title="StateBridge API",
    description="Deterministic cross-session state compiler for long LLM engineering conversations.",
    version="1.0.0",
)


class CompileRequest(BaseModel):
    raw_chat: str = Field(..., min_length=1, description="Raw multi-turn conversation transcript")
    budget: int = Field(default=500, gt=50, le=8000, description="Target max token budget")
    batch_size: int = Field(default=4, ge=1, le=20, description="Turns per extraction batch")
    model: str = Field(default="gemini-3.1-flash-lite", description="Gemini extraction model")
    use_mock: bool = Field(default=False, description="Run offline deterministic extraction")


class CompileResponse(BaseModel):
    prompt: str
    state: ProjectState
    raw_tokens: int
    compiled_tokens: int
    budget: int
    compression_ratio: float
    was_trimmed: bool


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "StateBridge"}


@app.post("/compile", response_model=CompileResponse)
def compile_endpoint(req: CompileRequest):
    try:
        raw_tokens = count_tokens(req.raw_chat)
        turns = parse_raw_chat(req.raw_chat)
        batches = chunk_turns(turns, batch_size=req.batch_size)

        state = ProjectState()
        for batch in batches:
            delta = extract_delta(batch, state, model_name=req.model, use_mock=req.use_mock)
            state = apply_delta(state, delta)

        handoff = compile_handoff(state, raw_tokens=raw_tokens, max_tokens=req.budget)

        return CompileResponse(
            prompt=handoff.prompt,
            state=state,
            raw_tokens=handoff.raw_tokens,
            compiled_tokens=handoff.compiled_tokens,
            budget=handoff.budget,
            compression_ratio=handoff.compression_ratio,
            was_trimmed=handoff.was_trimmed,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc