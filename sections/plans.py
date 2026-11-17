"""Umaira: subscription plans and monthly charges."""

import streamlit as st

import core

TOPIC = core.TOPICS["plans"]
PLANS = core.CATEGORIES["SubscriptionType"]


def render():
    df = core.data()
    bench = core.benchmark(df)
    core.header(f"{TOPIC['topic']} · {TOPIC['owner']}", TOPIC["key"],
                "Plan type and price band compared side by side. Click a plan to see its own price pattern.")

    by_plan = core.rates(df, "SubscriptionType")
    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True):
        core.question("Q1", "Which subscription plan has the highest cancellation percentage?")
        core.click_hint("Click a plan to filter the charge chart")
        event = core.show(core.bar_chart(by_plan, "SubscriptionType", PLANS, "Subscription plan", bench,
                                         core.FLOOR_Y_MAX, select="plan"), key="plan_chart", select="plan")
        plan = core.picked(event, "plan", "SubscriptionType")
        core.finding(core.gap_finding(by_plan, "SubscriptionType"))

    selection = df if plan is None else df[df["SubscriptionType"] == plan]
    by_charge = core.rates(selection, "charge")
    with right, st.container(border=True):
        core.question("Q2", "How does cancellation vary across monthly-charge bands?")
        st.html(f'<span class="chip">Showing: {"all plans" if plan is None else plan + " plan"}</span>')
        core.show(core.line_chart(by_charge, "charge", core.labels("charge"), core.title("charge"), bench,
                                  core.y_limit(by_charge)))
        core.finding(core.gap_finding(by_charge, "charge"))

    core.selection_metrics(selection, df, bench)

    with st.container(border=True):
        core.question("Q3", "Does the charge pattern differ across plans?",
                      "One line per plan. Parallel lines mean price works the same way on every plan.")
        grid = core.rates(df, ["SubscriptionType", "charge"])
        core.show(core.line_chart(grid, "charge", core.labels("charge"), core.title("charge"), bench,
                                  core.y_limit(grid), series="SubscriptionType", series_order=PLANS,
                                  series_title="Plan", height=320))
        rises, all_rise = [], True
        for p in PLANS:
            sub = grid[grid["SubscriptionType"] == p].set_index("charge")["rate"]
            rises.append(f"{p} {sub.iloc[0]:.1%} → {sub.iloc[-1]:.1%}")
            all_rise &= bool(sub.iloc[-1] > sub.iloc[0])
        core.finding("Lowest to highest charge band: " + "; ".join(rises) + "."
                     + (" Higher charges go with higher cancellation on <b>every</b> plan, so price matters "
                        "more than plan type." if all_rise else ""))

    core.numbers_panel([("Plan", by_plan, {"SubscriptionType": "Plan"}),
                        ("Charge band", by_charge, {"charge": "Charge band"}),
                        ("Plan × charge", grid, {"SubscriptionType": "Plan", "charge": "Charge band"})])
    core.section_limit(
        "- The currency of `MonthlyCharges` is not stated, so values are shown without a symbol.\n"
        "- Charge bands are equal-width price ranges, and each holds a similar number of customers.\n"
        "- Charges are a single snapshot: price changes before cancelling cannot be seen."
    )
