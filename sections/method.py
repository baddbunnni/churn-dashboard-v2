"""Method, data checks and limitations shared by every section."""

import pandas as pd
import streamlit as st

import core


def render():
    df = core.data()
    bench = core.benchmark(df)
    core.header("Method & limitations", "How the numbers were produced and what they cannot tell us",
                "This page applies to every section of the dashboard.")

    with st.container(border=True):
        st.subheader("Dataset")
        st.markdown(core.DATA_SOURCE)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rows (customers)", f"{len(df):,}", border=True)
        c2.metric("Unique CustomerID", f"{df['CustomerID'].nunique():,}", border=True)
        c3.metric("Missing values in analysis fields", f"{int(df[core.REQUIRED].isna().sum().sum()):,}", border=True)
        c4.metric("Cancelled (Churn = 1)", f"{int(df['Churn'].sum()):,} ({bench:.2%})", border=True)
        st.caption("These checks run every time the data loads. The app refuses to start if IDs are duplicated, "
                   "values are missing, or Churn holds anything other than 0 or 1.")

    with st.container(border=True):
        st.subheader("Shared calculation")
        st.markdown(
            "**Cancellation rate = customers with `Churn = 1` ÷ customers in the selected group.** Every chart "
            "uses this calculation and the same all-customer benchmark. Rates are compared instead of counts "
            "because a larger group will always have more cancellations even if its customers are no more "
            "likely to leave."
        )
        rows = []
        for key, (column, edges, names, label) in core.BANDS.items():
            rows.append({"Banded field": label, "Source column": column, "Bands": " | ".join(names)})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption("Each band includes its lower bound and excludes its upper bound (for example, 10 ≤ hours < 20). "
                   "Band edges follow each team member's work plan. Groups are not always the same size (for "
                   "example, account-age bands), so every chart shows its customer counts.")

    with st.container(border=True):
        st.subheader("Design decisions")
        st.markdown(
            "- **One colour rule everywhere:** orange marks a group above the all-customer rate and blue marks "
            "one at or below it. Heatmaps use a diverging colour centred on the same benchmark, with one fixed "
            "±15 pp range in every section, so equal colours always mean equal rates and small gaps stay pale.\n"
            "- **Shared 0–40% scale** on rate charts with a zero baseline, so bar lengths are honest and can be "
            "compared between sections. The scale only extends if a filter produces a higher rate.\n"
            "- **Counts beside every percentage** (n on the bars, in tooltips and in tables) so small groups "
            "can be spotted.\n"
            "- **Overview first, then details on demand:** the start page ranks factors, sections answer one "
            "question each, and the risk-profile page combines them.\n"
            "- **Linked views:** clicking a bar or point filters or highlights the other charts in the same "
            "section, so a viewer can drill from one factor into another without leaving the page. Each "
            "filtered chart shows a 'Showing:' label so the current state is always visible.\n"
            "- **Colour is never the only cue.** Every bar and cell also carries its value as text, and "
            "multi-line charts use different marker shapes."
        )

    with st.container(border=True):
        st.subheader("Limitations")
        st.markdown(
            "- **Association, not causation.** Every result compares groups observed at a single point in time. "
            "No factor was varied in a controlled way.\n"
            "- **No timing.** The data has no dates, so we cannot tell whether low viewing or support tickets "
            "came before the decision to cancel.\n"
            "- **One-factor views can mislead (Simpson's paradox).** A pattern seen in one chart may change once "
            "another factor is held constant. The heatmaps and the risk-profile page partly address this.\n"
            "- **Undocumented units.** `AccountAge` (assumed months), `AverageViewingDuration` (assumed minutes) "
            "and the `MonthlyCharges` currency are not stated in the source.\n"
            "- **Very even distributions.** Most numeric fields are spread almost uniformly, and every category "
            "holds nearly the same number of customers. That is unusual for real customer data and suggests a "
            "synthetic or curated dataset, so results may not carry over to a real streaming service.\n"
            "- **Survivorship.** Long-tenure customers are, by definition, the ones who have not yet left."
        )
