import os
import json
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="OOS Fishbone Analyzer", layout="wide")
st.title("🐟 OOS Fishbone Analyzer (AI-assisted)")

# ---- Security: API Key must be server-side (env var) ----
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("Missing OPENAI_API_KEY environment variable on the server.")
    st.stop()

client = OpenAI(api_key=api_key)

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # example; set your org model in env

with st.sidebar:
    st.header("OOS Context")
    test_name = st.text_input("Test name", "Plaque Assay (MDCK)")
    spec = st.text_input("Specification", "e.g., 1.0–2.0×10^6 PFU/mL")
    observed = st.text_input("Observed result", "e.g., 3.8×10^5 PFU/mL")
    lot = st.text_input("Batch/Lot", "Lot-XXXX")
    sample_type = st.text_input("Sample type", "Drug substance / Drug product / Intermediate")
    analyst_level = st.selectbox("Analyst level", ["Trainee", "Qualified", "Senior"])
    instrument = st.text_input("Instrument", "Incubator / Microscope / Plate reader / Pipette")
    cal_status = st.text_input("Calibration/Maintenance status", "In date / overdue / unknown")
    changes = st.text_area("Recent changes", "e.g., new reagent lot, SOP revision, new analyst")
    notes = st.text_area("Notes", "")

def build_prompt():
    system_msg = (
        "You are a senior QC scientist in a GMP environment. "
        "You support OOS investigation using 6M Fishbone (Man, Machine, Method, Material, Measurement, Environment). "
        "You must NOT make final decisions. Provide structured, evidence-based suggestions. "
        "Output MUST be valid JSON only."
    )

    user_msg = f"""
OOS Context:
- Test name: {test_name}
- Specification: {spec}
- Observed result: {observed}
- Batch/Lot: {lot}
- Sample type: {sample_type}
- Analyst level: {analyst_level}
- Instrument: {instrument} (Calibration/Maintenance: {cal_status})
- Recent changes: {changes}
- Notes: {notes}

Task:
1) Create a 6M Fishbone list of plausible causes (3–7 items per category).
2) Prioritize causes (High/Medium/Low) with rationale.
3) List evidence gaps / checks to confirm or exclude each high-probability cause.
4) Propose draft CAPA (Corrective + Preventive) for high-probability causes.
GxP: AI is decision-support only.

Return JSON with this schema:
{{
  "fishbone": {{
    "Man": [{{"cause":"","why_it_matters":""}}],
    "Machine": [],
    "Method": [],
    "Material": [],
    "Measurement": [],
    "Environment": []
  }},
  "prioritization": [{{"cause":"","category":"","probability":"","rationale":""}}],
  "evidence_gaps": [{{"cause":"","what_to_check":"","record_or_test":""}}],
  "capa_draft": [{{"cause":"","corrective_action":"","preventive_action":"","effectiveness_check":""}}],
  "disclaimer": ""
}}
"""
    return system_msg, user_msg

run = st.button("🧠 Analyze OOS with AI")

if run:
    system_msg, user_msg = build_prompt()

    with st.spinner("Analyzing..."):
        resp = client.responses.create(
            model=MODEL,
            input=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            # Optional: limit output size
            max_output_tokens=1200,
        )

    # The SDK returns structured output; easiest is to read text:
    text = resp.output_text

    st.subheader("Raw AI Output (JSON)")
    st.code(text, language="json")

    st.subheader("Parsed Result")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        st.error("AI did not return valid JSON. Try again or tighten prompt.")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Fishbone (6M)")
        st.json(data.get("fishbone", {}))
    with col2:
        st.markdown("### Prioritization")
        st.json(data.get("prioritization", []))

    st.markdown("### Evidence gaps / Checks")
    st.json(data.get("evidence_gaps", []))

    st.markdown("### CAPA draft (QC review required)")
    st.json(data.get("capa_draft", []))

    st.info(data.get("disclaimer", "AI is decision-support only; QC must review and approve."))

    st.download_button(
        "⬇️ Download JSON",
        data=json.dumps(data, indent=2).encode("utf-8"),
        file_name="oos_fishbone_result.json",
        mime="application/json",
    )
