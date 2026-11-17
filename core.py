"""Shared data loading, calculations, chart builders and layout helpers.

Every section of the dashboard uses these functions, so the whole app follows one
set of rules:
  * cancellation rate = customers with Churn = 1 / customers in the group
  * orange = higher than the all-customer rate, blue = lower (same everywhere)
  * the dashed line is always the all-customer rate
  * rate charts share one 0–40% scale so sections can be compared fairly
"""

from math import ceil, inf
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).parent
PARQUET = APP_DIR / "data" / "subscription_churn.parquet"
CSV_NAMES = ("subscription_churn_full.csv", "subscription_churn_full 1.csv")

# Edit this line once the group has agreed how to describe the dataset source.
DATA_SOURCE = "Approved CMP7227 dataset: subscription_churn_full.csv (customer-level subscription records)."

REQUIRED = [
    "CustomerID", "AccountAge", "MonthlyCharges", "SubscriptionType", "PaymentMethod",
    "ContentType", "DeviceRegistered", "GenrePreference", "ViewingHoursPerWeek",
    "AverageViewingDuration", "ContentDownloadsPerMonth", "UserRating",
    "SupportTicketsPerMonth", "Churn",
]
CATEGORIES = {
    "SubscriptionType": ["Basic", "Standard", "Premium"],
    "ContentType": ["Movies", "TV Shows", "Both"],
    "DeviceRegistered": ["Computer", "Mobile", "TV", "Tablet"],
    "GenrePreference": ["Action", "Comedy", "Drama", "Fantasy", "Sci-Fi"],
    "PaymentMethod": ["Bank transfer", "Credit card", "Electronic check", "Mailed check"],
}

# Band definitions: source column, bin edges (lower bound included), labels, axis title.
BANDS = {
    "tenure": ("AccountAge", [-inf, 13, 25, 37, 61, 91, inf],
               ["1–12", "13–24", "25–36", "37–60", "61–90", "91+"], "Account age (months)"),
    "charge": ("MonthlyCharges", [-inf, 8, 11, 14, 17, inf],
               ["Under 8", "8–<11", "11–<14", "14–<17", "17–20"], "Monthly charge band"),
    "viewing": ("ViewingHoursPerWeek", [-inf, 10, 20, 30, inf],
                ["<10 h", "10–<20 h", "20–<30 h", "30+ h"], "Weekly viewing hours"),
    "downloads": ("ContentDownloadsPerMonth", [-inf, 10, 20, 30, 40, inf],
                  ["0–9", "10–19", "20–29", "30–39", "40+"], "Monthly downloads"),
    "rating": ("UserRating", [-inf, 2, 3, 4, inf],
               ["1–<2", "2–<3", "3–<4", "4–5"], "User rating band"),
    "tickets_band": ("SupportTicketsPerMonth", [-inf, 2, 4, 6, 8, inf],
                     ["0–1", "2–3", "4–5", "6–7", "8–9"], "Monthly support tickets"),
    "duration": ("AverageViewingDuration", [-inf, 60, 120, inf],
                 ["Under 60", "60–<120", "120+"], "Average viewing duration (minutes)"),
}


def labels(band):
    return BANDS[band][2]


def title(band):
    return BANDS[band][3]


# ---------- Visual system ----------
ORANGE = "#D9622B"      # above the all-customer rate
BLUE = "#2F6DB5"        # at or below the all-customer rate
GREY = "#C9D2DD"
BENCH = "#3F4B5B"
INK = "#14263F"
ABOVE = "Above all-customer rate"
BELOW = "At or below all-customer rate"
TONE_SCALE = alt.Scale(domain=[ABOVE, BELOW], range=[ORANGE, BLUE])
# Okabe–Ito colours: distinguishable with common colour-vision deficiencies.
SERIES = ["#0072B2", "#E69F00", "#009E73", "#CC79A7"]
FLOOR_Y_MAX = 0.40
HEAT_SPREAD = 0.15

