"""LLM Client Utility for GraphScout.

Structured generation, text generation and embeddings over any OpenAI-compatible
provider (OpenAI, Groq), with an offline simulation fallback when no key is set.

Provider selection (first match wins):
  1. ``LLM_PROVIDER`` env var ("openai" or "groq"), using that provider's key
  2. ``OPENAI_API_KEY`` set  -> OpenAI
  3. ``GROQ_API_KEY`` set    -> Groq
  4. otherwise               -> offline simulation (canned demo responses)
``LLM_MODEL`` optionally overrides the provider's default model.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar

from pydantic import BaseModel

from src.utils.embeddings import local_embed
from src.utils.env import load_backend_env

logger = logging.getLogger("GraphScout.LLMClient")

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    key_env: str
    base_url: Optional[str]
    default_model: str
    models: List[str] = field(default_factory=list)
    supports_embeddings: bool = False


PROVIDERS: Dict[str, ProviderSpec] = {
    "openai": ProviderSpec(
        name="openai",
        key_env="OPENAI_API_KEY",
        base_url=None,
        default_model="gpt-4o",
        models=["gpt-4o", "gpt-4o-mini"],
        supports_embeddings=True,
    ),
    "groq": ProviderSpec(
        name="groq",
        key_env="GROQ_API_KEY",
        base_url="https://api.groq.com/openai/v1",
        default_model="openai/gpt-oss-120b",
        models=["openai/gpt-oss-120b", "openai/gpt-oss-20b"],
        supports_embeddings=False,
    ),
}


def resolve_provider() -> Tuple[Optional[ProviderSpec], str]:
    """Return the configured provider and its API key, or (None, "") for offline mode."""
    load_backend_env()
    forced = os.getenv("LLM_PROVIDER", "").strip().lower()
    if forced:
        spec = PROVIDERS.get(forced)
        if spec is None:
            logger.warning("Unknown LLM_PROVIDER '%s'; expected one of %s.", forced, list(PROVIDERS))
        else:
            return (spec, os.getenv(spec.key_env, "")) if os.getenv(spec.key_env) else (None, "")
    for spec in PROVIDERS.values():
        key = os.getenv(spec.key_env, "")
        if key:
            return spec, key
    return None, ""


def available_models() -> Dict[str, Any]:
    """Describe the active provider and selectable models (for the UI)."""
    spec, _ = resolve_provider()
    if spec is None:
        return {"provider": "offline", "live": False, "default_model": "simulated", "models": ["simulated"]}
    default = os.getenv("LLM_MODEL") or spec.default_model
    models = list(dict.fromkeys([default, *spec.models]))
    return {"provider": spec.name, "live": True, "default_model": default, "models": models}


class LLMClient:
    """Unified wrapper around OpenAI-compatible LLM providers with token tracking."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.1,
        api_key: Optional[str] = None,
        embedding_model: str = "text-embedding-3-small",
    ):
        self.temperature = temperature
        self.embedding_model = embedding_model
        self._openai_client = None
        # Number of calls that failed and were answered by the offline simulator instead.
        self.fallback_calls = 0

        if api_key:
            self.provider: Optional[ProviderSpec] = PROVIDERS["openai"]
            self.api_key = api_key
        else:
            self.provider, self.api_key = resolve_provider()

        self.model_name = self._pick_model(model_name)
        self._init_client()

    def _pick_model(self, requested: Optional[str]) -> str:
        if self.provider is None:
            return requested or "simulated"
        if requested and requested in self.provider.models:
            return requested
        chosen = os.getenv("LLM_MODEL") or self.provider.default_model
        if requested and requested != chosen:
            logger.info("Model '%s' is not offered by %s; using '%s'.", requested, self.provider.name, chosen)
        return chosen

    def _init_client(self) -> None:
        if not (self.provider and self.api_key):
            logger.info("No LLM API key configured; running in offline simulation mode.")
            return
        try:
            from openai import OpenAI
            # Extra retries: free tiers (e.g. Groq) return 429 when the per-minute token
            # budget is exhausted; the SDK backs off and retries automatically.
            self._openai_client = OpenAI(api_key=self.api_key, base_url=self.provider.base_url, max_retries=5)
        except Exception as exc:
            logger.warning("LLM client initialization failed: %s", exc)

    @property
    def is_live(self) -> bool:
        return self._openai_client is not None

    @property
    def provider_name(self) -> str:
        return self.provider.name if (self.provider and self.is_live) else "offline"

    @staticmethod
    def _usage(response: Any) -> Dict[str, int]:
        u = getattr(response, "usage", None)
        return {
            "prompt_tokens": getattr(u, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(u, "completion_tokens", 0) or 0,
        }

    def generate_json(self, system_prompt: str, user_prompt: str, schema_cls: Type[T]) -> Tuple[T, Dict[str, int]]:
        """Generate a structured Pydantic response.

        Tries native structured outputs first, then JSON mode with the schema in the
        prompt, and only then falls back to the offline simulator.
        """
        if not self._openai_client:
            return self._mock_structured_response(system_prompt, user_prompt, schema_cls)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            response = self._openai_client.chat.completions.parse(
                model=self.model_name,
                messages=messages,
                response_format=schema_cls,
                temperature=self.temperature,
            )
            parsed = response.choices[0].message.parsed
            if parsed is not None:
                return parsed, self._usage(response)
            logger.warning("Structured output returned no parsed object; retrying in JSON mode.")
        except Exception as exc:
            logger.warning("Structured output failed for %s (%s); retrying in JSON mode.", schema_cls.__name__, exc)

        try:
            schema = json.dumps(schema_cls.model_json_schema())
            json_messages = [
                {
                    "role": "system",
                    "content": f"{system_prompt}\n\nRespond with ONLY a JSON object that conforms to this JSON schema:\n{schema}",
                },
                {"role": "user", "content": user_prompt},
            ]
            response = self._openai_client.chat.completions.create(
                model=self.model_name,
                messages=json_messages,
                response_format={"type": "json_object"},
                temperature=self.temperature,
            )
            content = response.choices[0].message.content or "{}"
            return schema_cls.model_validate_json(content), self._usage(response)
        except Exception as exc:
            self.fallback_calls += 1
            logger.error("LLM JSON generation failed for %s: %s", schema_cls.__name__, exc)
            return self._failure_response(schema_cls, exc), {"prompt_tokens": 0, "completion_tokens": 0}

    @staticmethod
    def _failure_response(schema_cls: Type[T], exc: Exception) -> T:
        """Safe, clearly-labelled result for a failed *live* call (never the canned demo data)."""
        reason = str(exc)
        if "rate_limit" in reason or "413" in reason or "429" in reason:
            reason = "provider rate/size limit exceeded"
        reason = reason[:200]
        name = schema_cls.__name__
        if name == "OrchestratorDecision":
            data: Dict[str, Any] = {"action": "finish", "reasoning": f"Stopping: LLM call failed ({reason})."}
        elif name == "SynthesisResult":
            data = {"answer": f"⚠ Could not synthesize an answer: the LLM call failed ({reason})."}
        elif name == "EvaluationVerdict":
            data = {"completeness_score": 0.0, "confidence_rationale": f"Evaluation failed ({reason})."}
        else:
            data = {}
        return schema_cls.model_validate(data)

    def generate_text(self, system_prompt: str, user_prompt: str) -> Tuple[str, Dict[str, int]]:
        """Generate unstructured text completion."""
        if not self._openai_client:
            return f"[Simulated Response for: {user_prompt[:50]}...]", {"prompt_tokens": 50, "completion_tokens": 30}

        try:
            response = self._openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
            )
            return response.choices[0].message.content or "", self._usage(response)
        except Exception as exc:
            self.fallback_calls += 1
            logger.error("Text LLM call failed: %s", exc)
            return "[LLM call failed; no answer generated]", {"prompt_tokens": 0, "completion_tokens": 0}

    def get_embedding(self, text: str) -> List[float]:
        """Embed text: provider embeddings when available, otherwise the local hashed embedder."""
        if self._openai_client and self.provider and self.provider.supports_embeddings:
            try:
                res = self._openai_client.embeddings.create(input=[text], model=self.embedding_model)
                return res.data[0].embedding
            except Exception as exc:
                logger.warning("Embedding call failed (%s). Using local embedding.", exc)
        return local_embed(text)

    def _mock_structured_response(self, system_prompt: str, user_prompt: str, schema_cls: Type[T]) -> Tuple[T, Dict[str, int]]:
        """Construct fallback Pydantic instances when running in simulated or offline mode."""
        fields = schema_cls.model_fields
        mock_data: Dict[str, Any] = {}
        schema_name = schema_cls.__name__

        if schema_name == "OrchestratorDecision":
            if "INITIAL STEP" in user_prompt.upper() or "ITERATION: 0" in user_prompt:
                mock_data["action"] = "graph_traversal"
                mock_data["reasoning"] = "Expanding initial multi-hop relationship graph around seed entities."
                mock_data["seed_entities"] = ["Company_Alpha", "Project_Titan", "Supplier_Omega"]
                mock_data["max_hops"] = 2
            elif "ITERATION: 1" in user_prompt or "ITERATION: 2" in user_prompt:
                mock_data["action"] = "vector_search"
                mock_data["reasoning"] = "Retrieving backing document chunks for risk and bottleneck evidence."
                mock_data["search_queries"] = ["Project Titan supply chain constraints Supplier Omega export bans"]
            elif "ITERATION: 3" in user_prompt or "ITERATION: 4" in user_prompt:
                mock_data["action"] = "evaluate_evidence"
                mock_data["reasoning"] = "Evaluating accumulated graph and chunk evidence for query completeness."
            else:
                mock_data["action"] = "finish"
                mock_data["reasoning"] = "Complete evidence gathered across multi-hop graph and supporting chunks."

        elif schema_name == "SynthesisResult":
            mock_data["answer"] = (
                "Company Alpha developed Project Titan (high-density battery initiative), which depends directly "
                "on Supplier Omega for lithium cathode supply. The primary supply risk stems from export bans and "
                "supply chain constraints linked to Supplier Omega, creating a single-point-of-failure dependency."
            )
            mock_data["key_findings"] = [
                "Company Alpha -> DEVELOPED -> Project Titan (Confidence: 0.98)",
                "Project Titan -> DEPENDS_ON -> Supplier Omega (Confidence: 0.92)",
                "Document chunk_002 verifies risk from Supplier Omega export bans.",
            ]
            mock_data["citations"] = ["chunk_001", "chunk_002", "Company_Alpha", "Project_Titan", "Supplier_Omega"]

        elif schema_name == "EvaluationVerdict":
            mock_data["completeness_score"] = 0.95
            mock_data["has_sufficient_evidence"] = True
            mock_data["evidence_contradictions_found"] = False
            mock_data["knowledge_gaps"] = []
            mock_data["confidence_rationale"] = "All multi-hop graph relations and backing document chunks verified."

        elif schema_name == "EntityExtractionResult":
            mock_data["extracted_entities"] = ["Company Alpha", "Project Titan", "Supplier Omega"]
            mock_data["reasoning"] = "Extracted key organizations and project entities from the query."

        else:
            for field_name in fields.keys():
                if field_name == "action":
                    mock_data[field_name] = "finish"
                elif field_name == "reasoning":
                    mock_data[field_name] = "Evidence evaluation."
                elif field_name == "answer":
                    mock_data[field_name] = "Evidence synthesized successfully."
                elif field_name == "citations":
                    mock_data[field_name] = []
                elif field_name == "key_findings":
                    mock_data[field_name] = []
                elif field_name == "completeness_score":
                    mock_data[field_name] = 0.90
                elif field_name == "has_sufficient_evidence":
                    mock_data[field_name] = True
                elif field_name == "extracted_entities":
                    mock_data[field_name] = ["Company Alpha", "Project Titan"]

        instance = schema_cls.model_validate(mock_data)
        return instance, {"prompt_tokens": 120, "completion_tokens": 60}
