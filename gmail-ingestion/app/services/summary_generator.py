from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import ComplianceCheck, Defendant, DefendantRole, IntakeSummary, ProspectInput, SecondaryPracticeArea
from app.services.cross_practice import scan_cross_practice
from app.services.llm_agent_core import classify_with_llm, evidence_with_llm, summarize_with_llm
from app.services.prompt_loader import load_locked_prompt

PATTERN_BANK = {
    "portfolio recovery": ["FDCPA"],
    "transunion": ["FCRA"],
    "equifax": ["FCRA"],
    "experian": ["FCRA"],
    "navient": ["TCPA", "FCRA"],
}


def extract_defendants(text: str) -> list[Defendant]:
    lowered = text.lower()
    found: list[Defendant] = []
    for name, claims in PATTERN_BANK.items():
        if name in lowered:
            role = DefendantRole.FURNISHER if "FCRA" in claims else DefendantRole.COLLECTOR
            found.append(Defendant(name=name.title(), role=role, pattern_bank_hit=True))
    return found


def infer_collected_evidence(requested: list[str], transcript_text: str) -> list[str]:
    lowered = transcript_text.lower()
    collected: list[str] = []
    for item in requested:
        li = item.lower()
        if "call log" in li and "call log" in lowered:
            collected.append(item)
        elif "credit report" in li and "credit report" in lowered:
            collected.append(item)
        elif "letter" in li and ("letter" in lowered or "notice" in lowered):
            collected.append(item)
        elif "screenshot" in li and "screenshot" in lowered:
            collected.append(item)
        elif "dispute" in li and "dispute" in lowered:
            collected.append(item)
    return collected


async def generate_summary(session: AsyncSession, conversation_id: str, prospect: ProspectInput, transcript_text: str) -> IntakeSummary:
    _, prompt_hash = load_locked_prompt()
    cls_result, cls_meta = await classify_with_llm(session, conversation_id, transcript_text)
    defendants = extract_defendants(transcript_text)
    secondary = [
        SecondaryPracticeArea(area=item.area, confidence=item.confidence, reason=item.reason, source=getattr(item, "source", "rule_based"))
        for item in scan_cross_practice(cls_result.primary_practice_area, transcript_text, [d.name for d in defendants])
    ]
    ev_result, ev_meta = await evidence_with_llm(session, conversation_id, transcript_text, cls_result.primary_practice_area)
    collected = infer_collected_evidence(ev_result.evidence_requested, transcript_text)
    missing = [item for item in ev_result.evidence_requested if item not in collected]
    sum_result, sum_meta = await summarize_with_llm(
        session,
        conversation_id,
        transcript_text,
        cls_result.primary_practice_area,
        cls_result.primary_confidence,
        ev_result.evidence_requested,
        missing,
    )
    return IntakeSummary(
        conversation_id=conversation_id,
        prospect=prospect,
        primary_practice_area=sum_result.primary_practice_area,
        primary_confidence=round(sum_result.primary_confidence, 2),
        secondary_practice_areas=secondary,
        fact_pattern=sum_result.fact_pattern,
        defendants=defendants,
        evidence_collected=collected,
        evidence_requested=ev_result.evidence_requested,
        evidence_missing=missing,
        cross_practice_flag=len(secondary) > 0,
        follow_up_question=sum_result.follow_up_question,
        agent_recommendation=sum_result.agent_recommendation,
        compliance_check=ComplianceCheck(no_legal_advice_given=True, no_outcome_promised=True, no_acr_implied=True, disclosure_logged=True),
        agent_version=f"{prompt_hash[:12]}+{sum_meta.model_id}",
        llm_request_metadata={
            "classification": cls_meta.model_dump(),
            "evidence_request": ev_meta.model_dump(),
            "summary_generation": sum_meta.model_dump(),
        },
    )
