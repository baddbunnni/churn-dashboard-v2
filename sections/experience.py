"""Nelson: customer experience (user rating and support tickets)."""

import streamlit as st

import core

TOPIC = core.TOPICS["experience"]
RATINGS = core.labels("rating")
TICKETS = [str(n) for n in range(10)]


def render():
    df = core.data()
    bench = core.benchmark(df)
    core.header(f"{TOPIC['topic']} · {TOPIC['owner']}", TOPIC["key"],
                "Two signals of experience: the rating a customer gives (1–5) and the support tickets they raise "
                "each month (0–9).")

    by_rating = core.rates(df, "rating")
    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True):
        core.question("Q1", "Are customers giving lower ratings more likely to cancel?")
        core.click_hint("Click a rating band to filter the ticket chart")
        event = core.show(core.bar_chart(by_rating, "rating", RATINGS, core.title("rating"), bench,
                                         core.FLOOR_Y_MAX, select="rating_pick"), key="rating_chart",
                          select="rating_pick")
        band = core.picked(event, "rating_pick", "rating")
        low, high = by_rating.iloc[0], by_rating.iloc[-1]
        if low["rate"] < high["rate"]:
            core.finding(f"Low raters cancel <b>less</b> ({low['rate']:.1%}) than high raters ({high['rate']:.1%}), "
                         "the opposite of what you would expect. The gap is small, "
                         f"{(high['rate'] - low['rate']) * 100:.1f} pp.")
        else:
            core.finding(core.gap_finding(by_rating, "rating"))

    selection = df if band is None else df[df["rating"] == band]
    by_tickets = core.rates(selection, "tickets")
    with right, st.container(border=True):
        core.question("Q2", "How does cancellation vary with the number of support requests?")
        st.html(f'<span class="chip">Showing: {"all ratings" if band is None else "rating " + band}</span>')
        core.show(core.line_chart(by_tickets, "tickets", TICKETS, "Support tickets per month", bench,
                                  core.y_limit(by_tickets)))
        core.finding(core.gap_finding(by_tickets, "tickets", " tickets"))

    core.selection_metrics(selection, df, bench)

    with st.container(border=True):
        core.question("Q3", "Do customers with low ratings and many tickets cancel more?",
                      "Rows = rating, columns = tickets (adjacent counts combined).")
        grid = core.rates(df, ["rating", "tickets_band"])
        core.show(core.heatmap(grid, "rating", RATINGS[::-1], "tickets_band", core.labels("tickets_band"),
                               core.title("rating"), core.title("tickets_band"), bench, height=280,
                               big_text=True, focus_row=band))
        pivot = grid.pivot(index="rating", columns="tickets_band", values="rate")
        first, last = core.labels("tickets_band")[0], core.labels("tickets_band")[-1]
        rises = bool((pivot[last] > pivot[first]).all())
        core.finding((f"Rates rise from {first} to {last} tickets in <b>every</b> rating band. " if rises else "")
                     + "Ticket volume, not rating, goes with cancellation.")

    core.numbers_panel([("Rating", by_rating, {"rating": "Rating band"}),
                        ("Tickets", by_tickets, {"tickets": "Tickets per month"}),
                        ("Rating × tickets", grid, {"rating": "Rating", "tickets_band": "Tickets"})])
    core.section_limit(
        "- No event timing: we cannot tell whether tickets came before the decision to cancel.\n"
        "- A ticket is not proof of dissatisfaction. Some are routine questions.\n"
        "- `UserRating` is continuous (1.0–5.0), grouped into one-point bands."
    )