TOPICS = {
    "content": dict(owner="Suraj", topic="Content preferences", icon=":material/movie:",
                    key="How does cancellation vary across customers' content preferences?"),
    "plans": dict(owner="Humaira", topic="Plans & pricing", icon=":material/payments:",
                  key="How are subscription plan and monthly charges associated with cancellation?"),
    "engagement": dict(owner="Abdullah", topic="Engagement", icon=":material/play_circle:",
                       key="Are less engaged customers more likely to cancel?"),
    "tenure": dict(owner="Sunil", topic="Account age", icon=":material/hourglass_bottom:",
                   key="How does cancellation differ between newer and established customers?"),
    "experience": dict(owner="Nelson", topic="Customer experience", icon=":material/support_agent:",
                       key="How are customer ratings and support requests associated with cancellation?"),
}


# ---------- Data ----------
def _prepare(df):
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")
    df = df[REQUIRED].copy()
    if df[REQUIRED].isna().any().any():
        raise ValueError("The analysis columns contain missing values.")
    if df["CustomerID"].duplicated().any():
        raise ValueError("CustomerID values must be unique (one row per customer).")
    if not df["Churn"].isin([0, 1]).all():
        raise ValueError("Churn must be 0 (stayed) or 1 (cancelled).")
    df["Churn"] = df["Churn"].astype("int8")
    for column, order in CATEGORIES.items():
        df[column] = pd.Categorical(df[column].astype(str), categories=order, ordered=True)
    for band, (column, edges, names, _) in BANDS.items():
        df[band] = pd.cut(df[column], edges, right=False, labels=names)
    df["tickets"] = pd.Categorical(df["SupportTicketsPerMonth"], categories=range(10), ordered=True)
    return df


@st.cache_data(show_spinner="Loading customer records…")
def _load_parquet(path, modified):
    return _prepare(pd.read_parquet(path))


@st.cache_data(show_spinner="Reading the CSV…")
def _load_csv(source):
    return _prepare(pd.read_csv(source))


def data():
    """Return the prepared dataset from the bundled file, a local CSV or an upload."""
    if PARQUET.is_file():
        return _load_parquet(str(PARQUET), PARQUET.stat().st_mtime_ns)
    for name in CSV_NAMES:
        path = APP_DIR / name
        if path.is_file():
            return _load_csv(str(path))
    uploaded = st.session_state.get("uploaded_csv")
    if uploaded is not None:
        return _load_csv(uploaded)
    st.info("Upload subscription_churn_full.csv in the sidebar to load the dashboard.")
    st.stop()


def benchmark(df):
    return float(df["Churn"].mean())


def rates(df, by):
    """Cancellation rate per group. Empty groups are kept and shown as 'No customers'."""
    by = [by] if isinstance(by, str) else list(by)
    out = (
        df.groupby(by, observed=False)["Churn"]
        .agg(customers="size", cancelled="sum")
        .reset_index()
    )
    for column in by:
        out[column] = out[column].astype(str)
    out["customers"] = out["customers"].astype(int)
    out["cancelled"] = out["cancelled"].astype(int)
    out["rate"] = out["cancelled"] / out["customers"].where(out["customers"] > 0)
    return out


def tone(summary, bench):
    summary = summary.copy()
    summary["tone"] = [
        "No customers" if pd.isna(r) else (ABOVE if r > bench else BELOW) for r in summary["rate"]
    ]
    summary["vs_all"] = [
        "" if pd.isna(r) else f"{(r - bench) * 100:+.1f} pp vs all customers" for r in summary["rate"]
    ]
    summary["n_label"] = [compact(n) for n in summary["customers"]]
    summary["rate_label"] = [
        "No customers" if pd.isna(r) else f"{r:.1%}" for r in summary["rate"]
    ]
    return summary


def compact(n):
    if n >= 1000:
        return f"n={n / 1000:.1f}k"
    return f"n={n:,}"


