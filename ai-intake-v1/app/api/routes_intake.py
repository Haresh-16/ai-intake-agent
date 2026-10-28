from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Conversation, IntakeSummaryRecord, Message, Prospect
from app.schemas import APIMessageResponse, ConversationDetail, MessageCreate, ProspectInput
from app.services.audit import write_audit
from app.services.followup import build_follow_up_tasks
from app.services.pii import redact_sensitive_text
from app.services.prompt_loader import load_locked_prompt
from app.services.summary_generator import generate_summary

router = APIRouter(prefix="/api/intake", tags=["intake"])

STAGES = [
    "greeting_and_disclosure",
    "consent",
    "open_fact_gathering",
    "silent_classification",
    "targeted_followups",
    "evidence_request",
    "cross_practice_scan",
    "defendant_capture",
    "wrap",
]


def suggested_prompt(stage_index: int) -> str:
    """Return suggested prompt for given stage index.

    Returns empty string for wrap stage (index 8) to signal conversation completion
    and trigger auto-finalization on the frontend.
    """
    prompts = [
        "Hello, I am an AI intake assistant, not a lawyer. This chat is not legal advice and does not create an attorney-client relationship. Are you comfortable continuing?",  # 0: greeting_and_disclosure
        "Please describe what happened in your own words.",  # 1: consent
        "Who contacted you, how did they contact you, and when did this happen?",  # 2: open_fact_gathering
        "Please share any documents, screenshots, letters, call logs, or credit-report materials you already have.",  # 3: silent_classification
        "Do you have any additional details about the contact or timing?",  # 4: targeted_followups
        "Is there any evidence you can provide to support your case?",  # 5: evidence_request
        "Are there any other companies or individuals involved?",  # 6: cross_practice_scan
        "Please provide any final details about who contacted you.",  # 7: defendant_capture
        "",  # 8: wrap - no prompt, signals conversation complete
    ]

    # Return empty string if beyond prompts array
    if stage_index >= len(prompts):
        return ""

    return prompts[stage_index]


async def _get_or_create_conversation(session: AsyncSession, payload: MessageCreate) -> tuple[Prospect, Conversation]:
    if payload.conversation_id:
        conversation = await session.get(Conversation, payload.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        prospect = await session.get(Prospect, conversation.prospect_id)
        if not prospect:
            raise HTTPException(status_code=404, detail="Prospect not found")
        return prospect, conversation

    prospect = Prospect(
        first_name=payload.prospect.first_name,
        last_name=payload.prospect.last_name,
        email=payload.prospect.email,
        phone=payload.prospect.phone,
        state=payload.prospect.state,
        source_channel=payload.prospect.source_channel,
        consent_status=payload.prospect.consent_status,
        external_ids=payload.prospect.external_ids,
        status="in_intake",
    )
    session.add(prospect)
    await session.flush()

    _, prompt_hash = load_locked_prompt()
    conversation = Conversation(
        prospect_id=prospect.id,
        channel=payload.prospect.source_channel,
        status="active",
        agent_version=prompt_hash[:12],
    )
    session.add(conversation)
    await session.flush()
    return prospect, conversation


@router.post("/messages", response_model=APIMessageResponse)
async def create_message(payload: MessageCreate, request: Request, session: AsyncSession = Depends(get_session)) -> APIMessageResponse:
    prospect, conversation = await _get_or_create_conversation(session, payload)
    clean = redact_sensitive_text(payload.content)
    message = Message(
        conversation_id=conversation.id,
        role=payload.role,
        content=clean,
        tool_calls=None,
        model_metadata={"sanitized": clean != payload.content},
    )
    session.add(message)
    await write_audit(
        session,
        actor=payload.role,
        action="message.received",
        entity_type="conversation",
        entity_id=conversation.id,
        after_state={"content": clean},
        ip=request.client.host if request.client else None,
    )
    await session.commit()

    result = await session.execute(select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at.asc()))
    messages = result.scalars().all()
    prospect_turns = len([m for m in messages if m.role == "prospect"])
    stage_index = min(max(prospect_turns - 1, 0), len(STAGES) - 1)
    return APIMessageResponse(
        conversation_id=conversation.id,
        sanitized_content=clean,
        suggested_next_prompt=suggested_prompt(stage_index),
        current_stage=STAGES[stage_index],
    )


@router.post("/conversations/{conversation_id}/finalize")
async def finalize_conversation(conversation_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    conversation = await session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    prospect = await session.get(Prospect, conversation.prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    result = await session.execute(select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at.asc()))
    messages = result.scalars().all()
    transcript_text = "\n".join([f"{m.role}: {m.content}" for m in messages])
    if not transcript_text.strip():
        raise HTTPException(status_code=400, detail="Conversation has no messages")

    summary = await generate_summary(
        session=session,
        conversation_id=conversation.id,
        prospect=ProspectInput(
            first_name=prospect.first_name,
            last_name=prospect.last_name,
            email=prospect.email,
            phone=prospect.phone,
            state=prospect.state,
            source_channel=prospect.source_channel,
            consent_status=prospect.consent_status,
            external_ids=prospect.external_ids,
        ),
        transcript_text=transcript_text,
    )

    record = IntakeSummaryRecord(
        conversation_id=conversation.id,
        primary_practice_area=summary.primary_practice_area.value,
        primary_confidence=f"{summary.primary_confidence:.2f}",
        secondary_practice_areas=[item.model_dump() for item in summary.secondary_practice_areas],
        fact_pattern=summary.fact_pattern,
        defendants=[item.model_dump() for item in summary.defendants],
        evidence_collected=summary.evidence_collected,
        evidence_requested=summary.evidence_requested,
        evidence_missing=summary.evidence_missing,
        cross_practice_flag=summary.cross_practice_flag,
        follow_up_question=summary.follow_up_question,
        agent_recommendation=summary.agent_recommendation.value,
        review_status="pending",
        compliance_check=summary.compliance_check.model_dump(),
        agent_version=summary.agent_version,
        raw_summary_json=summary.model_dump(mode="json"),
    )
    session.add(record)

    if summary.evidence_missing:
        for task in build_follow_up_tasks(conversation.id, summary.evidence_missing, conversation.channel):
            session.add(task)

    conversation.status = "complete"
    await write_audit(
        session,
        actor="agent",
        action="summary.generated",
        entity_type="conversation",
        entity_id=conversation.id,
        after_state={
            "primary_practice_area": summary.primary_practice_area.value,
            "agent_version": summary.agent_version,
            "llm_request_metadata": summary.llm_request_metadata,
        },
    )
    await session.commit()
    return {"conversation_id": conversation.id, "summary": summary.model_dump(mode="json")}


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str, session: AsyncSession = Depends(get_session)) -> ConversationDetail:
    conversation = await session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await session.execute(select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at.asc()))
    messages = result.scalars().all()
    summary_result = await session.execute(select(IntakeSummaryRecord).where(IntakeSummaryRecord.conversation_id == conversation.id).order_by(IntakeSummaryRecord.created_at.desc()))
    summary = summary_result.scalars().first()

    return ConversationDetail(
        id=conversation.id,
        status=conversation.status,
        channel=conversation.channel,
        started_at=conversation.started_at,
        messages=[
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "model_metadata": m.model_metadata,
            }
            for m in messages
        ],
        summary=summary.raw_summary_json if summary else None,
    )
