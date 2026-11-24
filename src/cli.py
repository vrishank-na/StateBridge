from pathlib import Path
from typing import Optional
import tkinter as tk
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.schema import ProjectState
from src.parser import count_tokens, parse_raw_chat, chunk_turns, load_and_prepare_chat
from src.extractor import extract_delta
from src.reducer import apply_delta
from src.compiler import compile_handoff

app = typer.Typer(
    name="statebridge",
    help="Deterministic cross-session state compiler for long LLM engineering chats.",
    add_completion=False,
)
console = Console()


def _read_clipboard() -> str:
    """Reads plain text directly from the OS clipboard using standard-library tkinter."""
    root = tk.Tk()
    root.withdraw()
    try:
        return root.clipboard_get()
    finally:
        root.destroy()


@app.command()
def compile(
    chat_file: Optional[str] = typer.Argument(None, help="Path to raw chat log (.txt, .md, or .json)"),
    clipboard: bool = typer.Option(False, "--clipboard", "-c", help="Read copied chat directly from clipboard"),
    budget: int = typer.Option(500, "--budget", "-b", help="Maximum allowed tokens in compiled output"),
    batch_size: int = typer.Option(4, "--batch-size", help="Number of turns processed per delta batch"),
    model: str = typer.Option("gemini-3.1-flash-lite", "--model", "-m", help="Primary Gemini model for extraction"),
    mock: bool = typer.Option(False, "--mock", help="Use offline deterministic extractor (no API calls)"),
    out: Optional[str] = typer.Option(None, "--out", "-o", help="Optional path to save the compiled prompt"),
):
    """Compile any raw chat log or clipboard transcript into a token-budgeted handoff prompt."""
    if clipboard:
        console.print("[bold cyan]StateBridge[/bold cyan] reading transcript from [yellow]clipboard[/yellow]...")
        raw_text = _read_clipboard()
        raw_tokens = count_tokens(raw_text)
        turns = parse_raw_chat(raw_text)
        batches = chunk_turns(turns, batch_size=batch_size)
    elif chat_file:
        console.print(f"[bold cyan]StateBridge[/bold cyan] loading [yellow]{chat_file}[/yellow]...")
        batches, raw_tokens = load_and_prepare_chat(chat_file, batch_size=batch_size)
    else:
        console.print("[bold red]Error:[/bold red] Provide a chat file path or pass [yellow]--clipboard[/yellow].")
        raise typer.Exit(code=1)

    state = ProjectState()
    with console.status("[bold green]Extracting state deltas & reducing state...[/bold green]"):
        for batch in batches:
            delta = extract_delta(batch, state, model_name=model, use_mock=mock)
            state = apply_delta(state, delta)

    handoff = compile_handoff(state, raw_tokens=raw_tokens, max_tokens=budget)

    metrics = Table(title="StateBridge Compression Summary", show_header=True, header_style="bold magenta")
    metrics.add_column("Metric", style="cyan")
    metrics.add_column("Value", style="bold white")
    metrics.add_row("Batches Processed", str(len(batches)))
    metrics.add_row("Original Chat Tokens", str(handoff.raw_tokens))
    metrics.add_row("Compiled Handoff Tokens", f"{handoff.compiled_tokens} / {handoff.budget}")
    metrics.add_row("Tokens Saved", f"{handoff.compression_ratio}%")
    metrics.add_row("Priority Trimming Applied", "Yes" if handoff.was_trimmed else "No")
    console.print(metrics)

    console.print(Panel(handoff.prompt, title="Compiled Handoff Prompt", border_style="green"))

    if out:
        Path(out).write_text(handoff.prompt, encoding="utf-8")
        console.print(f"[bold green]Saved compiled prompt to {out}[/bold green]")


if __name__ == "__main__":
    app()