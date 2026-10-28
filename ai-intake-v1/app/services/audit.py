from sqlalchemy.ext.asyncio import AsyncSession
from app.models import AuditLog


async def write_audit(
    session: AsyncSession,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str,
    before_state: dict | None = None,
    after_state: dict | None = None,
    ip: str | None = None,
) -> None:
    row = AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=before_state,
        after_state=after_state,
        ip=ip,
    )
    session.add(row)
