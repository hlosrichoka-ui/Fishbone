# =========================================================
# OOS Fishbone Analyzer (AI-assisted) - Streamlit Web App
# Works WITHOUT OpenAI Python SDK (no `from openai import OpenAI`)
# Uses REST API via `requests` to avoid SDK version conflicts.
# =========================================================

import os
import json
import requests
import streamlit as st

# -----------------------
# Page configuration
# -----------------------
st.set_page_config(page_title="OOS Fishbone Analyzer", page_icon="🐟", layout="wide")
st.title("🐟 OOS Fishbone Analyzer (AI-assisted)")
st.caption("AI is decision-support only. Final conclusions and CAPA approval must be performed by qualified QC personnel.")

# -----------------------
# API Key check
# -----------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY not found. Please set it in Environment Variables or Streamlit Secrets.")
    st.stop()

# Model (set in Secrets as OPENAI_MODEL if needed)
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # change if your org uses a different allowed model

API_URL = "https://api.openai.com/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json",
}

# -----------------------
# Sidebar inputs
# -----------------------
with st.sidebar:
    st.header("📋 OOS Context")

    test_name = st.text_input("Test name", "Plaque Assay (MDCK)")
    specification = st.text_input("Specification", "1.0–2.0 × 10^6 PFU/mL")
    observed_result = st.text_input("Observed result", "3.8 × 10^5 PFU/mL")
    batch_lot = st.text_input("Batch / Lot No.", "Lot-XXXX")

    sample_type = st.selectbox(
        "Sample type",
        ["Drug Substance", "Drug Product", "Intermediate", "Reference / Control"]
    )

    analyst_level = st.selectbox(
        "Analyst experience level",
        ["Trainee", "Qualified analyst", "Senior analyst"]
    )

    instrument = st.text_input("Instrument(s)", "Incubator, Microscope, Pipette")
    calibration_status = st.selectbox("Calibration / Maintenance status", ["In date", "Overdue", "Unknown"])

    recent_changes = st.text_area("Recent changes (if any)", "e.g. New reagent lot, new analyst, SOP revision")
    notes = st.text_area("Additional notes", "")

    st.divider()
    st.subheader("⚙️ Options")
    temperature = st.slider("Creativity (temperature)", 0.0, 1.0, 0.2, 0.05)
    max_tokens = st.slider("Max tokens", 400, 2500, 1400, 100)

# -----------------------
# Prompt builder
# -----------------------
def build_messages():
    system_prompt = (
        "You are a senior QC scientist working in a GMP environment. "
        "Your role is to support OOS investigation using a structured 6M Fishbone approach "
        "(Man, Machine, Method, Material, Measurement, Environment). "
        "You must NOT make final decisions or approvals. Provide concise, evidence-based, GMP-appropriate suggestions. "
        "Return ONLY valid JSON. No markdown. No extra text."
    )

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
            {"cause": "", "corrective_action": "", "preventive_action": "", "effectiveness_check": ""}
        ],
        "disclaimer": ""
    }

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
1) Identify plausible causes using a 6M Fishbone framework (3–7 specific causes per category).
2) Prioritize causes as High / Medium / Low probability with rationale.
3) Identify evidence gaps or checks required to confirm or exclude each high-probability cause.
4) Propose draft CAPA (corrective and preventive actions) that are practical and GMP-compliant.
5) Include a GxP disclaimer that AI is decision-support only.

Return ONLY valid JSON that matches EXACTLY this schema (keys must match):
{json.dumps(schema, indent=2)}
""".strip()

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

# -----------------------
# Call OpenAI (REST)
# -----------------------
def call_openai_chat(messages, temperature=0.2, max_tokens=1400):
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": float(temperature),
        "max_tokens": int(max_tokens),
    }
    r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"OpenAI API error {r.status_code}: {r.text}")
    data = r.json()
    return data["choices"][0]["message"]["content"]

# -----------------------
# JSON repair (1 retry)
# -----------------------
def repair_to_json(bad_text):
    repair_messages = [
        {
            "role": "system",
            "content": (
                "Fix the following text into valid JSON ONLY. "
                "Do not add explanations. Output JSON only."
            ),
        },
        {"role": "user", "content": bad_text},
    ]
    return call_openai_chat(repair_messages, temperature=0.0, max_tokens=1200)

# -----------------------
# UI action
# -----------------------
analyze = st.button("🧠 Analyze OOS with AI")

if analyze:
    messages = build_messages()

    with st.spinner("Analyzing potential root causes..."):
        try:
            raw = call_openai_chat(messages, temperature=temperature, max_tokens=max_tokens)
        except Exception as e:
            st.error(str(e))
            st.stop()

    st.subheader("📄 Raw AI Output")
    st.code(raw, language="json")

    # Try parse JSON; if fails, attempt one repair call
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        st.warning("AI output was not valid JSON. Attempting 1-time JSON repair...")
        try:
            fixed = repair_to_json(raw)
            st.code(fixed, language="json")
            result = json.loads(fixed)
            raw = fixed
        except Exception as e:
            st.error(f"JSON repair failed: {e}")
            st.stop()

    # Display sections
    st.subheader("🐟 Fishbone (6M)")
    st.json(result.get("fishbone", {}))

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📊 Prioritization")
        st.json(result.get("prioritization", []))
    with c2:
        st.subheader("🔍 Evidence gaps / Checks")
        st.json(result.get("evidence_gaps", []))

    st.subheader("🛠️ CAPA draft (QC review required)")
    st.json(result.get("capa_draft", []))

    st.info(result.get("disclaimer", "AI is decision-support only; QC must review and approve final conclusions/CAPA."))

    st.download_button(
        "⬇️ Download JSON",
        data=json.dumps(result, indent=2).encode("utf-8"),
        file_name="OOS_Fishbone_AI_Result.json",
        mime="application/json",
    )

st.markdown("---")
st.caption("For QC use: ensure prompt/output logging and QC approval workflow for GMP compliance.")
