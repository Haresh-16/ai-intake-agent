from datetime import datetime, timedelta, timezone

from app.services.followup import compute_due_schedule, quiet_hours_ok


def test_followup_schedule_count_and_spacing():
    now = datetime(2026, 6, 1, 17, 0, tzinfo=timezone.utc)
    due = compute_due_schedule(now)
    assert len(due) == 3
    assert due[0] == now + timedelta(hours=24)
    assert due[1] == now + timedelta(hours=72)
    assert due[2] == now + timedelta(days=7)


def test_quiet_hours():
    allowed = datetime(2026, 6, 1, 18, 0, tzinfo=timezone.utc)
    blocked = datetime(2026, 6, 1, 4, 0, tzinfo=timezone.utc)
    assert quiet_hours_ok(allowed, -7) is True
    assert quiet_hours_ok(blocked, -7) is False