def y_limit(*summaries):
    """Shared rate scale: 0–40% unless a filtered selection needs more room."""
    highest = max((s["rate"].max() for s in summaries if s["rate"].notna().any()), default=0)
    return min(1.0, max(FLOOR_Y_MAX, ceil(highest * 20) / 20))


# ---------- Charts ----------
def _tooltip(field, field_title):
    return [
        alt.Tooltip(f"{field}:N", title=field_title),
        alt.Tooltip("rate:Q", title="Cancellation rate", format=".2%"),
        alt.Tooltip("vs_all:N", title="Difference"),
        alt.Tooltip("customers:Q", title="Customers", format=","),
        alt.Tooltip("cancelled:Q", title="Cancelled", format=","),
    ]


def _finish(chart, height):
    return (
        chart.properties(height=height)
        .configure_view(stroke=None)
        .configure_axis(
            labelFontSize=12, titleFontSize=12, labelColor="#334155", titleColor="#475569",
            gridColor="#E6EAF0", domainColor="#CBD5E1", tickSize=0, labelPadding=6, titlePadding=10,
        )
        .configure_legend(labelFontSize=12, titleFontSize=12, orient="top", symbolStrokeWidth=3)
    )


def _benchmark_layer(bench, y_scale, horizontal=False):
    frame = pd.DataFrame({"b": [bench], "label": [f"All customers {bench:.1%}"]})
    base = alt.Chart(frame)
    if horizontal:
        rule = base.mark_rule(color=BENCH, strokeDash=[5, 4], strokeWidth=1.5).encode(
            x=alt.X("b:Q", scale=y_scale))
        text = base.mark_text(align="left", dx=4, baseline="top", y=-14, color=BENCH, fontSize=11).encode(
            x=alt.X("b:Q", scale=y_scale), text="label:N")
    else:
        # No on-chart text here: it collides with value labels. The reading key explains the line.
        return base.mark_rule(color=BENCH, strokeDash=[5, 4], strokeWidth=1.5).encode(
            y=alt.Y("b:Q", scale=y_scale), tooltip=alt.Tooltip("label:N", title="Dashed line"))
    return rule + text


def _click(name, field, nearest=False):
    """Click a mark to select it; double-click to clear. Read back with `picked()`.

    `nearest` selects the closest point to the click, so small line markers are easy to hit.
    """
    return alt.selection_point(name=name, fields=[field], on="click", clear="dblclick", empty=True,
                               nearest=nearest)


def picked(event, name, field):
    """Return the clicked value from a Streamlit chart event, or None when nothing is selected."""
    try:
        points = event["selection"][name]
    except (KeyError, TypeError):
        return None
    if isinstance(points, dict):
        points = points.get("values") or points.get(field) or []
    if isinstance(points, (list, tuple)) and points:
        first = points[0]
        if isinstance(first, dict):
            value = first.get(field)
            return value[0] if isinstance(value, list) and value else value
        return first
    return None


def bar_chart(summary, field, order, x_title, bench, y_max, select=None, height=330):
    """Vertical bars of cancellation rate, coloured by above/below the all-customer rate.

    With `select`, bars are clickable: the clicked bar stays solid and the others fade.
    """
    s = tone(summary, bench)
    y_scale = alt.Scale(domain=[0, y_max], nice=False)
    base = alt.Chart(s).encode(
        x=alt.X(f"{field}:N", sort=order, title=x_title,
                axis=alt.Axis(labelAngle=0, labelFontWeight="bold")),
        tooltip=_tooltip(field, x_title),
    )
    bars = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=46,
                         cursor="pointer" if select else "default").encode(
        y=alt.Y("rate:Q", scale=y_scale, title="Cancellation rate",
                axis=alt.Axis(format=".0%", tickCount=5)),
        color=alt.Color("tone:N", scale=TONE_SCALE, legend=None),
    )
    if select:
        param = _click(select, field)
        bars = bars.add_params(param).encode(opacity=alt.condition(param, alt.value(1.0), alt.value(0.3)))
    values = base.mark_text(dy=-8, baseline="bottom", fontSize=13, fontWeight="bold", color=INK).encode(
        y=alt.Y("rate:Q", scale=y_scale), text="rate_label:N",
    )
    counts = base.transform_calculate(zero="0").mark_text(
        baseline="bottom", dy=-6, fontSize=10, color="white"
    ).encode(y=alt.Y("zero:Q", scale=y_scale), text="n_label:N")
    return _finish(bars + values + counts + _benchmark_layer(bench, y_scale), height)


