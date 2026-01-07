# =========================================================
# OOS Fishbone Analyzer (AI-assisted)
# Uses OpenAI Responses API (NEW, supported)
# No OpenAI SDK import -> avoids version issues
# =========================================================

import os
import json
import requests
import streamlit as st

# -----------------------
# Page config
# -----------------------
st.set_page_config(
    page_title="OOS Fishbone Analyzer",
    page_icon="🐟",
    layout="wide"
)

st.title("🐟 OOS Fishbone Analyzer (AI-assisted)")
st.caption(
    "AI is used as a decision-support tool only. "
    "Final root cause and CAPA approval must be performed by QC personnel."
)

# -----------------------
# API Key
# -----------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("❌ OPENAI_API_KEY not found. Please set it in Environment Variables or Streamlit Secrets.")
    st.stop()

MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")  # ใช้รุ่นใหม่

API_URL = "https://api.openai.com/v1/responses"

HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json",
}

# -----------------------
# Sidebar – OOS Context
# -----------------------
with st.sidebar:
    st.header("📋 OOS Context")

    test_name = st.text_input("Test name", "Plaque Assay (MDCK)")
    specification = st.text_input("Specification", "1.0–2.0 × 10^6 PFU/mL")
    observed_result = st.text_input("Observed result", "3.8 × 10^5 PFU/mL")
    batch_lot = st.text_input("Batch / Lot", "Lot-XXXX")

    sample_type = st.selectbox(
        "Sample type",
        ["Drug Substance", "Drug Product", "Intermediate", "Reference / Control"]
    )

    analyst_level = st.selectbox(
        "Analyst level",
        ["Trainee", "Qualified analyst", "Senior analyst"]
    )

    instrument = st.text_input(
        "Instrument(s)",
        "Incubator, Microscope, Pipette"
    )

    calibration_status = st.selectbox(
        "Calibration / Maintenance status",
        ["In date", "Overdue", "Unknown"]
    )

    recent_changes = st.text_area(
        "Recent changes",
        "e.g. new reagent lot, SOP revision, new analyst"
    )

    notes = st.text_area("Additional notes", "")

    st.divider()
    temperature = st.slider("Creativity (temperature)", 0.0, 1.0, 0.2, 0.05)

# -----------------------
# Prompt builder
# -----------------------
def build_input():
    schema = {
        "fishbone": {
            "Man": [{"cause": "", "why_it_matters": ""}],
            "Machine": [],
            "Method": [],
            "Material": [],
            "Measurement": [],
            "Environment": []
        },
        "prioritization": [
            {"cause": "", "category": "", "probability": "", "rationale": ""}
        ],
        "evidence_gaps": [
            {"cause": "", "what_to_check": "", "record_or_test": ""}
        ],
        "capa_draft": [
            {
                "cause": "",
                "corrective_action": "",
                "preventive_action": "",
                "effectiveness_check": ""
            }
        ],
        "disclaimer": ""
    }

    user_text = f"""
You are a senior QC scientist working in a GMP environment.
You support OOS investigation using a 6M Fishbone approach
(Man, Machine, Method, Material, Measurement, Environment).

You MUST NOT make final decisions.
Return ONLY valid JSON. No markdown. No explanation text.

OOS Context:
- Test name: {test_name}
- Specification: {specification}
- Observed result: {observed_result}
- Batch/Lot: {batch_lot}
- Sample type: {sample_type}
- Analyst level: {analyst_level}
- Instrument(s): {instrument}
- Calibration status: {calibration_status}
- Recent changes: {recent_changes}
- Notes: {notes}

Tasks:
1) Identify 3–7 plausible causes per 6M category
2) Prioritize causes (High / Medium / Low) with rationale
3) Identify evidence gaps or checks
4) Propose draft CAPA (corrective + preventive)
5) Add a GxP disclaimer (AI = decision support only)

Return JSON exactly matching this schema:
{json.dumps(schema, indent=2)}
""".strip()

    return user_text

# -----------------------
# Call OpenAI Responses API
# -----------------------
def call_openai(prompt_text, temperature):
    payload = {
        "model": MODEL,
        "input": prompt_text,
        "temperature": temperature,
        "max_output_tokens": 1500,
    }

    r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=90)
    if r.status_code != 200:
        raise RuntimeError(f"OpenAI API error {r.status_code}: {r.text}")

    data = r.json()

    # Responses API: text อยู่ใน output[0].content[0].text
    return data["output"][0]["content"][0]["text"]

# -----------------------
# Run
# -----------------------
if st.button("🧠 Analyze OOS with AI"):
    prompt_text = build_input()

    with st.spinner("AI is analyzing root causes..."):
        try:
            raw_text = call_openai(prompt_text, temperature)
        except Exception as e:
            st.error(str(e))
            st.stop()

    st.subheader("📄 Raw AI Output")
    st.code(raw_text, language="json")

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        st.error("❌ AI response is not valid JSON. Please refine inputs and try again.")
        st.stop()

    # -----------------------
    # Display results
    # -----------------------
    st.subheader("🐟 Fishbone (6M)")
    st.json(result.get("fishbone", {}))

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📊 Prioritization")
        st.json(result.get("prioritization", []))
    with c2:
        st.subheader("🔍 Evidence Gaps")
        st.json(result.get("evidence_gaps", []))

    st.subheader("🛠️ Draft CAPA (QC review required)")
    st.json(result.get("capa_draft", []))

    st.info(
        result.get(
            "disclaimer",
            "AI is a decision-support tool only. Final decisions must be made by QC."
        )
    )

    st.download_button(
        "⬇️ Download JSON",
        data=json.dumps(result, indent=2).encode("utf-8"),
        file_name="OOS_Fishbone_AI_Result.json",
        mime="application/json",
    )

st.markdown("---")
st.caption("Designed for GMP / QC environments | Responses API (current OpenAI standard)")

