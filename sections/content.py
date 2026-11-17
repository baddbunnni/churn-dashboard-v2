"""Suraj: content preferences. Rebuilt from Suraj's Power BI report (suraj.pbix):
title card, overall cancellation card, device slicer, content-type columns and genre bars
sorted by cancellation, and click-to-filter between the two charts.
"""

import streamlit as st

import core

TOPIC = core.TOPICS["content"]
DEVICES = core.CATEGORIES["DeviceRegistered"]


def render():
    df = core.data()
    bench = core.benchmark(df)
    core.header(f"{TOPIC['topic']} · {TOPIC['owner']}", "Subscription cancellation: content preferences",
                "Understanding cancellation patterns across content preferences and registered devices.")

    with st.container(border=True):
        core.control_label("Q3", "Do these patterns change depending on the registered device?")
        device = st.pills("Registered device", ["All devices", *DEVICES], default="All devices",
                          key="content_device", label_visibility="collapsed") or "All devices"
    by_device = df if device == "All devices" else df[df["DeviceRegistered"] == device]

    by_type = core.rates(by_device, "ContentType")
    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True):
        core.question("Q1", "Does cancellation differ between movie, TV-show and mixed viewers?")
        core.click_hint("Click a column to filter the genre chart")
        event = core.show(core.bar_chart(by_type, "ContentType", "-y", "Content type", bench,
                                         core.FLOOR_Y_MAX, select="ctype"),
                          key="content_type_chart", select="ctype")
        chosen = core.picked(event, "ctype", "ContentType")
        core.finding(core.gap_finding(by_type, "ContentType"))

    selection = by_device if chosen is None else by_device[by_device["ContentType"] == chosen]
    by_genre = core.rates(selection, "GenrePreference")
    with right, st.container(border=True):
        scope = "all content types" if chosen is None else f"{chosen} viewers only"
        core.question("Q2", "Which preferred genres have higher cancellation?")
        st.html(f'<span class="chip">Showing: {scope} · {device.lower()}</span>')
        core.show(core.ranked_bar_chart(by_genre, "GenrePreference", "Preferred genre", bench,
                                        core.y_limit(by_genre)))
        core.finding(core.gap_finding(by_genre, "GenrePreference"))

    core.selection_metrics(selection, df, bench)

    with st.container(border=True):
        core.question("Q3", "Genre × device: does the device change the genre pattern?",
                      "A row with one even colour means the genre's rate barely changes across devices.")
        grid = core.rates(df, ["GenrePreference", "DeviceRegistered"])
        core.show(core.heatmap(grid, "GenrePreference", core.CATEGORIES["GenrePreference"], "DeviceRegistered",
                               DEVICES, "Preferred genre", "Registered device", bench, height=300,
                               big_text=True))
        device_rates = core.rates(df, "DeviceRegistered")
        span = (device_rates["rate"].max() - device_rates["rate"].min()) * 100
        genres = core.rates(df, "GenrePreference").sort_values("rate", ascending=False)
        genre_span = (genres["rate"].iloc[0] - genres["rate"].iloc[-1]) * 100
        core.finding(f"Overall cancellation differs by only <b>{span:.1f} pp</b> across devices, compared with "
                     f"<b>{genre_span:.1f} pp</b> across genres ({genres.iloc[0]['GenrePreference']} highest). "
                     "Device adds almost nothing. Genre is the stronger signal.")

    core.numbers_panel([("Content type", by_type, {"ContentType": "Content type"}),
                        ("Genre", by_genre, {"GenrePreference": "Genre"}),
                        ("Genre × device", grid, {"GenrePreference": "Genre", "DeviceRegistered": "Device"})])
    core.section_limit(
        "- `GenrePreference` is one recorded preference, not everything a customer watches.\n"
        "- `DeviceRegistered` records one device per customer.\n"
        "- Differences are a few percentage points: they show association, not cause."
    )