def ranked_bar_chart(summary, field, y_title, bench, x_max, height=300):
    """Horizontal bars sorted from highest to lowest cancellation rate."""
    s = tone(summary, bench)
    order = s.sort_values("rate", ascending=False)[field].tolist()
    x_scale = alt.Scale(domain=[0, x_max], nice=False)
    base = alt.Chart(s).encode(
        y=alt.Y(f"{field}:N", sort=order, title=y_title, axis=alt.Axis(labelFontWeight="bold")),
        tooltip=_tooltip(field, y_title),
    )
    bars = base.mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, size=26).encode(
        x=alt.X("rate:Q", scale=x_scale, title="Cancellation rate", axis=alt.Axis(format=".0%", tickCount=5)),
        color=alt.Color("tone:N", scale=TONE_SCALE, legend=None),
    )
    values = base.mark_text(align="left", dx=5, fontSize=13, fontWeight="bold", color=INK).encode(
        x=alt.X("rate:Q", scale=x_scale), text="rate_label:N")
    counts = base.transform_calculate(zero="0").mark_text(align="left", dx=6, fontSize=10, color="white").encode(
        x=alt.X("zero:Q", scale=x_scale), text="n_label:N")
    return _finish(bars + values + counts + _benchmark_layer(bench, x_scale, horizontal=True), height)


def line_chart(summary, field, order, x_title, bench, y_max, series=None, series_order=None,
               series_title=None, height=330, show_labels=True, select=None):
    """Rate across ordered bands. With `series`, one line per group (no causal claim)."""
    s = tone(summary, bench)
    y_scale = alt.Scale(domain=[0, y_max], nice=False)
    tooltip = _tooltip(field, x_title)
    if series:
        tooltip.insert(0, alt.Tooltip(f"{series}:N", title=series_title))
    base = alt.Chart(s).encode(
        x=alt.X(f"{field}:N", sort=order, title=x_title,
                axis=alt.Axis(labelAngle=0, labelFontWeight="bold")),
        y=alt.Y("rate:Q", scale=y_scale, title="Cancellation rate",
                axis=alt.Axis(format=".0%", tickCount=5)),
        tooltip=tooltip,
    )
    if series:
        colour = alt.Color(f"{series}:N", sort=series_order, title=series_title,
                           scale=alt.Scale(domain=series_order, range=SERIES[: len(series_order)]))
        line = base.mark_line(strokeWidth=3).encode(color=colour)
        points = base.mark_point(filled=True, size=70, stroke="white", strokeWidth=1.5).encode(
            color=colour, shape=alt.Shape(f"{series}:N", sort=series_order, title=series_title,
                                          scale=alt.Scale(domain=series_order)))
        layers = line + points
    else:
        line = base.mark_line(strokeWidth=3, color=BLUE)
        points = base.mark_point(filled=True, size=150 if select else 90, stroke="white", strokeWidth=2,
                                 cursor="pointer" if select else "default").encode(
            color=alt.Color("tone:N", scale=TONE_SCALE, legend=None))
        if select:
            param = _click(select, field, nearest=True)
            points = points.add_params(param).encode(
                opacity=alt.condition(param, alt.value(1.0), alt.value(0.3)),
                size=alt.condition(param, alt.value(170), alt.value(110)))
        layers = line + points
        if show_labels:
            layers += base.mark_text(dy=-14, fontSize=12, fontWeight="bold", color=INK).encode(text="rate_label:N")
    return _finish(layers + _benchmark_layer(bench, y_scale), height)


