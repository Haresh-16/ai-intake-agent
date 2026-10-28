from __future__ import annotations

import json
from uuid import uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import LLMCallRecord
from app.schemas import AgentRecommendation, LLMClassificationResult, LLMEvidenceResult, LLMRequestMetadata, LLMStructuredSummary, PracticeArea
from app.services.evidence import checklist_for
from app.services.prompt_loader import get_prompt_hash, load_locked_prompt, load_prompts


class BaseLLMClient:
    async def classify(self, transcript_text: str):
        raise NotImplementedError

    async def evidence(self, transcript_text: str, primary_area: PracticeArea):
        raise NotImplementedError

    async def summarize(self, transcript_text: str, primary_area: PracticeArea, confidence: float, evidence_requested: list[str], evidence_missing: list[str]):
        raise NotImplementedError


class StubLLMClient(BaseLLMClient):
    def _classify(self, text: str):
        lowered = text.lower()
        scores = {
            PracticeArea.TCPA: sum(1 for w in ["call", "called", "robocall", "autodial", "text message", "mobile"] if w in lowered),
            PracticeArea.FCRA: sum(1 for w in ["credit report", "credit bureau", "transunion", "equifax", "experian", "furnisher"] if w in lowered),
            PracticeArea.FDCPA: sum(1 for w in ["debt collector", "collector", "collection", "debt", "third party calling"] if w in lowered),
            PracticeArea.MASS_ARB: sum(1 for w in ["arbitration", "mass arbitration", "terms of service", "consumer claims"] if w in lowered),
        }
        best = max(scores, key=scores.get)
        score = scores[best]
        if score <= 0:
            return PracticeArea.UNKNOWN_CONSUMER, 0.35, "No strong practice-area signal detected in transcript text."
        if score == 1:
            return best, 0.61, f"Single keyword cluster matched for {best.value}."
        return best, min(0.95, 0.65 + score * 0.08), f"Multiple keyword clusters matched for {best.value}."

    def _fact(self, text: str):
        compact = " ".join(text.split())
        compact = compact[:500] if len(compact) > 500 else compact
        return compact if "." in compact else compact + " A human reviewer should confirm the remaining details."

    async def classify(self, transcript_text: str):
        area, conf, reasoning = self._classify(transcript_text)
        raw = json.dumps({"primary_practice_area": area.value, "primary_confidence": conf, "reasoning": reasoning})
        return LLMClassificationResult(primary_practice_area=area, primary_confidence=conf, reasoning=reasoning), {"stubbed": True, "temperature": 0.0, "raw_response_preview": raw[:500]}, raw

    async def evidence(self, transcript_text: str, primary_area: PracticeArea):
        requested = checklist_for(primary_area)
        question = f"Which of these items can the prospect share next to verify the {primary_area.value} issue: {requested[0]}?" if requested else "What additional document or screenshot would most help the reviewer verify the claim?"
        raw = json.dumps({"evidence_requested": requested, "follow_up_question": question})
        return LLMEvidenceResult(evidence_requested=requested or ["Any relevant document, screenshot, or communication record"], follow_up_question=question), {"stubbed": True, "temperature": 0.0, "raw_response_preview": raw[:500]}, raw

    async def summarize(self, transcript_text: str, primary_area: PracticeArea, confidence: float, evidence_requested: list[str], evidence_missing: list[str]):
        if primary_area == PracticeArea.WRONG_FIT:
            rec = AgentRecommendation.WRONG_FIT_CLOSE
        elif evidence_missing:
            rec = AgentRecommendation.REQUEST_MORE_EVIDENCE
        elif confidence >= 0.8:
            rec = AgentRecommendation.ROUTE_TO_ATTORNEY
        else:
            rec = AgentRecommendation.ROUTE_TO_INTAKE_REVIEW
        fact = self._fact(transcript_text)
        question = f"Which missing evidence item is most likely to confirm the {primary_area.value} intake?" if evidence_missing else "What is the single highest-value follow-up question a reviewer should ask next?"
        raw = json.dumps({"primary_practice_area": primary_area.value, "primary_confidence": confidence, "fact_pattern": fact, "follow_up_question": question, "agent_recommendation": rec.value})
        return LLMStructuredSummary(primary_practice_area=primary_area, primary_confidence=confidence, fact_pattern=fact, follow_up_question=question, agent_recommendation=rec), {"stubbed": True, "temperature": 0.0, "raw_response_preview": raw[:500]}, raw


