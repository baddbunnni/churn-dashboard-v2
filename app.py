"""CMP7227 group dashboard: who is more likely to cancel their subscription?

Run locally:   streamlit run app.py
Each team member's section lives in sections/<topic>.py; shared rules live in core.py.
"""

from functools import partial

import streamlit as st

import core
from sections import content, engagement, experience, home, method, plans, profiles, tenure

st.set_page_config(page_title="Subscription churn dashboard", page_icon=":material/insights:", layout="wide")
st.html(core.STYLE)

T = core.TOPICS
pages = {
    "content": st.Page(content.render, title=f"{T['content']['topic']} · {T['content']['owner']}",
                       icon=T["content"]["icon"], url_path="content-preferences"),
    "plans": st.Page(plans.render, title=f"{T['plans']['topic']} · {T['plans']['owner']}",
                     icon=T["plans"]["icon"], url_path="plans-and-pricing"),
    "engagement": st.Page(engagement.render, title=f"{T['engagement']['topic']} · {T['engagement']['owner']}",
                          icon=T["engagement"]["icon"], url_path="engagement"),
    "tenure": st.Page(tenure.render, title=f"{T['tenure']['topic']} · {T['tenure']['owner']}",
                      icon=T["tenure"]["icon"], url_path="account-age"),
    "experience": st.Page(experience.render, title=f"{T['experience']['topic']} · {T['experience']['owner']}",
                          icon=T["experience"]["icon"], url_path="customer-experience"),
}
profiles_page = st.Page(profiles.render, title="Risk profiles", icon=":material/join_inner:",
                        url_path="risk-profiles")
together = [
    profiles_page,
    st.Page(method.render, title="Method & limitations", icon=":material/rule:", url_path="method"),
]
start = st.Page(partial(home.render, {**pages, "profiles": profiles_page}), title="Overview",
                icon=":material/home:", url_path="overview", default=True)

nav = st.navigation({
    "Start here": [start],
    "Team sections": list(pages.values()),
    "Bringing it together": together,
})

with st.sidebar:
    if not core.PARQUET.is_file() and not any((core.APP_DIR / n).is_file() for n in core.CSV_NAMES):
        st.session_state["uploaded_csv"] = st.file_uploader("Upload subscription_churn_full.csv", type=["csv"])
    st.caption("Reading key")
    st.html(core.KEY_HTML)
    st.caption("CMP7227 Data Visualisation · Birmingham City University")

nav.run()
