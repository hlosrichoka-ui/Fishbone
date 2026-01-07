# =========================================================
# OOS Fishbone Analyzer (AI-assisted)
# Author: QC Lab
# Purpose: Decision-support tool for OOS investigation (6M Fishbone)
# GxP: Final decisions must be made by qualified QC personnel
# =========================================================

import os
import json
import streamlit as st
from openai import OpenAI

# -----------------------
# Page configuration
# -----------------------
st.set_page_config(
    page_title="OOS Fishbone Analyzer",
    page_icon="🐟",
    layout="wide"
)

st.title("🐟 OOS Fishbone Analyzer (AI-assisted)")
st.caption(
    "AI is used as a decision-support tool only. "
    "Final conclusions and CAPA approval must be performed by QC personnel."
)

# -----------------------
# Security: API Key
# -----------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error(
        "OPENAI_API_KEY not found. "
        "Please set it as an environment variable or Streamlit Secret."
    )
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# Choose model via env (recommended for controlled environments)
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# -----------------------
# Sidebar: OOS Context
# -----------------------
with st.sidebar:
    st.header("📋 OOS Context")

    test_name = st.text_input(
        "Test name",
        value="Plaque Assay (MDCK)"
    )

    specification = st.text_input(
        "Specification",
        value="1.0–2.0 × 10^6 PFU/mL"
    )

    observed_result = st.text_input(
        "Observed result",
        value="3.8 × 10^5 PFU/mL"
    )

    batch_lot = st.text_input(
        "Batch / Lot No.",
        value="Lot-XXXX"
    )

    sample_type = st.selectbox(
        "Sample type",
        [
            "Drug Substance",
            "Drug Product",
            "Intermediate",
            "Reference / Control"
        ]
    )

    analyst_level = st.selectbox(
        "Analyst experience level",
        ["Trainee", "Qualified analyst", "Senior analyst"]
    )

    instrument = st.text_input(
        "Instrument(s)",
        value="Incubator, Microscope, Pipette"
    )

    calibration_status = st.selectbox(
        "Calibration / Maintenance status",
        ["In date", "Overdue", "Unknown"]
    )

    recent_changes = st.text_area(
        "Recent changes (if any)",
        value="e.g. New reagent lot, new analyst, SOP revision"
    )

    notes = st.text_area(
        "Additional notes",
        value=""
    )

# -----------------------
# Prompt builder
# -----------------------
def build_prompts():
    system_prompt = (
        "You are a senior QC scientist working in a GMP environment. "
        "Your role is to support OOS investigation using a structured "
        "6M Fishbone approach (Man, Machine, Method, Material, Measurement, Environment). "
        "You must NOT make final decisions or approvals. "
        "Provide concise, evidence-based, and GMP-appropriate suggestions only. "
        "All outputs MUST be valid JSON."
    )

    user_prompt = f"""
OOS Context:
- Test name: {test_name}
- Specification: {specification}
- Observed result: {observed_result}
- Batch/Lot: {batch_lot}
- Sample type: {sample_type}
- Analyst experience level: {analyst_level}
- Instrument(s): {instrument}
- Calibration/Maintenance status: {calibration_status}
- Recent changes: {recent_changes}
- Notes: {notes}

Tasks:
1) Identify plausible causes using a 6M Fishbone framework
   (3–7 specific causes per category).
2) Prioritize causes as High / Medium / Low probability with rationale.
3) Identify evidence gaps or checks required to confirm or exclude
   each high-probability cause.
4) Propose draft CAPA (corrective and preventive actions).
   CAPA must be practical and GMP-compliant.
5) Include a GxP disclaimer.

Return ONLY valid JSON using this schema:

{{
  "fishbone": {{
    "Man": [{{"cause": "", "why_it_matters": ""}}],
    "Machine": [],
    "Method": [],
    "Material": [],
    "Measurement": [],
    "Environment": []
  }},
  "prioritization": [
    {{
      "cause": "",
      "category": "",
      "probability": "",
      "rationale": ""
    }}
  ],
  "evidence_gaps": [
    {{
      "cause": "",
      "what_to_check": "",
      "record_or_test": ""
    }}
  ],
  "capa_draft": [
    {{
      "cause": "",
      "corrective_action": "",
      "preventive_action": "",
      "effectiveness_check": ""
    }}
  ],
  "disclaimer": ""
}}
"""
    return system_prompt, user_prompt

# -----------------------
# Run analysis
# -----------------------
analyze = st.button("🧠 Analyze OOS with AI")

if analyze:
    system_prompt, user_prompt = build_prompts()

    with st.spinner("AI is analyzing potential root causes..."):
        response = client.responses.create(
            model=MODEL_NAME,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_output_tokens=1400
        )

    raw_output = response.output_text

    st.subheader("📄 Raw AI Output (JSON)")
    st.code(raw_output, language="json")

    # -----------------------
    # Parse JSON safely
    # -----------------------
    try:
        result = json.loads(raw_output)
    except json.JSONDecodeError:
        st.error(
            "AI output is not valid JSON. "
            "Please retry or refine the input information."
        )
        st.stop()

    # -----------------------
    # Display results
    # -----------------------
    st.subheader("🐟 Fishbone Analysis (6M)")
    st.json(result.get("fishbone", {}))

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Cause Prioritization")
        st.json(result.get("prioritization", []))

    with col2:
        st.subheader("🔍 Evidence Gaps / Required Checks")
        st.json(result.get("evidence_gaps", []))

    st.subheader("🛠️ Draft CAPA (QC Review Required)")
    st.json(result.get("capa_draft", []))

    st.info(
        result.get(
            "disclaimer",
            "AI is used as a supporting tool only. "
            "Final root cause determination and CAPA approval must be "
            "performed by qualified QC personnel."
        )
    )

    # -----------------------
    # Download JSON
    # -----------------------
    st.download_button(
        label="⬇️ Download OOS Fishbone Result (JSON)",
        data=json.dumps(result, indent=2).encode("utf-8"),
        file_name="OOS_Fishbone_AI_Result.json",
        mime="application/json"
    )

# -----------------------
# Footer
# -----------------------
st.markdown("---")
st.caption(
    "© QC Laboratory | AI-assisted OOS Investigation Tool | "
    "Designed for GMP-compliant environments"
)
