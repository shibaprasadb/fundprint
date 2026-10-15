"""Landing page: the privacy promise, sample data first, then upload and the request-a-statement checklist."""
import pandas as pd
import streamlit as st

import ui
from fundprint.parse import CasError, parse_cas
from fundprint.sample import sample_cas, sample_categories

st.set_page_config(page_title="Fundprint", page_icon="🔒", layout="wide")

RESULTS_PAGE = "pages/1_Time_in_Market.py"


def read_statement(file, password, cats):
    """Open the file and keep the result in memory. Returns True when it worked."""
    try:
        with st.spinner("Reading your statement…"):
            parsed = parse_cas(file.getvalue(), password)
    except CasError as e:
        ui.show_error(str(e), e.step)
        return False
    except Exception:  # never show details: they could contain statement data (P8)
        ui.show_error("Couldn't read this file. Is it a CAMS or KFintech statement PDF?", step=1)
        return False
    st.session_state["parsed"] = parsed
    st.session_state["categories"] = cats
    st.session_state["is_sample"] = False
    return True


def main():
    ui.sidebar_note()
    bench, cats, manifest = ui.load_public_data()

    ui.header_bar()
    st.markdown(
        "Fundprint goes one level deeper than a single XIRR number. It breaks down your mutual fund "
        "investments in different ways, such as how long you have held each purchase and how "
        "that compares with a Nifty 50 index fund, so you can see what is really driving your returns."
    )

    ui.promise_box()
    st.markdown(ui.PROMISE_DETAIL)

    # The payoff first: the sample is one click away
    if st.button("See it with sample data", type="primary"):
        st.session_state["parsed"] = sample_cas(pd.Timestamp.today())
        st.session_state["categories"] = sample_categories()
        st.session_state["is_sample"] = True
        st.switch_page(RESULTS_PAGE)
    st.caption("A made-up portfolio, so you can see what Fundprint shows before using your own.")

    ui.section_bar("Use your own statement")

    st.subheader("Already have your statement?")
    file = st.file_uploader("Your statement (PDF)", type="pdf")
    done = False
    if file is not None:
        # Choose the file, type the password, press Enter (or the button): no other clicks.
        # clear_on_submit empties the box after every try, including a failed one (P9).
        # autocomplete="off" asks the browser not to offer to save the password.
        with st.form("password", clear_on_submit=True):
            password = st.text_input("Password", type="password", autocomplete="off")
            st.caption("The password you set on the CAMS form.")
            go = st.form_submit_button("Show my results")
        if go:
            # The password is used once to open the file, then dropped (P9).
            done = read_statement(file, password, cats)
            password = None
    if done:
        st.switch_page(RESULTS_PAGE)

    ui.cas_checklist()

    ui.footer(manifest)


try:
    main()
except Exception as exc:  # shows only the error type and place, never values
    ui.report_failure(exc)
