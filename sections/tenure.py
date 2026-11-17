"""Sunil: account age (tenure), by plan and by viewing engagement."""

import streamlit as st

import core

TOPIC = core.TOPICS["tenure"]
PLANS = core.CATEGORIES["SubscriptionType"]
TENURE = core.labels("tenure")


def render():
    df = core.data()
    bench = core.benchmark(df)
    median_hours = float(df["ViewingHoursPerWeek"].median())
    core.header(f"{TOPIC['topic']} · {TOPIC['owner']}", TOPIC["key"],
                "Months since the account was opened, compared across plans and between light and heavy viewers.")

    with st.container(border=True):
        core.control_label("Q3", "Does the account-age pattern change between lower and higher engagement groups?")
        choice = st.segmented_control(
            "Engagement group",
            ["All customers", f"Lower engagement (< {median_hours:.1f} h/week)",
             f"Higher engagement (≥ {median_hours:.1f} h/week)"],
            default="All customers", key="tenure_engagement", label_visibility="collapsed",
        ) or "All customers"
    hours = df["ViewingHoursPerWeek"]
    if choice.startswith("Lower"):
        selection = df[hours < median_hours]
    elif choice.startswith("Higher"):
        selection = df[hours >= median_hours]
    else:
        selection = df

    by_age = core.rates(selection, "tenure")
    left, right = st.columns([1, 1.15], gap="medium")
    with left, st.container(border=True):
        core.question("Q1", "Which account-age groups have higher cancellation percentages?")
        core.click_hint("Click a bar to highlight that row in Q2")
        event = core.show(core.bar_chart(by_age, "tenure", TENURE, core.title("tenure"), bench,
                                         core.y_limit(by_age), select="age", height=340),
                          key="age_chart", select="age")
        band = core.picked(event, "age", "tenure")
        core.finding(core.gap_finding(by_age, "tenure", " months"))

    by_age_plan = core.rates(selection, ["tenure", "SubscriptionType"])
    pivot = by_age_plan.pivot(index="tenure", columns="SubscriptionType", values="rate")
    with right, st.container(border=True):
        core.question("Q2", "Does the account-age pattern differ across subscription plans?")
        st.html(f'<span class="chip">Showing: {choice.split(" (")[0].lower()}'
                + (f' · {band} months highlighted' if band else '') + '</span>')
        core.show(core.heatmap(by_age_plan, "tenure", TENURE, "SubscriptionType", PLANS, core.title("tenure"),
                               "Subscription plan", bench, height=340, big_text=True, focus_row=band))
        newest, oldest = TENURE[0], TENURE[-1]
        if band:
            row = pivot.loc[band]
            core.finding(f"At {band} months: " + ", ".join(f"{p} <b>{row[p]:.1%}</b>" for p in PLANS) + ".")
        else:
            falls = all(pivot.loc[newest, p] > pivot.loc[oldest, p] for p in PLANS)
            leader = pivot.idxmax(axis=1).value_counts()
            core.finding(("Rates fall with account age on <b>every</b> plan. " if falls else "")
                         + f"{leader.index[0]} is highest in {leader.iloc[0]} of {len(pivot)} age bands.")

    core.selection_metrics(selection, df, bench)

    with st.container(border=True):
        core.question("Q3", "Lower vs higher viewers across account age",
                      "Parallel lines mean the same tenure pattern. The gap between them is the extra risk "
                      "linked to low viewing.")
        both = df.assign(engagement=(hours >= median_hours).map({False: "Lower engagement",
                                                                 True: "Higher engagement"}))
        grid = core.rates(both, ["tenure", "engagement"])
        core.show(core.line_chart(grid, "tenure", TENURE, core.title("tenure"), bench, core.y_limit(grid),
                                  series="engagement", series_order=["Lower engagement", "Higher engagement"],
                                  series_title="Group", height=320))
        p3 = grid.pivot(index="tenure", columns="engagement", values="rate")
        gaps = (p3["Lower engagement"] - p3["Higher engagement"]) * 100
        core.finding(
            f"New, light viewers cancel at <b>{p3.loc[newest, 'Lower engagement']:.1%}</b>, compared with "
            f"<b>{p3.loc[oldest, 'Higher engagement']:.1%}</b> for long-standing heavy viewers."
            + (f" Light viewers are higher in every band (by {gaps.min():.1f}–{gaps.max():.1f} pp)."
               if (gaps > 0).all() else "")
        )

    core.numbers_panel([("Account age", by_age, {"tenure": "Account age (months)"}),
                        ("Age × plan", by_age_plan, {"tenure": "Account age", "SubscriptionType": "Plan"}),
                        ("Age × engagement", grid, {"tenure": "Account age", "engagement": "Group"})])
    core.section_limit(
        "- `AccountAge` runs 1–119, so months is assumed. Confirm this with the source.\n"
        "- It supports comparisons by tenure, not calendar trends (a single snapshot).\n"
        "- Survivorship: customers who left early never reach the long-tenure bands."
    )
