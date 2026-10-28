from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_session
from app.models import Conversation, IntakeSummaryRecord, Message
from app.schemas import ReviewAction
from app.services.audit import write_audit

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/queue")
async def review_queue(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        select(IntakeSummaryRecord).where(IntakeSummaryRecord.review_status == "pending").order_by(IntakeSummaryRecord.created_at.asc())
    )
    rows = result.scalars().all()
    return [
        {
            "summary_id": row.id,
            "conversation_id": row.conversation_id,
            "practice_area": row.primary_practice_area,
            "recommendation": row.agent_recommendation,
            "cross_practice_flag": row.cross_practice_flag,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.get("/summaries/{summary_id}")
async def get_summary(summary_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    summary = await session.get(IntakeSummaryRecord, summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    result = await session.execute(select(Message).where(Message.conversation_id == summary.conversation_id).order_by(Message.created_at.asc()))
    messages = result.scalars().all()
    return {
        "summary": summary.raw_summary_json,
        "review_status": summary.review_status,
        "transcript": [{"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in messages],
    }


@router.post("/summaries/{summary_id}/decision")
async def review_decision(summary_id: str, payload: ReviewAction, session: AsyncSession = Depends(get_session)) -> dict:
    summary = await session.get(IntakeSummaryRecord, summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    before = dict(summary.raw_summary_json)
    summary.review_status = payload.decision.value
    summary.reviewer_id = payload.reviewer_id
    summary.reviewed_at = datetime.utcnow()
    if payload.updated_summary:
        summary.raw_summary_json = payload.updated_summary
    if payload.decision.value == "approved":
        summary.final_disposition = "approved_for_next_step"
    elif payload.decision.value == "rejected":
        summary.final_disposition = "rejected_to_engineering_or_human_followup"
    else:
        summary.final_disposition = "modified_for_review"

    conversation = await session.get(Conversation, summary.conversation_id)
    conversation.status = "in_review"

    await write_audit(
        session,
        actor=f"reviewer:{payload.reviewer_id}",
        action=f"review.{payload.decision.value}",
        entity_type="intake_summary",
        entity_id=summary.id,
        before_state=before,
        after_state=summary.raw_summary_json,
    )
    await session.commit()
    return {"status": "ok", "summary_id": summary.id, "review_status": summary.review_status}
