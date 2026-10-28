from app.schemas import PracticeArea


CHECKLISTS = {
    PracticeArea.TCPA: [
        "Call logs showing incoming calls or texts",
        "Screenshots of caller ID or text messages",
        "Dates and approximate times of contact",
        "Any consent or revocation communication",
    ],
    PracticeArea.FCRA: [
        "Credit report showing the disputed tradeline",
        "Dispute letters or portal dispute confirmation",
        "Any bureau response letters",
        "Supporting account records or statements",
    ],
    PracticeArea.FDCPA: [
        "Collection letters or notices",
        "Call logs or voicemail records",
        "Dispute or validation request communications",
        "Any notes showing third-party debt contact",
    ],
    PracticeArea.MASS_ARB: [
        "Terms of service or arbitration clause",
        "Screenshots of account issue or platform conduct",
        "Purchase or billing records",
        "Relevant support communications",
    ],
    PracticeArea.UNKNOWN_CONSUMER: ["Any relevant document, screenshot, or communication record"],
    PracticeArea.WRONG_FIT: ["Any document that helps a human reviewer determine fit"],
}


def checklist_for(area: PracticeArea) -> list[str]:
    return CHECKLISTS.get(area, CHECKLISTS[PracticeArea.UNKNOWN_CONSUMER])
