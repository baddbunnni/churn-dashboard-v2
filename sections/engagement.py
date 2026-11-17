"""Abdullah: customer engagement (viewing hours, downloads, average viewing duration)."""

import streamlit as st

import core

TOPIC = core.TOPICS["engagement"]
DURATION_MARKS = [0, 30, 60, 90, 120, 150, 180]


def row_check(grid):
    """True when, for every viewing band, the top download band cancels less than the bottom one."""
    pivot = grid.pivot(index="viewing", columns="downloads", values="rate")
    first, last = core.labels("downloads")[0], core.labels("downloads")[-1]
    return bool((pivot[last] < pivot[first]).all())


def render():
    df = core.data()
    bench = core.benchmark(df)
    core.header(f"{TOPIC['topic']} · {TOPIC['owner']}", TOPIC["key"],
                "Engagement measured two ways, weekly viewing and monthly downloads, across short and long "
                "viewing sessions.")

    with st.container(border=True):
        core.control_label("Q3", "Do these patterns differ for shorter and longer average viewing sessions?")
        low, high = st.select_slider("Average viewing duration (minutes)", options=DURATION_MARKS,
                                     value=(0, 180), key="engagement_duration")
    if low == high:
        st.warning("Choose a range wider than a single value.")
        st.stop()
    duration = df["AverageViewingDuration"]
    selection = df if (low, high) == (0, 180) else df[(duration >= low) & (duration < high)]

    by_hours = core.rates(selection, "viewing")
    y_max = core.y_limit(by_hours, core.rates(selection, "downloads"))
    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True):
        core.question("Q1", "How does cancellation vary with weekly viewing hours?")
        core.click_hint("Click a point to filter the downloads chart")
        event = core.show(core.line_chart(by_hours, "viewing", core.labels("viewing"), core.title("viewing"),
                                          bench, y_max, select="hours"), key="hours_chart", select="hours")
        band = core.picked(event, "hours", "viewing")
        core.finding(core.gap_finding(by_hours, "viewing"))

    focus = selection if band is None else selection[selection["viewing"] == band]
    by_downloads = core.rates(focus, "downloads")
    with right, st.container(border=True):
        core.question("Q2", "How does cancellation vary with monthly downloads?")
        st.html(f'<span class="chip">Showing: {"all viewers" if band is None else band + " per week"} · '
                f'{low}–{high} min sessions</span>')
        core.show(core.bar_chart(by_downloads, "downloads", core.labels("downloads"), core.title("downloads"),
                                 bench, max(y_max, core.y_limit(by_downloads))))
        core.finding(core.gap_finding(by_downloads, "downloads", " downloads"))

    core.selection_metrics(focus, df, bench)

    with st.container(border=True):
        core.question("Q3", "Viewing × downloads: does each measure add something?",
                      "Read across a row: same viewing level, more downloads. The duration slider filters this too.")
        grid = core.rates(selection, ["viewing", "downloads"])
        core.show(core.heatmap(grid, "viewing", core.labels("viewing")[::-1], "downloads", core.labels("downloads"),
                               core.title("viewing"), core.title("downloads"), bench, height=290, big_text=True,
                               focus_row=band))
        filled = grid.dropna(subset=["rate"])
        hi, lo = filled.loc[filled["rate"].idxmax()], filled.loc[filled["rate"].idxmin()]
        core.finding(
            f"Least engaged ({hi['viewing']}, {hi['downloads']} downloads) <b>{hi['rate']:.1%}</b> vs most engaged "
            f"({lo['viewing']}, {lo['downloads']}) <b>{lo['rate']:.1%}</b>."
            + (" More downloads lower the rate in every viewing band, so the two measures add up."
               if row_check(grid) else "")
        )

    core.numbers_panel([("Viewing hours", by_hours, {"viewing": "Weekly viewing"}),
                        ("Downloads", by_downloads, {"downloads": "Monthly downloads"}),
                        ("Viewing × downloads", grid, {"viewing": "Weekly viewing", "downloads": "Downloads"})])
    core.section_limit(
        "- The unit of `AverageViewingDuration` is not documented. Its 5–180 range suggests minutes.\n"
        "- Engagement is a snapshot: it may drop *because* a customer has already decided to leave.\n"
        "- Bands include the lower bound and exclude the upper bound (10 ≤ hours < 20)."
    )
