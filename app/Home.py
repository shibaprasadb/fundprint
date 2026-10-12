"""Landing page: the privacy promise, upload, password, sample data."""
import pandas as pd
import streamlit as st

import ui
from fundprint.classify import UNCLASSIFIED, classify_isin
from fundprint.parse import CasError, parse_cas
from fundprint.sample import sample_cas, sample_categories

st.set_page_config(page_title="Fundprint", page_icon="🔒", layout="wide")

def main():
    ui.sidebar_note()
    bench, cats, manifest = ui.load_public_data()

    st.title("Fundprint")
    st.markdown("*A CASual look at your mutual fund statement.*")

    st.markdown(ui.PROMISE)
    st.markdown(ui.PROMISE_DETAIL)

    with st.expander("How to get your CAS"):
        st.markdown(
            "Request a **Detailed** Consolidated Account Statement from "
            "[CAMS](https://www.camsonline.com/Investors/Statements/Consolidated-Account-Statement) "
            "or KFintech. Set the start date before your first investment. "
            "Either 'with zero balance folios' or 'without' works."
        )

    with st.form("upload"):
        file = st.file_uploader("Your CAS (PDF)", type="pdf")
        password = st.text_input("PDF password (leave empty if none)", type="password")
        go = st.form_submit_button("Read my statement")
    use_sample = st.button("Or try with sample data")

    # The password is used once to open the file, then dropped (P9).
    if go and file is not None:
        try:
            with st.spinner("Reading your statement…"):
                parsed = parse_cas(file.getvalue(), password)
            st.session_state["parsed"] = parsed
            st.session_state["categories"] = cats
            st.session_state["is_sample"] = False
        except CasError as e:
            st.error(str(e))
        except Exception as exc:  # never show details: they could contain statement data (P8)
            st.error("Couldn't read this statement. Is it a CAMS/KFintech detailed CAS? "
                     f"(Error type: {type(exc).__name__})")
        password = None
    elif go:
        st.warning("Choose a PDF first.")

    if use_sample:
        st.session_state["parsed"] = sample_cas(pd.Timestamp.today())
        st.session_state["categories"] = sample_categories()
        st.session_state["is_sample"] = True

    parsed = st.session_state.get("parsed")
    if parsed is not None:
        s = parsed.schemes
        unclassified = sum(
            classify_isin(i, n, st.session_state["categories"]) == UNCLASSIFIED
            for i, n in zip(s["isin"], s.scheme)
        )
        label = "sample portfolio" if st.session_state["is_sample"] else "your statement"
        st.success(f"Read {label}: {len(s)} funds, {unclassified} unclassified.")
        if parsed.period_start is not None and parsed.period_end is not None:
            st.caption(f"Statement period: {parsed.period_start:%d %b %Y} to {parsed.period_end:%d %b %Y}")
        st.page_link("pages/1_Vintage.py", label="See returns by holding period →")

    ui.footer(manifest)



try:
    main()
except Exception as exc:  # shows only the error type and place, never values
    ui.report_failure(exc)
