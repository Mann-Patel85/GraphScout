"""3-Way Benchmarking Harness for GraphScout.

Compares Standard RAG vs GraphRAG vs Agentic GraphRAG on TigerGraph
across latency, token efficiency, retrieval completeness, and answer quality.
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
from src.benchmark.agentic_rag import AgenticRAGPipeline
from src.benchmark.graph_rag import GraphRAGPipeline
from src.benchmark.standard_rag import StandardRAGPipeline
from src.db.tigergraph_client import TigerGraphClient, TigerGraphConfig
from src.utils.llm_client import LLMClient

logger = logging.getLogger("GraphScout.BenchmarkHarness")
console = Console()


class BenchmarkHarness:
    """Benchmark runner orchestrating side-by-side evaluation."""

    def __init__(
        self,
        tg_client: Optional[TigerGraphClient] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        self.tg_client = tg_client or TigerGraphClient()
        self.llm_client = llm_client or LLMClient()

        self.standard_rag = StandardRAGPipeline(self.tg_client, self.llm_client)
        self.graph_rag = GraphRAGPipeline(self.tg_client, self.llm_client)
        
        orchestrator = OrchestratorAgent(self.tg_client, self.llm_client)
        self.agentic_rag = AgenticRAGPipeline(orchestrator)

    def evaluate_query(self, query: str) -> Dict[str, Any]:
        """Run all 3 pipelines on a single benchmark query."""
        console.print(f"\n[bold cyan]=== Evaluating Query: '{query}' ===[/bold cyan]")
        
        res_std = self.standard_rag.run(query)
        res_graph = self.graph_rag.run(query)
        res_agentic = self.agentic_rag.run(query)

        return {
            "query": query,
            "standard_rag": res_std.model_dump(),
            "graph_rag": res_graph.model_dump(),
            "agentic_rag": res_agentic.model_dump(),
        }

    def run_suite(self, queries: List[str], output_json_path: Optional[str] = None) -> pd.DataFrame:
        """Run full evaluation suite over a set of test queries."""
        all_results = []
        rows = []

        for q in queries:
            result = self.evaluate_query(q)
            all_results.append(result)

            for pipe_name in ["standard_rag", "graph_rag", "agentic_rag"]:
                p_data = result[pipe_name]
                rows.append({
                    "Query": q[:40] + "..." if len(q) > 40 else q,
                    "Pipeline": pipe_name,
                    "Total Tokens": p_data.get("total_tokens", 0),
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
        table = Table(title="GraphScout 3-Way Benchmark Summary", header_style="bold magenta")
        table.add_column("Query", style="dim", width=35)
        table.add_column("Pipeline", style="bold yellow")
        table.add_column("Tokens", justify="right")
        table.add_column("Latency (s)", justify="right")
        table.add_column("Entities", justify="right")
        table.add_column("Chunks", justify="right")

        for _, row in df.iterrows():
            table.add_row(
                str(row["Query"]),
                str(row["Pipeline"]),
                str(row["Total Tokens"]),
                str(row["Latency (s)"]),
                str(row["Entities"]),
                str(row["Chunks"]),
            )

        console.print(table)
