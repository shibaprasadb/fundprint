"""Time in Market: returns by how long each purchase has been held, vs the Nifty 50."""
import io

import pandas as pd
import streamlit as st

import ui
from fundprint.benchmark import compare, load_bench
from fundprint.charts import allocation_chart, facet_chart
from fundprint.classify import ASSET_CLASSES, UNCLASSIFIED, classify_isin
from fundprint.lots import held_lots
from fundprint.xirr import xirr

st.set_page_config(page_title="Fundprint · Time in Market", page_icon="🔒", layout="wide")

def main():
    ui.sidebar_note()
    bench_rows, cats, manifest = ui.load_public_data()

    st.title("Returns by holding period")

    parsed = st.session_state.get("parsed")
    if parsed is None:
        st.info("Upload a statement (or see the sample) on the Home page first.")
        st.page_link("Home.py", label="← Home")
        ui.footer(manifest)
        st.stop()

    if st.session_state.get("is_sample"):
        ui.sample_banner()

    cats = st.session_state["categories"]
    overrides = st.session_state.setdefault("class_overrides", {})
    schemes = parsed.schemes.copy()
    schemes["asset_class"] = [classify_isin(i, n, cats) for i, n in zip(schemes["isin"], schemes.scheme)]
    schemes["asset_class"] = [overrides.get((f, s), a) for f, s, a in zip(schemes.folio, schemes.scheme, schemes.asset_class)]

    scope = st.radio("Which funds?", ["All funds", "Equity funds only"], horizontal=True)

    unclassified = schemes[schemes.asset_class == UNCLASSIFIED]
    if len(unclassified):
        with st.expander(f"{len(unclassified)} fund(s) couldn't be classified. Set them here."):
            for f, s in zip(unclassified.folio, unclassified.scheme):
                choice = st.selectbox(s, [UNCLASSIFIED] + ASSET_CLASSES, key=f"cls_{f}_{s}")
                if choice != UNCLASSIFIED:
                    overrides[(f, s)] = choice
                    schemes.loc[(schemes.folio == f) & (schemes.scheme == s), "asset_class"] = choice

    today = pd.Timestamp.today().normalize()
    cf = held_lots(parsed.txns, parsed.schemes, today)
    if scope == "Equity funds only":
        keep = schemes[schemes.asset_class == "Equity"]
        cf = cf.merge(keep[["folio", "scheme"]], on=["folio", "scheme"])
        with st.expander("Funds included"):
            st.write("\n".join(f"- {n}" for n in sorted(keep.scheme)))
    label = "Equity funds" if scope != "All funds" else "All funds"

    if cf.empty:
        st.warning("No held units found for this selection.")
        ui.footer(manifest)
        st.stop()

    bench = load_bench(bench_rows)
    table, n_excluded = compare(cf, bench)
    as_of = bench.date.iloc[-1]

    if n_excluded:
        st.caption(f"{n_excluded} purchase(s) are older than the benchmark's history and were left out of both sides.")
    if schemes.scheme.str.contains("IDCW|Dividend", case=False).any() and \
            schemes.scheme.str.contains("Payout", case=False).any():
        st.caption("Some funds look like IDCW payout plans. Cash paid out isn't counted, so their returns read low.")


    def png(fig):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=180, facecolor=fig.get_facecolor())
        return buf.getvalue()


    active_xirr = 100 * xirr(cf.date, cf.amount)
    if pd.isna(active_xirr):
        st.markdown(f"Your active XIRR for {label.lower()} could not be calculated.")
    else:
        st.markdown(f"Your active XIRR for {label.lower()} is **{active_xirr:.1f}%**.")

    alloc = allocation_chart(table)
    st.pyplot(alloc)
    st.download_button("Download this chart (PNG)", png(alloc), "fundprint_allocation.png", "image/png")

    facet = facet_chart(table, label, as_of)
    st.pyplot(facet)
    st.download_button("Download this chart (PNG)", png(facet), "fundprint_vs_nifty.png", "image/png")

    shown = table.rename(columns={
        "share_%": "Share of money", "my_xirr_%": "My XIRR", "nifty_xirr_%": "Nifty XIRR",
        "xirr_gap_%": "XIRR gap", "my_abs_%": "My abs. return", "nifty_abs_%": "Nifty abs. return",
    }).map(ui.pct)
    st.dataframe(shown, use_container_width=True)

    with st.expander("How this is calculated"):
        st.markdown("""
    - **Held units only.** Each purchase is kept as a lot. Units you sold are taken from the oldest lots first (first in, first out). Bounced SIPs are removed, and reinvested dividends count as free units bought on their own date.
    - **Buckets.** Each lot goes into a bucket by how long ago it was bought: under 1 year, 1-3, 3-5, and 5+ years.
    - **XIRR.** For each bucket we line up the money you put in (on each purchase date) against what those units are worth today, and find the yearly rate that connects them.
    - **Nifty 50 replay.** We take the same amounts on the same dates and imagine they went into a Nifty 50 index fund instead. Same cash flows, different fund, so the gap is about the fund and not about timing.
    - **Under 1 year** the XIRR is annualised from a few months and swings wildly, so it is faded. Read the absolute return instead.

    **Limits.** Units already sold aren't counted, which makes results look slightly kinder than reality. Cash paid out by IDCW payout plans isn't counted as a return. XIRR reflects timing as well as fund quality, which is why the index replay is shown.
    """)

    ui.footer(manifest)



try:
    main()
except Exception as exc:  # shows only the error type and place, never values
    ui.report_failure(exc)
