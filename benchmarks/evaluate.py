import argparse
from pathlib import Path
from rich.console import Console
from rich.table import Table

from src.schema import ProjectState
from src.parser import load_and_prepare_chat
from src.extractor import extract_delta
from src.reducer import apply_delta
from src.compiler import compile_handoff


def run_benchmarks(budget: int = 250, use_mock: bool = True):
    console = Console()
    chat_files = sorted(Path("benchmarks").glob("*.txt"))

    if not chat_files:
        console.print("[red]No .txt files found in benchmarks/[/red]")
        return

    table = Table(title=f"StateBridge Benchmark Results (Budget: {budget} tokens)")
    table.add_column("Chat File", style="cyan")
    table.add_column("Batches", justify="right")
    table.add_column("Raw Tokens", justify="right")
    table.add_column("Compiled Tokens", justify="right", style="green")
    table.add_column("Reduction", justify="right", style="bold magenta")
    table.add_column("Trimmed?", justify="center")

    for file_path in chat_files:
        batches, raw_tokens = load_and_prepare_chat(str(file_path))
        state = ProjectState()
        for batch in batches:
            delta = extract_delta(batch, state, use_mock=use_mock)
            state = apply_delta(state, delta)

        result = compile_handoff(state, raw_tokens=raw_tokens, max_tokens=budget)
        table.add_row(
            file_path.name,
            str(len(batches)),
            str(result.raw_tokens),
            str(result.compiled_tokens),
            f"{result.compression_ratio}%",
            "Yes" if result.was_trimmed else "No",
        )

    console.print(table)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run StateBridge compression benchmarks.")
    parser.add_argument("--budget", type=int, default=250, help="Target token budget")
    parser.add_argument("--live", action="store_true", help="Use live Gemini API instead of mock mode")
    args = parser.parse_args()
    run_benchmarks(budget=args.budget, use_mock=not args.live)