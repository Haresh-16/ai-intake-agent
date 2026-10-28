from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.db import get_session
from app.models import FollowUpTask, Message
from app.schemas import FollowUpTaskView
from app.services.audit import write_audit
from app.services.followup import should_send_follow_up
router = APIRouter(prefix="/api/followups", tags=["followups"])


@router.get("/due", response_model=list[FollowUpTaskView])
async def due_followups(session: AsyncSession = Depends(get_session)) -> list[FollowUpTaskView]:
    now = datetime.utcnow()
    result = await session.execute(
        select(FollowUpTask).where(FollowUpTask.status == "scheduled", FollowUpTask.due_at <= now).order_by(FollowUpTask.due_at.asc())
    )
    return list(result.scalars().all())


@router.post("/run")
async def run_followups(session: AsyncSession = Depends(get_session)) -> dict:
    now = datetime.utcnow()
    result = await session.execute(
        select(FollowUpTask).where(FollowUpTask.status == "scheduled", FollowUpTask.due_at <= now).order_by(FollowUpTask.due_at.asc())
    )
    tasks = result.scalars().all()
    sent = 0
    blocked = 0

    for task in tasks:
        last_message_result = await session.execute(
            select(Message).where(Message.conversation_id == task.conversation_id).order_by(Message.created_at.desc())
        )
        latest = last_message_result.scalars().first()
        allowed, reason = should_send_follow_up(now, settings.outbound_kill_switch, latest.content if latest else None)
        if not allowed:
            task.status = "blocked"
            task.stop_reason = reason
            blocked += 1
            await write_audit(
                session,
                actor="system",
                action="followup.blocked",
                entity_type="follow_up_task",
                entity_id=task.id,
                after_state={"reason": reason},
            )
            continue

        task.status = "sent"
        task.sent_at = now
        sent += 1
        await write_audit(
            session,
            actor="system",
            action="followup.sent",
            entity_type="follow_up_task",
            entity_id=task.id,
            after_state={"payload": task.payload, "template_id": task.template_id},
        )

    await session.commit()
    return {"sent": sent, "blocked": blocked}
