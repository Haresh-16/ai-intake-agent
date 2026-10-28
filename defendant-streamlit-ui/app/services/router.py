from app.schemas import IntakeSummary


def route_summary(summary: IntakeSummary) -> list[str]:
    queues = ["tier1_intake"]
    if summary.agent_recommendation == "route_to_attorney":
        queues.append("tier2_supervising_attorney")
    if summary.cross_practice_flag or any(d.pattern_bank_hit for d in summary.defendants):
        queues.append("tier3_partner")
    return queues