def heatmap(summary, row, row_order, col, col_order, row_title, col_title, bench, height=300,
            big_text=False, focus_row=None):
    """Diverging colour centred on the all-customer rate: orange above, blue below.

    `focus_row` (set by clicking another chart) keeps one row solid and fades the rest.
    """
    s = tone(summary, bench)
    s["fade"] = [focus_row is not None and v != focus_row for v in s[row]]
    # Fixed ±15 pp range for every heatmap: the same colour means the same rate in every section,
    # and small differences stay pale instead of being stretched to full colour.
    spread = HEAT_SPREAD
    s["light"] = [bool(pd.notna(r) and abs(r - bench) > spread * 0.6) for r in s["rate"]]
    ink = alt.condition("datum.light && !datum.fade", alt.value("#FFFFFF"), alt.value(INK))
    s["count_text"] = [f"{n:,} customers" if n else "" for n in s["customers"]]
    base = alt.Chart(s).encode(
        x=alt.X(f"{col}:N", sort=col_order, title=col_title,
                axis=alt.Axis(labelAngle=0, orient="top", labelFontWeight="bold")),
        y=alt.Y(f"{row}:N", sort=row_order, title=row_title, axis=alt.Axis(labelFontWeight="bold")),
        tooltip=[alt.Tooltip(f"{row}:N", title=row_title), *_tooltip(col, col_title)],
    )
    empty = base.mark_rect(color="#EEF1F5", stroke="white", strokeWidth=3, cornerRadius=4)
    cells = base.transform_filter("datum.customers > 0").mark_rect(
        stroke="white", strokeWidth=3, cornerRadius=4
    ).encode(color=alt.Color(
        "rate:Q",
        scale=alt.Scale(domain=[bench - spread, bench, bench + spread],
                        range=[BLUE, "#F4F4F2", ORANGE], clamp=True, interpolate="lab"),
        legend=alt.Legend(title="Cancellation rate", format=".0%", orient="right",
                          gradientLength=160, values=[bench - spread, bench, bench + spread]),
    ), opacity=alt.condition("datum.fade", alt.value(0.25), alt.value(1.0)))
    rate_text = base.mark_text(dy=-7 if not big_text else -9, fontSize=16 if big_text else 13,
                               fontWeight="bold").encode(
        text="rate_label:N", color=ink, opacity=alt.condition("datum.fade", alt.value(0.3), alt.value(1.0)))
    count_text = base.mark_text(dy=10 if not big_text else 12, fontSize=10).encode(
        text="count_text:N", color=ink, opacity=alt.condition("datum.fade", alt.value(0.3), alt.value(1.0)))
    return _finish(empty + cells + rate_text + count_text, height)


def factor_spread_chart(spread_frame, bench, x_max, height):
    """Overview: one row per factor, dots = groups, line = gap between lowest and highest group."""
    order = (spread_frame.groupby("factor")["gap"].first().sort_values(ascending=False).index.tolist())
    s = tone(spread_frame, bench)
    x_scale = alt.Scale(domain=[0, x_max], nice=False)
    ranges = (s.groupby("factor", as_index=False)
              .agg(low=("rate", "min"), high=("rate", "max"), gap=("gap", "first")))
    ranges["gap_label"] = [f"{g:.1f} pp" for g in ranges["gap"]]
    y = alt.Y("factor:N", sort=order, title=None, axis=alt.Axis(labelFontWeight="bold", labelLimit=260))
    span = alt.Chart(ranges).mark_rule(strokeWidth=6, color=GREY, strokeCap="round").encode(
        y=y, x=alt.X("low:Q", scale=x_scale, title="Cancellation rate of each group",
                     axis=alt.Axis(format=".0%", tickCount=5)), x2="high:Q")
    gap = alt.Chart(ranges).mark_text(align="left", dx=10, fontSize=12, fontWeight="bold", color=INK).encode(
        y=y, x=alt.X("high:Q", scale=x_scale), text="gap_label:N")
    dots = alt.Chart(s).mark_circle(size=120, opacity=0.95, stroke="white", strokeWidth=1).encode(
        y=y, x=alt.X("rate:Q", scale=x_scale),
        color=alt.Color("tone:N", scale=TONE_SCALE, legend=None),
        tooltip=[alt.Tooltip("factor:N", title="Factor"), alt.Tooltip("group:N", title="Group"),
                 alt.Tooltip("rate:Q", title="Cancellation rate", format=".2%"),
                 alt.Tooltip("vs_all:N", title="Difference"),
                 alt.Tooltip("customers:Q", title="Customers", format=",")],
    )
    return _finish(span + dots + gap + _benchmark_layer(bench, x_scale, horizontal=True), height)


