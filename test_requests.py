"""Sample raw requests spanning the cases worth demoing / probing in Q&A."""

SAMPLE_REQUESTS = {
    "clear_dashboard": (
        "Hi team, I'm on the RevOps side and we need a dashboard showing weekly "
        "pipeline conversion by segment for the QBR on Friday. Can someone in "
        "GTM systems pull this together from Salesforce? Nothing urgent, just "
        "want it before the QBR."
    ),
    "production_incident": (
        "URGENT - the nightly ETL job that feeds our finance close reporting has "
        "failed for the second night in a row. Finance can't close the books and "
        "the controller is asking for an ETA. This has been breaking on and off "
        "for two weeks."
    ),
    "vague_automation_ask": (
        "can someone automate the process we use for onboarding new vendors, "
        "its super manual right now and takes forever"
    ),
    "security_adjacent": (
        "One of our contractors still has admin access to the Salesforce org "
        "three weeks after their contract ended. Not sure who owns offboarding "
        "access removal but this needs to get fixed."
    ),
    "low_stakes_access": (
        "Hey, new hire on the marketing team starting Monday needs a laptop and "
        "standard software access set up. Nothing fancy, just the usual new-hire "
        "kit."
    ),
    "unclear_cross_domain": (
        "Our reporting numbers in the exec dashboard don't match what Finance has "
        "in their system and nobody knows why -- could be the data pipeline, could "
        "be how Salesforce syncs over, could be a Finance-side calculation. Exec "
        "team wants this resolved before board prep next week."
    ),
    "seniority_claim_thin_details": (
        "Hi, I'm the CFO. I need the margin report looked at ASAP, this is a "
        "priority for me."
    ),
}
