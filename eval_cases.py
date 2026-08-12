"""
Labeled evaluation set.

Each case's `expected_facts` are what a careful reader would extract from the text --
`expected_priority` is NOT hand-picked, it's computed by running those facts through the
real rule_engine.compute_priority(), so the eval is checking "did extraction + classify
recover the facts/category a careful human would," not re-grading the rule engine itself
(which is deterministic code and doesn't need an LLM eval).

A few cases are marked lenient_domain / lenient_work_type where the "correct" category is
genuinely debatable even for a human -- those are scored but not counted as hard failures,
and are worth pointing at directly as taxonomy limitations.
"""

EVAL_CASES = [
    {
        "id": "sales_system_down",
        "text": "Salesforce is completely down for the whole sales team right now, and we're supposed to close Q3 deals by end of day today. Nobody can log opportunities.",
        "expected_domain": "Sales/GTM",
        "expected_work_type": "Incident/Debug",
        "expected_facts": {"system_down": True, "deadline_urgency": "within_24h", "scope": "team", "business_impact": "revenue_or_compliance", "claimed_seniority": "not_stated"},
    },
    {
        "id": "vendor_onboarding_manual",
        "text": "The vendor onboarding process is all manual right now, lots of back-and-forth emails. Would be great if someone could automate it eventually.",
        "expected_domain": "Finance/Procurement",
        "expected_work_type": "Build/Automate",
        "expected_facts": {"system_down": False, "deadline_urgency": "none_stated", "scope": "team", "business_impact": "operational_inefficiency", "claimed_seniority": "not_stated"},
    },
    {
        "id": "nda_esign_setup",
        "text": "Need to get an NDA e-signature workflow set up for a new partner meeting next week.",
        "expected_domain": "Legal/Executive/Cross-functional",
        "expected_work_type": "Access/Support",
        "expected_facts": {"system_down": False, "deadline_urgency": "within_1_week", "scope": "individual", "business_impact": "none_stated", "claimed_seniority": "not_stated"},
        "lenient_work_type": True,
    },
    {
        "id": "mau_report_request",
        "text": "Can someone pull a report on monthly active users by region for our team's planning session next week?",
        "expected_domain": "Data/Analytics",
        "expected_work_type": "Analytics/Reporting",
        "expected_facts": {"system_down": False, "deadline_urgency": "within_1_week", "scope": "team", "business_impact": "none_stated", "claimed_seniority": "not_stated"},
    },
    {
        "id": "vpn_unreliable",
        "text": "VPN keeps dropping connections for everyone company-wide over the past few days. Not fully down, but really unreliable and slowing everyone down.",
        "expected_domain": "Infra/Platform",
        "expected_work_type": "Incident/Debug",
        "expected_facts": {"system_down": True, "deadline_urgency": "none_stated", "scope": "company_wide", "business_impact": "operational_inefficiency", "claimed_seniority": "not_stated"},
    },
    {
        "id": "new_hire_laptop",
        "text": "New hire starting Monday needs a laptop and standard software access set up.",
        "expected_domain": "Employee IT/Access",
        "expected_work_type": "Access/Support",
        "expected_facts": {"system_down": False, "deadline_urgency": "within_1_week", "scope": "individual", "business_impact": "none_stated", "claimed_seniority": "not_stated"},
    },
    {
        "id": "contractor_badge_access",
        "text": "Noticed a contractor still has badge access to the building even though their contract ended last month. Might want to look into it when someone has time.",
        "expected_domain": "Security",
        "expected_work_type": "Access/Support",
        "expected_facts": {"system_down": False, "deadline_urgency": "none_stated", "scope": "individual", "business_impact": "none_stated", "claimed_seniority": "not_stated"},
    },
    {
        "id": "cross_system_mismatch",
        "text": "Our numbers don't match between two of our systems and nobody's sure why -- could be a few different teams' fault. Leadership wants it fixed before a big meeting next week.",
        "expected_domain": "Unclear/Cross-domain",
        "expected_work_type": "Incident/Debug",
        "expected_facts": {"system_down": False, "deadline_urgency": "within_1_week", "scope": "multiple_teams", "business_impact": "revenue_or_compliance", "claimed_seniority": "not_stated"},
        "lenient_domain": True,
    },
    {
        "id": "dashboard_build_request",
        "text": "We need a new pipeline conversion dashboard built in Salesforce for the sales team's quarterly review next week.",
        "expected_domain": "Sales/GTM",
        "expected_work_type": "Build/Automate",
        "expected_facts": {"system_down": False, "deadline_urgency": "within_1_week", "scope": "team", "business_impact": "none_stated", "claimed_seniority": "not_stated"},
    },
    {
        "id": "expense_system_errors",
        "text": "The expense reimbursement system is throwing errors for everyone in finance and we need it working before payroll processes tomorrow.",
        "expected_domain": "Finance/Procurement",
        "expected_work_type": "Incident/Debug",
        "expected_facts": {"system_down": True, "deadline_urgency": "within_24h", "scope": "team", "business_impact": "revenue_or_compliance", "claimed_seniority": "not_stated"},
    },
    {
        "id": "sso_integration_setup",
        "text": "Need to set up SSO integration between our new vendor tool and Okta before the team starts using it next week.",
        "expected_domain": "Infra/Platform",
        "expected_work_type": "Integration/Infra",
        "expected_facts": {"system_down": False, "deadline_urgency": "within_1_week", "scope": "team", "business_impact": "none_stated", "claimed_seniority": "not_stated"},
    },
    {
        "id": "laptop_random_restarts",
        "text": "My laptop has been randomly restarting a few times a day for the past week, making it hard to get work done. Whenever someone has a chance to look at it.",
        "expected_domain": "Employee IT/Access",
        "expected_work_type": "Incident/Debug",
        "expected_facts": {"system_down": False, "deadline_urgency": "none_stated", "scope": "individual", "business_impact": "none_stated", "claimed_seniority": "not_stated"},
    },
    {
        "id": "metrics_digest_automation",
        "text": "Would love to have an automated weekly digest of our key metrics instead of someone manually compiling them each week.",
        "expected_domain": "Data/Analytics",
        "expected_work_type": "Build/Automate",
        "expected_facts": {"system_down": False, "deadline_urgency": "none_stated", "scope": "team", "business_impact": "operational_inefficiency", "claimed_seniority": "not_stated"},
    },
    {
        "id": "dpa_compliance_deadline",
        "text": "Legal needs the data processing agreement addendum finalized and signed before a compliance deadline tomorrow -- this affects our ability to process customer data for the entire EU region.",
        "expected_domain": "Legal/Executive/Cross-functional",
        "expected_work_type": "Other/Unclear",
        "expected_facts": {"system_down": False, "deadline_urgency": "within_24h", "scope": "company_wide", "business_impact": "revenue_or_compliance", "claimed_seniority": "not_stated"},
        "lenient_work_type": True,
    },
    {
        "id": "seniority_claim_no_substance",
        "text": "Hi, I'm the CFO. I need the margin report looked at ASAP, this is a priority for me.",
        "expected_domain": "Finance/Procurement",
        "expected_work_type": "Analytics/Reporting",
        "expected_facts": {"system_down": False, "deadline_urgency": "none_stated", "scope": "individual", "business_impact": "none_stated", "claimed_seniority": "executive_or_leadership"},
        "lenient_domain": True,
        "lenient_work_type": True,
    },
    {
        "id": "status_page_customer_facing",
        "text": "Our customer-facing status page is down and customers are actively posting about it on social media. This needs fixing immediately.",
        "expected_domain": "Infra/Platform",
        "expected_work_type": "Incident/Debug",
        "expected_facts": {"system_down": True, "deadline_urgency": "within_24h", "scope": "external_customer", "business_impact": "customer_facing", "claimed_seniority": "not_stated"},
    },
]
