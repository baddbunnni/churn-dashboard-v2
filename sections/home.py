"""Overview: the umbrella question, the big picture across all factors, and links into each topic."""

import pandas as pd
import streamlit as st

import core

# (label on the chart, column or band in the data, section key)
FACTORS = [
    ("Account age", "tenure", "tenure"),
    ("Monthly downloads", "downloads", "engagement"),
    ("Weekly viewing hours", "viewing", "engagement"),
    ("Monthly charge", "charge", "plans"),
    ("Support tickets", "tickets_band", "experience"),
    ("Subscription plan", "SubscriptionType", "plans"),
    ("Genre preference", "GenrePreference", "content"),
    ("User rating", "rating", "experience"),
    ("Average viewing duration", "duration", "engagement"),
    ("Content type", "ContentType", "content"),
    ("Registered device", "DeviceRegistered", "content"),
]

TEASERS = {
    "content": "Movies vs TV, genres, and whether the device matters",
    "plans": "Basic, Standard or Premium, and what price does",
    "engagement": "Viewing hours, downloads and session length",
    "tenure": "New vs long-standing customers, by plan and viewing",
    "experience": "Ratings, support tickets and the two combined",
}


@st.cache_data
def factor_spread(df):
    frames = []
    for name, column, key in FACTORS:
        s = core.rates(df, column).rename(columns={column: "group"})
        s["factor"] = name
        s["gap"] = (s["rate"].max() - s["rate"].min()) * 100
        frames.append(s)
    return pd.concat(frames, ignore_index=True)


def render(pages):
    df = core.data()
    bench = core.benchmark(df)
    core.header("CMP7227 Data Visualisation · Subscription churn",
                "Who is more likely to cancel their subscription?",
                f"{len(df):,} customers of a streaming subscription service. Start with the big picture, "
                "then open a topic to explore it.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Customers analysed", f"{len(df):,}", border=True)
    c2.metric("Cancelled", f"{int(df['Churn'].sum()):,}", border=True)
    c3.metric("Cancellation rate (benchmark)", f"{bench:.1%}", border=True,
              help="Dashed line on every chart. Orange = above it, blue = below it.")

    spread = factor_spread(df)
    gaps = spread.groupby("factor")["gap"].first().sort_values(ascending=False)
    with st.container(border=True):
        core.question("1", "Which factors separate customers the most?",
                      "Each dot is one group of customers. The longer the line, the more that factor separates "
                      "customers who stay from those who cancel.")
        core.show(core.factor_spread_chart(spread, bench, core.FLOOR_Y_MAX, height=34 * len(FACTORS) + 60))
        weak = gaps[gaps < 1.5]
        core.finding(
            f"<b>{gaps.index[0]}</b> separates customers most (<b>{gaps.iloc[0]:.0f} pp</b> between its groups). "
            f"Engagement and price come next. {', '.join(weak.index)} barely matter (under 1.5 pp)."
        )

    core.question("2", "Explore by topic")
    cols = st.columns(len(core.TOPICS))
    gap_by_topic = {}
    for name, _, key in FACTORS:
        gap_by_topic[key] = max(gap_by_topic.get(key, 0), gaps[name])
    for col, (key, topic) in zip(cols, core.TOPICS.items()):
        with col, st.container(border=True):
            st.html(
                f'<div class="topic-card"><div class="owner">{topic["owner"]}</div>'
                f'<h4>{topic["topic"]}</h4><p class="teaser">{TEASERS[key]}</p>'
                f'<p class="gap">Largest gap: <b>{gap_by_topic[key]:.1f} pp</b></p></div>'
            )
            st.page_link(pages[key], label="Open", icon=":material/arrow_forward:")

    core.question("3", "Put it together")
    st.page_link(pages["profiles"], label="Risk profiles: combine factors to find the highest-risk customers",
                 icon=":material/join_inner:")