class OllamaClient(BaseLLMClient):
    """
    LLM client for Ollama (local LLM server).

    Uses Ollama's chat API with JSON format enforcement.
    Configured via environment variables:
    - LLM_BASE_URL: Ollama endpoint (default: http://localhost:11434)
    - LLM_MODEL_ID: Model identifier (e.g., llama3.1:8b)
    No API key required.
    """
    async def _call_json(self, system_prompt: str, user_prompt: str) -> tuple[dict, dict, str]:
        if not settings.llm_base_url:
            raise RuntimeError("LLM_BASE_URL is required for ollama mode")

        # Ollama uses /api/chat endpoint
        payload = {
            "model": settings.llm_model_id,
            "messages": [
                {"role": "system", "content": system_prompt + "\n\nYou must respond with valid JSON only. Do not include any text outside the JSON object."},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": "json",  # Ollama's JSON mode
            "options": {
                "temperature": 0.0,
            }
        }

        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            resp = await client.post(
                f"{settings.llm_base_url.rstrip('/')}/api/chat",
                json=payload,
            )
            if resp.status_code != 200:
                error_body = resp.text
                print(f"Ollama API Error ({resp.status_code}): {error_body}")
            resp.raise_for_status()
            data = resp.json()

        # Ollama response format: {"message": {"role": "assistant", "content": "..."}}
        text = data["message"]["content"]
        parsed = json.loads(text)

        meta = {
            "stubbed": False,
            "temperature": 0.0,
            "prompt_tokens_estimate": data.get("prompt_eval_count"),
            "completion_tokens_estimate": data.get("eval_count"),
            "raw_response_preview": text[:500],
        }
        return parsed, meta, text

    async def classify(self, transcript_text: str):
        prompts = load_prompts()
        system_prompt = prompts["classification"]["system"]
        user_template = prompts["classification"]["user_template"]
        user_prompt = user_template.replace("{transcript_text}", transcript_text)

        parsed, meta, raw = await self._call_json(system_prompt, user_prompt)
        return LLMClassificationResult.model_validate(parsed), meta, raw

    async def evidence(self, transcript_text: str, primary_area: PracticeArea):
        prompts = load_prompts()
        system_prompt = prompts["evidence"]["system"]
        user_template = prompts["evidence"]["user_template"]
        user_prompt = user_template.replace("{primary_area}", primary_area.value).replace("{transcript_text}", transcript_text)

        parsed, meta, raw = await self._call_json(system_prompt, user_prompt)
        return LLMEvidenceResult.model_validate(parsed), meta, raw

    async def summarize(self, transcript_text: str, primary_area: PracticeArea, confidence: float, evidence_requested: list[str], evidence_missing: list[str]):
        prompts = load_prompts()
        system_prompt = prompts["summary"]["system"]
        user_template = prompts["summary"]["user_template"]

        context = {
            "transcript": transcript_text,
            "primary_area": primary_area.value,
            "confidence": confidence,
            "evidence_requested": evidence_requested,
            "evidence_missing": evidence_missing,
        }

        user_prompt = user_template.replace("{context_json}", json.dumps(context, indent=2))

        parsed, meta, raw = await self._call_json(system_prompt, user_prompt)
        return LLMStructuredSummary.model_validate(parsed), meta, raw


class OpenAICompatibleClient(BaseLLMClient):
    """
    LLM client for OpenAI-compatible APIs (Groq, OpenAI, etc.).

    Uses the OpenAI chat completions format with JSON mode.
    Configured via environment variables:
    - LLM_BASE_URL: API endpoint (default: Groq)
    - LLM_MODEL_ID: Model identifier
    - LLM_API_KEY: API authentication key
    """
    async def _call_json(self, system_prompt: str, user_prompt: str) -> tuple[dict, dict, str]:
        if not settings.llm_api_key or not settings.llm_base_url:
            raise RuntimeError("LLM_API_KEY and LLM_BASE_URL are required for openai_compatible mode")
        payload = {
            "model": settings.llm_model_id,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            resp = await client.post(
                f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json=payload,
            )
            if resp.status_code != 200:
                error_body = resp.text
                print(f"LLM API Error ({resp.status_code}): {error_body}")
            resp.raise_for_status()
            data = resp.json()
        text = data["choices"][0]["message"]["content"]
        parsed = json.loads(text)
        meta = {
            "stubbed": False,
            "temperature": 0.0,
            "prompt_tokens_estimate": data.get("usage", {}).get("prompt_tokens"),
            "completion_tokens_estimate": data.get("usage", {}).get("completion_tokens"),
            "raw_response_preview": text[:500],
        }
        return parsed, meta, text

    async def classify(self, transcript_text: str):
        prompts = load_prompts()
        system_prompt = prompts["classification"]["system"]
        user_template = prompts["classification"]["user_template"]
        user_prompt = user_template.replace("{transcript_text}", transcript_text)

        parsed, meta, raw = await self._call_json(system_prompt, user_prompt)
        return LLMClassificationResult.model_validate(parsed), meta, raw

    async def evidence(self, transcript_text: str, primary_area: PracticeArea):
        prompts = load_prompts()
        system_prompt = prompts["evidence"]["system"]
        user_template = prompts["evidence"]["user_template"]
        user_prompt = user_template.replace("{primary_area}", primary_area.value).replace("{transcript_text}", transcript_text)

        parsed, meta, raw = await self._call_json(system_prompt, user_prompt)
        return LLMEvidenceResult.model_validate(parsed), meta, raw

    async def summarize(self, transcript_text: str, primary_area: PracticeArea, confidence: float, evidence_requested: list[str], evidence_missing: list[str]):
        prompts = load_prompts()
        system_prompt = prompts["summary"]["system"]
        user_template = prompts["summary"]["user_template"]

        context = {
            "transcript": transcript_text,
            "primary_area": primary_area.value,
            "confidence": confidence,
            "evidence_requested": evidence_requested,
            "evidence_missing": evidence_missing,
        }

        user_prompt = user_template.replace("{context_json}", json.dumps(context, indent=2))

        parsed, meta, raw = await self._call_json(system_prompt, user_prompt)
        return LLMStructuredSummary.model_validate(parsed), meta, raw


def get_llm_client() -> BaseLLMClient:
    """
    Returns the appropriate LLM client based on configuration.

    Supported providers:
    - "ollama": Local Ollama server (no API key needed)
    - "openai_compatible": OpenAI-compatible APIs (Groq, OpenAI, etc.)
    - Falls back to StubLLMClient if llm_stub_mode=True or invalid config

    This ensures the app runs locally without credentials while allowing
    real LLM integration when properly configured.
    """
    if settings.llm_stub_mode:
        return StubLLMClient()

    if settings.llm_provider == "ollama":
        return OllamaClient()

    if settings.llm_provider == "openai_compatible" and settings.llm_api_key:
        return OpenAICompatibleClient()

    # Fallback to stub if provider is invalid or missing config
    return StubLLMClient()


def _prompt_info() -> tuple[str, str, str]:
    # Load prompt hash from file (cached)
    prompt_hash = get_prompt_hash()
    # Note: prompt_text is now loaded via load_prompts() in individual methods
    return "", "system_prompt_v1", prompt_hash


async def _record_call(session: AsyncSession, *, conversation_id: str | None, operation: str, prompt_version: str, prompt_hash: str, metadata: dict, raw_response_text: str) -> LLMRequestMetadata:
    request_id = str(uuid4())
    row = LLMCallRecord(
        conversation_id=conversation_id,
        provider=settings.llm_provider,
        model_id=settings.llm_model_id,
        operation=operation,
        prompt_version=prompt_version,
        prompt_hash=prompt_hash,
        request_metadata={
            "request_id": request_id,
            "stubbed": bool(metadata.get("stubbed", False)),
            "temperature": float(metadata.get("temperature", 0.0)),
        },
        response_metadata={
            "prompt_tokens_estimate": metadata.get("prompt_tokens_estimate"),
            "completion_tokens_estimate": metadata.get("completion_tokens_estimate"),
            "raw_response_preview": metadata.get("raw_response_preview"),
        },
        raw_response_text=raw_response_text,
    )
    session.add(row)
    await session.flush()
    return LLMRequestMetadata(
        provider=settings.llm_provider,
        model_id=settings.llm_model_id,
        operation=operation,
        prompt_version=prompt_version,
        prompt_hash=prompt_hash,
        request_id=request_id,
        stubbed=bool(metadata.get("stubbed", False)),
        temperature=float(metadata.get("temperature", 0.0)),
        prompt_tokens_estimate=metadata.get("prompt_tokens_estimate"),
        completion_tokens_estimate=metadata.get("completion_tokens_estimate"),
        raw_response_preview=metadata.get("raw_response_preview"),
    )


async def classify_with_llm(session: AsyncSession, conversation_id: str | None, transcript_text: str):
    _prompt_text, prompt_version, prompt_hash = _prompt_info()
    result, metadata, raw = await get_llm_client().classify(transcript_text)
    record = await _record_call(session, conversation_id=conversation_id, operation="classification", prompt_version=prompt_version, prompt_hash=prompt_hash, metadata=metadata, raw_response_text=raw)
    return result, record


async def evidence_with_llm(session: AsyncSession, conversation_id: str | None, transcript_text: str, primary_area: PracticeArea):
    _prompt_text, prompt_version, prompt_hash = _prompt_info()
    result, metadata, raw = await get_llm_client().evidence(transcript_text, primary_area)
    record = await _record_call(session, conversation_id=conversation_id, operation="evidence_request", prompt_version=prompt_version, prompt_hash=prompt_hash, metadata=metadata, raw_response_text=raw)
    return result, record


async def summarize_with_llm(session: AsyncSession, conversation_id: str | None, transcript_text: str, primary_area: PracticeArea, confidence: float, evidence_requested: list[str], evidence_missing: list[str]):
    _prompt_text, prompt_version, prompt_hash = _prompt_info()
    result, metadata, raw = await get_llm_client().summarize(transcript_text, primary_area, confidence, evidence_requested, evidence_missing)
    record = await _record_call(session, conversation_id=conversation_id, operation="summary_generation", prompt_version=prompt_version, prompt_hash=prompt_hash, metadata=metadata, raw_response_text=raw)
    return result, record
