"""Workforce Pell Readiness Checker (Streamlit app)."""
from pathlib import Path

import pandas as pd
import streamlit as st

from eligibility import FAQ_URL, HOUR_RANGES, check_program, summarize

STATE_FILE = Path(__file__).resolve().parent.parent / "analysis" / "data" / "state_status_2026-11-17.csv"
STATUS_ICON = {"Met": "✅", "Not met": "❌", "Needs check": "⚠️"}


@st.cache_data
def load_states():
    df = pd.read_csv(STATE_FILE)
    return df.sort_values("State").set_index("State")


st.set_page_config(page_title="Workforce Pell Readiness Checker", page_icon="📋")
st.title("Workforce Pell Readiness Checker")
st.write("Check a short-term training program against the main Workforce Pell requirements, "
         "and see where your state's approval process stands.")
st.warning("**Not official guidance.** This prototype is a self-check based on public federal guidance. "
           "Only the governor's certification and U.S. Department of Education approval determine eligibility.")

states = load_states()

with st.form("program"):
    st.subheader("1. Your program")
    state = st.selectbox("State where the program is offered", states.index)
    col1, col2 = st.columns(2)
    weeks = col1.number_input("Length (weeks of instruction)", min_value=0, max_value=104, value=10, step=1)
    unit = col2.selectbox("Unit of program size", list(HOUR_RANGES))
    amount = st.number_input("Program size (in the unit chosen above)", min_value=0, max_value=2000, value=300, step=1)

    st.subheader("2. Program details")
    choices = ["Yes", "No", "Not sure"]
    offered = st.radio("Has the program met these length rules, continuously offered, for the past 12 months?",
                       choices, horizontal=True, index=2)
    accredited = st.radio("Is the program within your institution's accreditation?", choices, horizontal=True, index=2)
    credential = st.radio("Does it lead to a recognized postsecondary credential (industry certificate, license, "
                          "apprenticeship certificate)?", choices, horizontal=True, index=2)
    credit = st.radio("Does completion earn academic credit toward a certificate or degree?",
                      choices, horizontal=True, index=2)
    excluded = st.checkbox("The program includes correspondence, remedial or ESL, study abroad, "
                           "or direct assessment coursework")
    online = st.radio("Is it offered online to students in other states?", ["No", "Yes"], horizontal=True)

    st.subheader("3. Outcomes (optional)")
    know_rates = st.checkbox("I have completion and job placement rates")
    col3, col4 = st.columns(2)
    completion = col3.number_input("Completion rate (%)", min_value=0.0, max_value=100.0, value=70.0, step=1.0)
    placement = col4.number_input("Job placement rate (%)", min_value=0.0, max_value=100.0, value=70.0, step=1.0)

    submitted = st.form_submit_button("Check my program", type="primary")

if submitted:
    row = states.loc[state]
    note = row["Review_Note"] if isinstance(row.get("Review_Note"), str) else ""
    results = check_program(
        weeks=weeks, amount=amount, unit=unit,
        offered_12_months=offered, within_accreditation=accredited,
        recognized_credential=credential, earns_credit=credit,
        excluded_coursework=excluded, online_out_of_state=online,
        completion_rate=completion if know_rates else None,
        placement_rate=placement if know_rates else None,
        state_stage=int(row["Stage_Order"]), state_name=state, state_note=note,
    )

    verdict, message = summarize(results)
    st.header("Results")
    (st.error if verdict == "Not met" else st.info)(message)

    for rule_type, label in [("Program", "Program requirements"), ("State", "State process"),
                             ("Outcomes", "Outcomes and federal approval")]:
        st.subheader(label)
        for r in [r for r in results if r["type"] == rule_type]:
            st.markdown(f"{STATUS_ICON[r['status']]} **{r['rule']}** — {r['status']}  \n"
                        f"{r['reason']}  \n<small>Source: {r['source']}</small>", unsafe_allow_html=True)

    st.subheader(f"Where {state} stands")
    st.write(f"**Tracker stage:** {int(row['Stage_Order'])} — {row['Overall_Stage']}  \n"
             f"**Last verified:** {row['Last_Verified']}")
    if isinstance(row.get("Primary_Source"), str):
        links = [u.strip() for u in str(row.get("Source_URL", "")).split(";") if u.strip().startswith("http")]
        st.write("**Source:** " + row["Primary_Source"] + ("  \n" + "  \n".join(links) if links else ""))

st.divider()
st.caption(f"Rules: [U.S. Department of Education, Workforce Pell FAQs (Oct 2026)]({FAQ_URL}). "
           "State stages: Workforce Pell State Tracker, data frozen 2026-11-17. "
           "Built by Anruo Wang.")
