import {
  BenchmarkResult,
  CorpusDocDetail,
  CorpusPage,
  GraphSchema,
  IngestResult,
  InvestigationResult,
  PresetQuery,
  SystemStatus,
} from "./types";

const API_BASE = "";

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

/** fetch wrapper: JSON in/out, readable errors (incl. "backend not running"), abort support. */
async function request<T>(path: string, init: RequestInit = {}, fallbackError = "Request failed"): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: init.body ? { "Content-Type": "application/json", ...init.headers } : init.headers,
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    throw new ApiError("Cannot reach the backend. Is it running on port 8000? (python run.py)");
  }

  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? "");
    } catch {
      /* non-JSON error body */
    }
    if (res.status >= 500 && !detail) {
      detail = "The backend returned a server error. Check the backend terminal for details.";
    }
    throw new ApiError(detail || `${fallbackError} (HTTP ${res.status})`, res.status);
  }
  return res.json() as Promise<T>;
}

export const getSystemStatus = () => request<SystemStatus>("/api/status", {}, "Failed to fetch system status");

export const getPresetQueries = () => request<PresetQuery[]>("/api/presets", {}, "Failed to fetch presets");

export function runInvestigation(
  params: {
    query: string;
    model: string;
    temperature: number;
    max_hops: number;
    completeness_threshold: number;
    token_budget: number;
  },
  signal?: AbortSignal
) {
  return request<InvestigationResult>(
    "/api/investigate",
    { method: "POST", body: JSON.stringify({ ...params, model: params.model || null }), signal },
    "Investigation failed"
  );
}

export function runBenchmark(
  params: { dataset: string; limit: number; model: string; temperature?: number },
  signal?: AbortSignal
) {
  return request<BenchmarkResult>(
    "/api/benchmark",
    { method: "POST", body: JSON.stringify({ ...params, model: params.model || null }), signal },
    "Benchmark failed"
  );
}

export function getCorpusDocuments(query = "", limit = 24, offset = 0) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (query) params.set("query", query);
  return request<CorpusPage>(`/api/corpus?${params}`, {}, "Failed to fetch corpus documents");
}

export const getCorpusDocDetail = (docId: string) =>
  request<CorpusDocDetail>(`/api/corpus/${encodeURIComponent(docId)}`, {}, `Failed to fetch document ${docId}`);

export const ingestCorpus = (maxDocs = 100) =>
  request<IngestResult>("/api/ingest", { method: "POST", body: JSON.stringify({ max_docs: maxDocs }) }, "Ingestion failed");

export const getGraphSchema = () => request<GraphSchema>("/api/schema", {}, "Failed to fetch graph schema");
