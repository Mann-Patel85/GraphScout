"""GraphScout Main Entrypoint.

Provides CLI commands to run agentic investigation or execute 3-way benchmarking.
"""

from __future__ import annotations

import argparse
import logging
import sys
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree

try:  # Load LLM keys / NEO4J_* from a .env file if one exists
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.agents.orchestrator import OrchestratorAgent
from src.agents.state import GraphScoutState
from src.db.graph_client import create_graph_client
from src.evaluation.benchmark_runner import BenchmarkRunner
from src.utils.llm_client import LLMClient

console = Console()


def run_investigation(query: str) -> None:
    """Run GraphScout Orchestrator on a user query."""
    console.print(Panel(f"[bold cyan]Query:[/bold cyan] {query}", title="GraphScout Autonomous Investigation"))
    
    tg_client = create_graph_client()

    llm_client = LLMClient()
    orchestrator = OrchestratorAgent(tg_client=tg_client, llm_client=llm_client)

    state: GraphScoutState = orchestrator.run(query)

    # Render Step Tree
    tree = Tree("[bold green]Execution Traces[/bold green]")
    for step in state.step_history:
        step_branch = tree.add(f"[bold yellow]Step {step.step_index}[/bold yellow] ({step.action_taken.value}) - {step.duration_ms:.1f}ms")
        step_branch.add(f"Reasoning: {step.reasoning}")
        step_branch.add(f"Output: {step.tool_outputs_summary}")
    console.print(tree)

    console.print(Panel(
        f"[bold green]Answer:[/bold green]\n{state.final_answer}\n\n"
        f"[dim]Tokens used: {state.token_metrics.total_tokens} | "
        f"Entities discovered: {len(state.retrieved_entities)} | "
        f"Latency: {state.total_latency_seconds:.2f}s[/dim]",
        title="Final Answer & Evidence Summary"
    ))


def run_benchmark(dataset_path: str = "data/eval_public.jsonl", limit: int = 10) -> None:
    """Run 3-way benchmark suite across test dataset."""
    import json
    from pathlib import Path

    tg_client = create_graph_client()

    runner = BenchmarkRunner(tg_client=tg_client)
    
    data_file = Path(dataset_path)
    if not data_file.exists():
        data_file = Path(__file__).resolve().parent.parent / dataset_path
    questions = []
    if data_file.exists():
        if dataset_path.endswith(".jsonl"):
            with open(data_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        questions.append(json.loads(line))
        else:
            with open(data_file, "r", encoding="utf-8") as f:
                questions = json.load(f)
    else:
        questions = [
            {"question": "What are the supply chain bottlenecks affecting Project Titan developed by Company Alpha?"},
            {"question": "How does Supplier Omega impact Company Alpha's initiatives?"},
        ]

    # Run on subset
    selected_questions = questions[:limit]
    console.print(f"[bold green]Running benchmark on {len(selected_questions)} questions from {dataset_path}...[/bold green]")
    runner.run_benchmark(selected_questions, output_json_path="results/benchmark_report.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="GraphScout - Agentic GraphRAG System")
    parser.add_argument("--query", type=str, help="Run single agentic investigation on user query")
    parser.add_argument("--benchmark", action="store_true", help="Run 3-way benchmarking harness")
    parser.add_argument("--dataset", type=str, default="data/eval_public.jsonl", help="Dataset file path for benchmark")
    parser.add_argument("--limit", type=int, default=5, help="Number of questions to evaluate (default: 5)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    if args.benchmark:
        run_benchmark(dataset_path=args.dataset, limit=args.limit)
    elif args.query:
        run_investigation(args.query)
    else:
        # Default demo query
        run_investigation("Who won the gold medal in the event held at Eton Dorney on 6 to 8 August at the 2012 Summer Olympics?")


if __name__ == "__main__":
    main()
