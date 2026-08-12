"""
Routing table: maps a request's business domain to the internal team that owns it.

Grounded in Snowflake's public Enterprise Technology job postings (careers.snowflake.com),
not confirmed internal org data -- treated as a working assumption, editable without
touching agent reasoning logic (see design doc: "what breaks at scale").
"""

DOMAINS = [
    "Sales/GTM",
    "Finance/Procurement",
    "Legal/Executive/Cross-functional",
    "Data/Analytics",
    "Infra/Platform",
    "Employee IT/Access",
    "Security",
    "Unclear/Cross-domain",
]

WORK_TYPES = [
    "Build/Automate",
    "Analytics/Reporting",
    "Incident/Debug",
    "Access/Support",
    "Integration/Infra",
    "Other/Unclear",
]

PRIORITIES = ["P0-Critical", "P1-High", "P2-Medium", "P3-Low"]

DOMAIN_TO_TEAM = {
    "Sales/GTM": "GTM Applications Engineering",
    "Finance/Procurement": "Finance Systems (Core Finance / Procure-to-Pay)",
    "Legal/Executive/Cross-functional": "Enterprise Applications",
    "Data/Analytics": "Data Engineering",
    "Infra/Platform": "Cloud Infrastructure & DevOps",
    "Employee IT/Access": "Client Platform & Support Engineering",
    "Security": "Security",
    "Unclear/Cross-domain": "Enterprise Technology Intake Lead (cross-domain escalation)",
}

# Domains where the agent still completes classification/priority/routing/response on
# its own, but flags the result for downstream review before anyone acts on it --
# there's no human in the intake loop itself, this is a governance signal attached to
# the agent's own completed output, not a pause in the agent's reasoning.
ALWAYS_ESCALATE_DOMAINS = {"Security", "Unclear/Cross-domain"}

# Priorities that always get flagged for downstream review even when the domain/team
# routing is confident, because the cost of a wrong autonomous action is high.
ALWAYS_ESCALATE_PRIORITIES = {"P0-Critical"}


def routing_table_as_prompt_context() -> str:
    lines = ["Domain -> Owning team:"]
    for domain, team in DOMAIN_TO_TEAM.items():
        lines.append(f"- {domain} -> {team}")
    return "\n".join(lines)
