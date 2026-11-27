export interface LlmInfo {
  /** "openai" | "groq" | "offline" */
  provider: string;
  live: boolean;
  default_model: string;
  models: string[];
}

/** Which LLM actually served a run. */
export interface LlmRunInfo {
  provider: string;
  model: string;
  live: boolean;
  /** calls that failed and returned a placeholder instead of a model answer */
  fallback_calls: number;
}

export interface SystemStatus {
  status: string;
  engine: string;
  graph: {
    /** "neo4j" | "memory" */
    backend: string;
    label: string;
    /** false for the in-memory graph, which is rebuilt on every start */
    persistent: boolean;
    location: string | null;
    database: string | null;
    indexed_entities: number;
    indexed_relations: number;
    indexed_chunks: number;
  };
  llm: LlmInfo;
  datasets: {
    corpus_documents: number;
    corpus_file: string | null;
    eval_public_questions: number;
    eval_hidden_questions: number;
    sample_questions_available: boolean;
  };
}

export interface PresetQuery {
  id: string;
  category: string;
  query: string;
  hops: number;
  tags: string[];
}

export interface StepTrace {
  step_index: number;
  action_taken: string;
  reasoning: string;
  tool_outputs_summary: string;
  entities_discovered: string[];
  chunks_retrieved_count: number;
  duration_ms: number;
  tool_inputs: {
    search_queries?: string[];
    seed_entities?: string[];
    max_hops?: number;
    updated_hypothesis?: string | null;
    /** find_events filters (sport, year, venue, date, sort_by, …) */
    event_filter?: Record<string, unknown>;
    [key: string]: unknown;
  };
}

export interface GraphNode {
  id: string;
  label: string;
  title: string;
  group: string;
  entity_type: string;
  description?: string | null;
  aliases?: string[];
  hops?: number;
  confidence?: number;
}

export interface GraphEdge {
  from: string;
  to: string;
  label: string;
  title: string;
  relation_type: string;
  confidence: number;
  arrows?: string;
}

export interface SubgraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  total_nodes: number;
  total_edges: number;
}

export interface DocumentChunk {
  chunk_id: string;
  doc_id?: string | null;
  section_header: string;
  text_content: string;
  score: number;
  token_count: number;
  associated_entities: string[];
}

export interface InvestigationResult {
  query: string;
  final_answer: string;
  latency_seconds: number;
  hypothesis: string;
  metrics: {
    total_tokens: number;
    prompt_tokens: number;
    completion_tokens: number;
    estimated_cost_usd: number;
    calls_count: number;
    entities_discovered: number;
    reasoning_steps: number;
    /** evaluator agent's self-assessment, 0 if no evaluation step ran */
    completeness_score: number;
    completeness_pct: number;
  };
  steps: StepTrace[];
  subgraph: SubgraphData;
  chunks: DocumentChunk[];
  citation_references: string[];
  stopping_condition_met: boolean;
  llm?: LlmRunInfo;
}

export type PipelineId = "standard_rag" | "graph_rag" | "agentic_rag";

export interface BenchmarkRow {
  question: string;
  ground_truth?: string | null;
  pipeline: PipelineId;
  pipeline_label: string;
  answer: string;
  /** null when the question has no ground truth to score against */
  accuracy: number | null;
  completeness: number | null;
  total_tokens: number;
  latency_seconds: number;
  entities_count: number;
  chunks_count: number;
}

export interface PipelineSummary {
  /** null when no evaluated question had ground truth */
  avg_completeness: number | null;
  avg_accuracy: number | null;
  avg_tokens: number;
  avg_latency: number;
}

export interface BenchmarkResult {
  dataset_name: string;
  questions_evaluated: number;
  total_duration_seconds: number;
  summary: Record<PipelineId, PipelineSummary>;
  rows: BenchmarkRow[];
  raw_results: unknown[];
  llm?: LlmRunInfo;
}

export interface CorpusDocSummary {
  doc_id: string;
  title: string;
  url: string;
  approx_tokens: number;
  snippet: string;
}

export interface CorpusPage {
  total: number;
  offset: number;
  limit: number;
  documents: CorpusDocSummary[];
}

export interface CorpusDocDetail {
  doc_id: string;
  title: string;
  url: string;
  approx_tokens: number;
  infobox: Record<string, string>;
  full_text: string;
}

export interface IngestResult {
  success: boolean;
  docs_ingested: number;
  duration_seconds: number;
  total_entities: number;
  total_chunks: number;
}

export interface GraphSchema {
  backend: string;
  language: string;
  file_path: string;
  code: string;
  nodes: Array<{ name: string; key: string; description: string; attributes: string[] }>;
  relationships: Array<{ name: string; from: string; to: string; type: string; description: string }>;
  queries: Array<{ name: string; parameters: string; description: string }>;
}
