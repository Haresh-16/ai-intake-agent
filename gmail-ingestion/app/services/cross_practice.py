from __future__ import annotations

from app.schemas import PracticeArea, SecondaryPracticeArea


PATTERN_BANK_MULTI = {"Navient": ["TCPA", "FCRA"]}


def scan_cross_practice(primary_area: PracticeArea, text: str, defendants: list[str]) -> list[SecondaryPracticeArea]:
    lowered = text.lower()
    matches: list[SecondaryPracticeArea] = []

    if primary_area == PracticeArea.TCPA and ("debt collector" in lowered or "debt" in lowered):
        matches.append(SecondaryPracticeArea(area="FDCPA", confidence=0.8, reason="TCPA transcript also references debt-collection conduct", source="rule_based"))
    if primary_area == PracticeArea.TCPA and ("credit report" in lowered or "credit bureau" in lowered):
        matches.append(SecondaryPracticeArea(area="FCRA", confidence=0.76, reason="TCPA transcript also references credit-reporting activity", source="rule_based"))
    if primary_area == PracticeArea.FDCPA and ("credit report" in lowered or "disputed" in lowered):
        matches.append(SecondaryPracticeArea(area="FCRA", confidence=0.81, reason="Debt-collection transcript references disputed credit reporting", source="rule_based"))
    if primary_area == PracticeArea.FDCPA and ("mobile" in lowered or "cell" in lowered or "called" in lowered):
        matches.append(SecondaryPracticeArea(area="TCPA", confidence=0.73, reason="Collector contact to mobile device may support TCPA follow-up review", source="rule_based"))
    if primary_area == PracticeArea.FCRA and ("collector" in lowered or "collection" in lowered or "debt" in lowered):
        matches.append(SecondaryPracticeArea(area="FDCPA", confidence=0.79, reason="Credit-report issue also references active collection conduct", source="rule_based"))

    for defendant in defendants:
        claims = PATTERN_BANK_MULTI.get(defendant)
        if claims and len(claims) > 1:
            for claim in claims:
                if claim != primary_area.value and all(m.area != claim for m in matches):
                    matches.append(SecondaryPracticeArea(area=claim, confidence=0.72, reason=f"Pattern Bank hit indicates additional possible {claim} exposure", source="rule_based"))

    return list({m.area: m for m in matches}.values())