def show(chart, key=None, select=None):
    """Draw a chart. With `select`, clicks rerun the page and the event is returned."""
    if select:
        return st.altair_chart(chart, width="stretch", key=key, on_select="rerun", selection_mode=[select])
    st.altair_chart(chart, width="stretch")
    return None


# ---------- Layout helpers ----------
def header(kicker, heading, intro):
    st.html(
        f'<div class="hero"><p class="kicker">{kicker}</p><h1>{heading}</h1><p>{intro}</p></div>'
    )


def question(number, text, how_to_read=None):
    st.html(f'<div class="q-title"><span class="q-badge">{number}</span><span>{text}</span></div>')
    if how_to_read:
        st.caption(how_to_read)


def finding(text, kind="finding"):
    """One-line callout. `text` contains only fixed wording and numbers computed from the data."""
    if not text:
        return
    label = {"finding": "Finding", "limit": "Limitation", "note": "Note"}[kind]
    st.html(f'<div class="callout {kind}"><b>{label}:</b> {text}</div>')


def click_hint(text):
    st.html(f'<div class="hint">👆 {text} · double-click to reset</div>')


def control_label(number, text):
    st.html(f'<div class="q-title small"><span class="q-badge alt">{number}</span><span>{text}</span></div>')


def selection_metrics(selection, df, bench, label="Customers in view"):
    total = len(selection)
    cancelled = int(selection["Churn"].sum())
    rate = cancelled / total if total else float("nan")
    c1, c2, c3 = st.columns(3)
    c1.metric(label, f"{total:,}",
              None if total == len(df) else f"{total / len(df):.0%} of all customers",
              delta_color="off", border=True)
    c2.metric("Cancelled", f"{cancelled:,}", border=True)
    c3.metric("Cancellation rate", f"{rate:.1%}",
              f"{(rate - bench) * 100:+.1f} pp vs all customers ({bench:.1%})", delta_color="inverse",
              border=True)


def gap_finding(summary, field, suffix=""):
    """Highest vs lowest group in one short sentence."""
    s = summary.dropna(subset=["rate"])
    if len(s) < 2:
        return None
    hi, lo = s.loc[s["rate"].idxmax()], s.loc[s["rate"].idxmin()]
    return (f"<b>{hi[field]}{suffix}</b> is highest at <b>{hi['rate']:.1%}</b>, "
            f"<b>{lo[field]}{suffix}</b> lowest at <b>{lo['rate']:.1%}</b>: a "
            f"<b>{(hi['rate'] - lo['rate']) * 100:.1f} pp</b> gap.")


def numbers_panel(tables):
    """One expander per section holding every chart's numbers, one tab per chart."""
    with st.expander("Numbers behind this section", icon=":material/table_chart:"):
        tabs = st.tabs([name for name, _, _ in tables])
        for tab, (_, summary, names) in zip(tabs, tables):
            table = summary[[*names, "customers", "cancelled", "rate"]].rename(
                columns={**names, "customers": "Customers", "cancelled": "Cancelled",
                         "rate": "Cancellation rate"})
            tab.dataframe(
                table, hide_index=True, width="stretch",
                column_config={
                    "Customers": st.column_config.NumberColumn(format="localized"),
                    "Cancelled": st.column_config.NumberColumn(format="localized"),
                    "Cancellation rate": st.column_config.NumberColumn(format="percent"),
                },
            )


