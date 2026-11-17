"""Bringing it together: combine factors from different sections into customer profiles."""

import pandas as pd
import streamlit as st

import core

DIMENSIONS = [
    ("tenure", "Account age (months)", "Sunil"),
    ("viewing", "Weekly viewing hours", "Abdullah"),
    ("tickets_band", "Monthly support tickets", "Nelson"),
    ("charge", "Monthly charge band", "Humaira"),
    ("SubscriptionType", "Subscription plan", "Humaira"),
    ("GenrePreference", "Preferred genre", "Suraj"),
]
MIN_GROUP = 300


@st.cache_data
def ranked_profiles(df):
    keys = ["tenure", "viewing", "tickets_band", "charge"]
    table = core.rates(df, keys)
    return table[table["customers"] >= MIN_GROUP].sort_values("rate", ascending=False)


def render():
    df = core.data()
    bench = core.benchmark(df)
    core.header("Bringing it together · Risk profiles",
                "What happens when the strongest factors combine?",
                "Each section looks at one factor at a time. Here you can combine groups from different "
                "sections to describe a type of customer and see how far their cancellation rate moves from "
                "the average.")

    with st.container(border=True):
        st.markdown("**Build a customer profile**. Leave a factor on *Any* to ignore it.")
        cols = st.columns(3)
        mask = pd.Series(True, index=df.index)
        chosen = []
        for i, (column, label, owner) in enumerate(DIMENSIONS):
            options = ["Any", *(core.labels(column) if column in core.BANDS else core.CATEGORIES[column])]
            value = cols[i % 3].selectbox(f"{label} · {owner}", options, key=f"profile_{column}")
            if value != "Any":
                mask &= df[column] == value
                chosen.append(f"{label}: {value}")
    profile = df[mask]
    n = len(profile)
    if n == 0:
        st.warning("No customers match this profile. Set one of the factors back to *Any*.")
        return
    rate = profile["Churn"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Customers matching", f"{n:,}", f"{n / len(df):.1%} of all customers", delta_color="off", border=True)
    c2.metric("Profile cancellation rate", f"{rate:.1%}", f"{(rate - bench) * 100:+.1f} pp vs all customers",
              delta_color="inverse", border=True)
    c3.metric("Relative to average", f"{rate / bench:.2f}×", border=True)
    c4.metric("Expected cancellations per 100", f"{rate * 100:.0f}", f"average: {bench * 100:.0f}",
              delta_color="off", border=True)
    if n < MIN_GROUP:
        core.finding(f"Only {n:,} customers match, so this rate is less stable than the others. Treat it with "
                     "caution.", kind="limit")

    compare = pd.DataFrame({
        "group": ["All customers", "This profile"],
        "customers": [len(df), n],
        "cancelled": [int(df["Churn"].sum()), int(profile["Churn"].sum())],
    })
    compare["rate"] = compare["cancelled"] / compare["customers"]
    with st.container(border=True):
        st.markdown("**This profile compared with all customers**" + (f"  \n{' · '.join(chosen)}" if chosen else ""))
        core.show(core.ranked_bar_chart(compare, "group", None, bench, core.y_limit(compare), height=130))

    st.subheader("Highest- and lowest-risk combinations")
    st.caption(
        f"Every combination of account age × viewing hours × support tickets × charge band that holds at least "
        f"{MIN_GROUP} customers, ranked by cancellation rate. Groups below that size are left out because "
        "their rates are less reliable."
    )
    ranked = ranked_profiles(df)
    config = {
        "tenure": "Account age",
        "viewing": "Weekly viewing",
        "tickets_band": "Tickets / month",
        "charge": "Charge band",
        "customers": st.column_config.NumberColumn("Customers", format="localized"),
        "cancelled": st.column_config.NumberColumn("Cancelled", format="localized"),
        "rate": st.column_config.ProgressColumn("Cancellation rate", format="percent", min_value=0, max_value=1),
    }
    shown = ["tenure", "viewing", "tickets_band", "charge", "customers", "rate"]
    left, right = st.columns(2, gap="medium")
    with left:
        st.markdown(f"**Top 10: highest cancellation** (all-customer rate {bench:.1%})")
        st.dataframe(ranked.head(10), hide_index=True, width="stretch", column_config=config,
                     column_order=shown)
    with right:
        st.markdown("**Top 10: lowest cancellation**")
        st.dataframe(ranked.tail(10).iloc[::-1], hide_index=True, width="stretch", column_config=config,
                     column_order=shown)
    top, bottom = ranked.iloc[0], ranked.iloc[-1]
    core.finding(
        f"The highest-risk combination cancels at <b>{top['rate']:.1%}</b> and the lowest at "
        f"<b>{bottom['rate']:.1%}</b>, roughly {top['rate'] / bottom['rate']:.0f} times higher. That is far "
        "wider than any single factor shows on its own. These profiles show which groups a retention team "
        "could prioritise. They describe association, not proof that changing one factor would prevent "
        "cancellation."
    )
