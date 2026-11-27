"""3-Way Benchmarking Runner for GraphScout.

Compares Standard RAG vs GraphRAG vs Agentic GraphRAG
across Accuracy, Answer Completeness, Token Efficiency, and Latency.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from rich.console import Console
from rich.table import Table

from src.agents.orchestrator import OrchestratorAgent
from src.db.graph_client import GraphClient, create_graph_client
from src.evaluation.metrics import GroundTruth, answer_accuracy, context_recall, extract_ground_truth
from src.pipelines.agentic_rag import AgenticRAGPipeline
from src.pipelines.graph_rag import GraphRAGPipeline
from src.pipelines.standard_rag import StandardRAGPipeline
from src.utils.llm_client import LLMClient

logger = logging.getLogger("GraphScout.BenchmarkRunner")
console = Console()


def _fmt_score(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value:.2f}"


class BenchmarkRunner:
    """Benchmark runner orchestrating side-by-side evaluation across 3 RAG paradigms."""

    def __init__(
        self,
        tg_client: Optional[GraphClient] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        self.tg_client = tg_client or create_graph_client()
        self.llm_client = llm_client or LLMClient()

        self.standard_rag = StandardRAGPipeline(self.tg_client, self.llm_client)
        self.graph_rag = GraphRAGPipeline(self.tg_client, self.llm_client)
        
        orchestrator = OrchestratorAgent(self.tg_client, self.llm_client)
        self.agentic_rag = AgenticRAGPipeline(orchestrator)

    def evaluate_question(self, question: str, ground_truth: GroundTruth = None) -> Dict[str, Any]:
        """Run all 3 pipelines on a single benchmark question and score them against ground truth."""
        console.print(f"\n[bold cyan]=== Evaluating Question: '{question}' ===[/bold cyan]")

        refs = extract_ground_truth({"ground_truth": ground_truth})
        output: Dict[str, Any] = {
            "question": question,
            "ground_truth": "; ".join(refs) if refs else None,
        }
        for name, pipeline in (
            ("standard_rag", self.standard_rag),
            ("graph_rag", self.graph_rag),
            ("agentic_rag", self.agentic_rag),
        ):
            res = pipeline.run(question)
            res.accuracy_score = answer_accuracy(res.answer, refs)
            res.completeness_score = context_recall(res.retrieved_context, refs)
            output[name] = res.model_dump()
        return output

    def run_benchmark(
        self,
        questions_dataset: List[Dict[str, str]],
        output_json_path: Optional[str] = "results/benchmark_report.json",
    ) -> pd.DataFrame:
        """Run full evaluation suite across dataset questions."""
        all_results = []
        rows = []

        for item in questions_dataset:
            q = item.get("question", "")
            result = self.evaluate_question(q, extract_ground_truth(item))
            all_results.append(result)

            for pipe_name in ["standard_rag", "graph_rag", "agentic_rag"]:
                p_data = result[pipe_name]
                rows.append({
                    "Question": q[:35] + "..." if len(q) > 35 else q,
                    "Pipeline": pipe_name,
                    "Accuracy": _fmt_score(p_data.get("accuracy_score")),
                    "Completeness": _fmt_score(p_data.get("completeness_score")),
                    "Tokens": p_data.get("total_tokens", 0),
                    "Latency (s)": round(p_data.get("latency_seconds", 0.0), 3),
                    "Entities": p_data.get("retrieved_entities_count", 0),
                    "Chunks": p_data.get("retrieved_chunks_count", 0),
                })

        df = pd.DataFrame(rows)
        self._display_summary_table(df)

        if output_json_path:
            out_file = Path(output_json_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(all_results, f, indent=2)
            console.print(f"[bold green]Saved benchmark results to {output_json_path}[/bold green]")

        return df

    def _display_summary_table(self, df: pd.DataFrame) -> None:
        """Render Rich table summary."""
        table = Table(title="GraphScout 3-Way Benchmark Results", header_style="bold magenta")
        table.add_column("Question", style="dim", width=35)
        table.add_column("Pipeline", style="bold yellow")
        table.add_column("Accuracy", justify="right")
        table.add_column("Completeness", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Latency (s)", justify="right")
        table.add_column("Entities", justify="right")
        table.add_column("Chunks", justify="right")

        for _, row in df.iterrows():
            table.add_row(
                str(row["Question"]),
                str(row["Pipeline"]),
                str(row["Accuracy"]),
                str(row["Completeness"]),
                str(row["Tokens"]),
                str(row["Latency (s)"]),
                str(row["Entities"]),
                str(row["Chunks"]),
            )

        console.print(table)