def section_limit(text):
    with st.expander("Limitations for this section"):
        st.markdown(text)


STYLE = """
<style>
.block-container {max-width: 1320px; padding-top: 2.6rem;}
.hero {background: linear-gradient(120deg, #0F2742 0%, #1C4A80 100%); color: #fff;
  border-radius: 16px; padding: 1.4rem 1.8rem 1.5rem; margin-bottom: .6rem;}
.hero .kicker {color: #A9C8F0; font-size: .74rem; font-weight: 700; letter-spacing: .11em;
  text-transform: uppercase; margin: 0 0 .45rem;}
.hero h1 {color: #fff; font-size: clamp(1.55rem, 2.8vw, 2.25rem); line-height: 1.15;
  margin: 0 0 .5rem; padding: 0; letter-spacing: -.02em;}
.hero p {color: #DCE8F8; margin: 0; font-size: .98rem; max-width: 62rem;}
.q-title {display: flex; gap: .6rem; align-items: center; font-weight: 700; font-size: 1.12rem;
  color: #14263F; margin: .1rem 0 .1rem;}
.q-title.small {font-size: .95rem;}
.q-badge {background: #14263F; color: #fff; border-radius: 6px; padding: .12rem .5rem;
  font-size: .78rem; letter-spacing: .04em; white-space: nowrap;}
.q-badge.alt {background: #D9622B;}
.callout {border-left: 4px solid #2F6DB5; background: rgba(47,109,181,.08); border-radius: 0 8px 8px 0;
  padding: .65rem .9rem; margin: .2rem 0 .4rem; font-size: .93rem; line-height: 1.5;}
.callout.limit {border-left-color: #D9622B; background: rgba(217,98,43,.08);}
.callout.note {border-left-color: #64748B; background: rgba(100,116,139,.08);}
.hint {font-size: .82rem; color: #475569; background: #F3F6FA; border-radius: 999px;
  display: inline-block; padding: .18rem .7rem; margin: 0 0 .2rem;}
.chip {display: inline-block; background: #14263F; color: #fff; border-radius: 999px;
  padding: .1rem .6rem; font-size: .8rem; font-weight: 600;}
.key {display: flex; flex-wrap: wrap; gap: 1rem; font-size: .85rem; color: #334155; margin: .2rem 0 .4rem;}
.key span {display: inline-flex; align-items: center; gap: .35rem;}
.sw {width: 14px; height: 14px; border-radius: 3px; display: inline-block;}
.dash {width: 22px; border-top: 2px dashed #3F4B5B; display: inline-block;}
.topic-card h4 {margin: 0 0 .2rem; padding: 0; font-size: 1.05rem;}
.topic-card .owner {font-size: .8rem; font-weight: 700; color: #D9622B; letter-spacing: .06em;
  text-transform: uppercase;}
.topic-card ol {padding-left: 1.1rem; margin: .4rem 0; font-size: .88rem;}
.topic-card .teaser {font-size: .86rem; color: #334155; margin: .2rem 0 .4rem; min-height: 2.6em;}
.topic-card .gap {font-size: .82rem; color: #475569; margin: 0;}
div[data-testid="stMetricValue"] {font-variant-numeric: tabular-nums;}
@media (max-width: 700px) {.block-container {padding-left: 1rem; padding-right: 1rem;}
  .hero {padding: 1.1rem;}}
</style>
"""

KEY_HTML = (
    '<div class="key">'
    f'<span><i class="sw" style="background:{ORANGE}"></i>Above the all-customer rate</span>'
    f'<span><i class="sw" style="background:{BLUE}"></i>At or below the all-customer rate</span>'
    '<span><i class="dash"></i>All-customer rate (benchmark)</span>'
    '<span>n = customers in the group</span>'
    '</div>'
)


def reading_key():
    st.html(KEY_HTML)
