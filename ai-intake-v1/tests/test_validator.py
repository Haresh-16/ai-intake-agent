from app.schemas import AgentRecommendation, ComplianceCheck, IntakeSummary, PracticeArea, ProspectInput


def test_valid_summary_schema():
    summary = IntakeSummary(
        conversation_id="123",
        prospect=ProspectInput(first_name="Ada", state="CA"),
        primary_practice_area=PracticeArea.TCPA,
        primary_confidence=0.88,
        secondary_practice_areas=[],
        fact_pattern="The prospect reports repeated calls to a mobile phone from an unknown caller. The caller discussed a debt and continued contact after the prospect objected. A human reviewer should confirm timing, consent, and evidence.",
        defendants=[],
        evidence_collected=[],
        evidence_requested=["Call logs showing incoming calls or texts"],
        evidence_missing=["Call logs showing incoming calls or texts"],
        cross_practice_flag=False,
        follow_up_question="Which missing evidence item is most likely to confirm the TCPA intake?",
        agent_recommendation=AgentRecommendation.REQUEST_MORE_EVIDENCE,
        compliance_check=ComplianceCheck(no_legal_advice_given=True, no_outcome_promised=True, no_acr_implied=True, disclosure_logged=True),
        agent_version="hash+model",
        llm_request_metadata={},
    )
    assert summary.primary_practice_area == PracticeArea.TCPA
