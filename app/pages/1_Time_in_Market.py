"""Time in Market: returns by how long each purchase has been held, vs the Nifty 50."""
import io

import pandas as pd
import streamlit as st

import ui
from fundprint.benchmark import compare, load_bench
from fundprint.charts import allocation_chart, facet_chart, gaps_chart, periodicity_chart
from fundprint.classify import ASSET_CLASSES, UNCLASSIFIED, classify_isin
from fundprint.insights import fund_gaps, periodicity
from fundprint.lots import held_lots
from fundprint.xirr import xirr

st.set_page_config(page_title="Fundprint · Time in Market", page_icon="🔒", layout="wide")

PERIODICITY_CAPTION = (
    "Every purchase you've made, including ones since sold, shown against the Nifty 50 for context. "
    "\"Periodic\" means within 5 days of your usual investing day for that fund. "
    "Regular rebalancing on other dates isn't recognised yet."
)


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

    unclassified = schemes[schemes.asset_class == UNCLASSIFIED]
    if len(unclassified):
        with st.expander(f"{len(unclassified)} fund(s) couldn't be classified. Set them here."):
            for f, s in zip(unclassified.folio, unclassified.scheme):
                # Fund names come from the PDF, so they are shown with st.text, which never reads
                # Markdown or makes links. Widget labels would (FP-01), so the label stays fixed.
                st.text(s)
                choice = st.selectbox("Asset class", [UNCLASSIFIED] + ASSET_CLASSES, key=f"cls_{f}_{s}",
                                      label_visibility="collapsed")
                if choice != UNCLASSIFIED:
                    overrides[(f, s)] = choice
                    schemes.loc[(schemes.folio == f) & (schemes.scheme == s), "asset_class"] = choice

    today = pd.Timestamp.today().normalize()
    all_cf = held_lots(parsed.txns, parsed.schemes, today)
    all_cf = all_cf.merge(schemes[["folio", "scheme", "asset_class"]], on=["folio", "scheme"], how="left")
    bench = load_bench(bench_rows)
    as_of = bench.date.iloc[-1]


    def png(fig):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=180, facecolor=fig.get_facecolor())
        return buf.getvalue()


    st.header("By time in market")
    scope = st.radio("Which funds? (This choice changes the charts and table in this section only.)",
                     ["All funds", "Equity funds only"], horizontal=True)
    cf = all_cf
    if scope == "Equity funds only":
        keep = schemes[schemes.asset_class == "Equity"]
        cf = cf.merge(keep[["folio", "scheme"]], on=["folio", "scheme"])
        with st.expander("Funds included"):
            st.text("\n".join(f"• {n}" for n in sorted(keep.scheme)))   # plain text, see above
    label = "Equity funds" if scope != "All funds" else "All funds"

    if cf.empty:
        st.warning("No held units found for this selection.")
    else:
        table, n_excluded = compare(cf, bench)
        if n_excluded:
            st.caption(f"{n_excluded} purchase(s) are older than the benchmark's history and were left out of both sides.")
        if schemes.scheme.str.contains("IDCW|Dividend", case=False).any() and \
                schemes.scheme.str.contains("Payout", case=False).any():
            st.caption("Some funds look like IDCW payout plans. Cash paid out isn't counted, so their returns read low.")

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

    st.header("The big picture")
    st.caption("These charts always use your whole portfolio; the toggle above doesn't change them.")

    gaps = fund_gaps(all_cf, bench, today)
    if gaps.table.empty:
        st.caption("No equity funds to compare.")
    else:
        fig = gaps_chart(gaps.table)
        st.pyplot(fig)
        st.download_button("Download this chart (PNG)", png(fig), "fundprint_index_twin.png", "image/png")
        if gaps.n_hidden:
            st.caption("Showing your 12 largest equity funds.")
    if (all_cf.asset_class != "Equity").any():
        st.caption("Debt, gold and other non-equity funds aren't shown here.")

    regular = periodicity(parsed.txns, bench)
    if regular is None:
        st.caption("No purchases fall inside the benchmark's history.")
    else:
        fig = periodicity_chart(regular, as_of)
        st.pyplot(fig)
        st.download_button("Download this chart (PNG)", png(fig), "fundprint_regular_investing.png", "image/png")
        st.caption(PERIODICITY_CAPTION)

    with st.expander("How this is calculated"):
        st.markdown("""
    - **Held units only.** Each purchase is kept as a lot. Units you sold are taken from the oldest lots first (first in, first out). Bounced SIPs are removed, and reinvested dividends count as free units bought on their own date.
    - **Buckets.** Each lot goes into a bucket by how long ago it was bought: under 1 year, 1-3, 3-5, and 5+ years.
    - **XIRR.** For each bucket we line up the money you put in (on each purchase date) against what those units are worth today, and find the yearly rate that connects them.
    - **Nifty 50 replay.** We take the same amounts on the same dates and imagine they went into a Nifty 50 index fund instead. Same cash flows, different fund, so the gap is about the fund and not about timing.
    - **Under 1 year** the XIRR is annualised from a few months and swings wildly, so it is faded. Read the absolute return instead.
    - **Index twin per fund.** Each fund's purchases are replayed into a Nifty 50 index fund on the same dates, and the two XIRRs are compared. It is the Nifty 50 for every fund, not each fund's own category.
    - **Regular investing.** For each fund, Fundprint finds the day of the month you most often invest on, and counts a purchase as periodic if it's within 5 days of that day (counting across the month end). A fund needs at least 3 such purchases to have a pattern. Switches, reinvested dividends and reversed payments aren't counted.

    **Limits.** Units already sold aren't counted, which makes results look slightly kinder than reality. Cash paid out by IDCW payout plans isn't counted as a return. XIRR reflects timing as well as fund quality, which is why the index replay is shown.
    """)

    ui.footer(manifest)



try:
    main()
except Exception as exc:  # shows only the error type and place, never values
    ui.report_failure(exc)
