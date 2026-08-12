from pathlib import Path

import streamlit as st

from agent import run_intake
from test_requests import SAMPLE_REQUESTS

st.set_page_config(page_title="Enterprise Intake Agent", page_icon="\U0001F4E5", layout="wide")

PRIORITY_COLOR = {
    "P0-Critical": "🔴",
    "P1-High": "🟠",
    "P2-Medium": "🟡",
    "P3-Low": "🟢",
}

DOCS_DIR = Path(__file__).parent


def render_markdown_file(filename: str) -> None:
    path = DOCS_DIR / filename
    if path.exists():
        st.markdown(path.read_text())
    else:
        st.info(f"{filename} not found.")


st.title("Enterprise Intake Agent")
st.caption(
    "Raw request in -> classification, priority, routing, and a draft first response out. "
    "No human in the intake loop -- five sequential decision stages (four LLM reasoning, "
    "one deterministic policy), each consuming the previous stage's output."
)

with st.sidebar:
    st.header("Try it")
    sample_choice = st.selectbox(
        "Load a sample request",
        ["(write your own)"] + list(SAMPLE_REQUESTS.keys()),
    )
    default_text = "" if sample_choice == "(write your own)" else SAMPLE_REQUESTS[sample_choice]
    st.markdown("---")
    st.caption(
        "Architecture:\n\n"
        "1. **Extract** (LLM) — pull structured facts from raw text\n"
        "2. **Classify** (LLM) — domain + work type only\n"
        "3. **Priority** (rule engine, no LLM) — deterministic, auditable\n"
        "4. **Route** (LLM + policy) — team + downstream-review flag\n"
        "5. **Respond** (LLM) — draft reply, or a clarification ask if confidence is low"
    )

demo_tab, design_tab, reliability_tab, ai_usage_tab = st.tabs(
    ["Live Demo", "Design Doc", "Reliability Findings", "AI Usage Notes"]
)

with demo_tab:
    raw_request = st.text_area(
        "Raw incoming request",
        value=default_text,
        height=120,
        placeholder="e.g. \"Hey, the nightly ETL job feeding finance close reporting failed again, controller wants an ETA...\"",
    )

    run_clicked = st.button("Run intake agent", type="primary", disabled=not raw_request.strip())

    if run_clicked:
        with st.spinner("Running 5-step reasoning pipeline..."):
            try:
                result = run_intake(raw_request.strip())
            except Exception as e:
                st.error(f"Run failed: {e}")
                st.stop()

        c, p, r = result.classification, result.priority, result.routing

        st.subheader("Result")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Domain", c.get("domain", "-"))
        col2.metric("Work type", c.get("work_type", "-"))
        col3.metric("Priority", f"{PRIORITY_COLOR.get(p.get('priority'), '')} {p.get('priority', '-')}")
        col4.metric("Routed to", r.get("recommended_team", "-"))

        if r.get("requires_downstream_review"):
            urgency = r.get("review_urgency", "standard")
            urgency_tag = "🔺 EXPEDITED" if urgency == "expedited" else "standard queue"
            st.warning(f"**Flagged for downstream review** [{urgency_tag}]: {r.get('escalation_reason', '')}")
        else:
            st.success("Completed autonomously — no downstream review flagged.")

        st.markdown("### Draft first response")
        st.info(result.response.get("draft_response", ""))

        with st.expander("▾ View agent trace — every stage is auditable, not just plausible"):
            rtab1, rtab2, rtab3, rtab4 = st.tabs(["1. Extract", "2. Classify", "3. Priority (rule engine)", "4. Route"])
            with rtab1:
                st.json(result.extraction)
            with rtab2:
                st.json(result.classification)
            with rtab3:
                st.markdown(f"**Rule triggered:** `{p.get('rule_triggered')}`")
                st.markdown(p.get("priority_reasoning", ""))
                st.caption("No LLM call in this step -- pure deterministic logic over stage-1 facts. See rule_engine.py.")
            with rtab4:
                st.json(result.routing)

            st.markdown("**Full raw output (JSON)**")
            st.json(result.to_dict())

with design_tab:
    render_markdown_file("design_doc.md")

with reliability_tab:
    render_markdown_file("reliability_findings.md")

with ai_usage_tab:
    render_markdown_file("ai_usage_notes.md")
