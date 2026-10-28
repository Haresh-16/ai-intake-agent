from __future__ import annotations

from app.schemas import PracticeArea, SecondaryPracticeArea


PATTERN_BANK_MULTI = {"Navient": ["TCPA", "FCRA"]}


def scan_cross_practice_deterministic(primary_area: PracticeArea, text: str, defendants: list[str]) -> list[SecondaryPracticeArea]:
    """Deterministic keyword-based cross-practice detection (compliance-critical)."""
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


def merge_secondary_areas(
    llm_suggestions: list[SecondaryPracticeArea],
    rule_based: list[SecondaryPracticeArea],
    primary_area: PracticeArea,
    min_llm_confidence: float = 0.7
) -> list[SecondaryPracticeArea]:
    """
    Merge LLM-inferred and rule-based secondary areas.

    Strategy:
    - Union of both sources
    - Deduplicate by area name
    - Prefer rule-based when both suggest same area (for auditability)
    - Filter out primary area if LLM accidentally included it
    - Filter LLM suggestions by minimum confidence threshold
    - Return sorted by confidence (highest first)

    Args:
        llm_suggestions: Secondary areas suggested by LLM
        rule_based: Secondary areas from deterministic rules
        primary_area: The primary practice area (to filter out from secondary)
        min_llm_confidence: Minimum confidence for LLM suggestions (default 0.7)

    Returns:
        Merged list of secondary practice areas
    """
    merged: dict[str, SecondaryPracticeArea] = {}

    # Add rule-based first (higher priority for auditability)
    for item in rule_based:
        merged[item.area] = item

    # Add LLM suggestions (only if not already present and meet confidence threshold)
    for item in llm_suggestions:
        # Skip if this is the primary area
        if item.area == primary_area.value:
            continue

        # Skip if confidence too low
        if item.confidence < min_llm_confidence:
            continue

        # Only add if not already present (rule-based takes precedence)
        if item.area not in merged:
            merged[item.area] = SecondaryPracticeArea(
                area=item.area,
                confidence=item.confidence,
                reason=item.reason,
                source="llm_inferred"
            )

    # Return sorted by confidence (highest first)
    return sorted(merged.values(), key=lambda x: x.confidence, reverse=True)
