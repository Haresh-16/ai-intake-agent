from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import FollowUpTask


def compute_due_schedule(base_time: datetime) -> list[datetime]:
    return [
        base_time + timedelta(hours=24),
        base_time + timedelta(hours=72),
        base_time + timedelta(days=7),
    ]


def quiet_hours_ok(now_utc: datetime, prospect_utc_offset_hours: int = 0) -> bool:
    local = now_utc + timedelta(hours=prospect_utc_offset_hours)
    return 8 <= local.hour < 21


def build_follow_up_tasks(conversation_id: str, evidence_items: list[str], channel: str = "sms") -> list[FollowUpTask]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    tasks: list[FollowUpTask] = []
    for idx, due in enumerate(compute_due_schedule(now), start=1):
        tasks.append(
            FollowUpTask(
                conversation_id=conversation_id,
                template_id="evidence_followup_v1",
                template_version="v1",
                attempt_number=idx,
                due_at=due,
                channel=channel,
                payload={"evidence_items": evidence_items},
                status="scheduled",
            )
        )
    return tasks


def should_send_follow_up(now: datetime, kill_switch: bool, last_message_content: str | None) -> tuple[bool, str | None]:
    """
    Determine if a follow-up should be sent based on compliance policies.

    Returns:
        (allowed, reason) - allowed is True if send is permitted, reason explains why not
    """
    # Kill switch check
    if kill_switch:
        return False, "kill_switch_enabled"

    # Opt-out detection
    if last_message_content:
        opt_out_keywords = ["stop", "unsubscribe", "opt out", "opt-out", "cancel"]
        content_lower = last_message_content.lower()
        if any(keyword in content_lower for keyword in opt_out_keywords):
            return False, "opt_out_detected"

    # Quiet hours check (simplified - checks UTC hours 8-21)
    if not quiet_hours_ok(now):
        return False, "quiet_hours"

    return True, None
