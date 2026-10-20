"""Interactive scientific figures; no calculations replace the src engine."""

import altair as alt
import pandas as pd

COLORS = ["#16866b", "#d05b45", "#bd8a24", "#4e78a4", "#696d73"]
CHART_CONFIG = {
    "background": "#fbfcfc",
    "view": {"stroke": "#d8e3e2", "strokeWidth": 1},
    "axis": {"labelColor": "#40504f", "titleColor": "#263635", "gridColor": "#e7eeee"},
    "legend": {"labelColor": "#40504f", "titleColor": "#263635"},
}


def security_scores(records, threshold):
    points = (
        alt.Chart(
            pd.DataFrame(
                [
                    {
                        "index": i + 1,
                        "task": r["G\u00f6rev"],
                        "score": r["G\u00fcvenlik S"],
                        "status": "E\u015fik alt\u0131"
                        if r["G\u00fcvenlik S"] < threshold
                        else "E\u015fik ve \u00fcst\u00fc",
                    }
                    for i, r in enumerate(records)
                ]
            )
        )
        .mark_circle(size=65)
        .encode(
            x=alt.X(
                "index:Q",
                title="G\u00f6rev s\u0131ras\u0131",
                axis=alt.Axis(tickMinStep=1),
            ),
            y=alt.Y(
                "score:Q",
                title="G\u00fcvenlik puan\u0131 S",
                scale=alt.Scale(domain=[0, 1]),
            ),
            color=alt.Color(
                "status:N",
                title=None,
                scale=alt.Scale(
                    domain=["E\u015fik ve \u00fcst\u00fc", "E\u015fik alt\u0131"],
                    range=COLORS[:2],
                ),
            ),
            tooltip=["task:N", alt.Tooltip("score:Q", format=".6f"), "status:N"],
        )
    )
    rule = (
        alt.Chart(pd.DataFrame([{"threshold": threshold}]))
        .mark_rule(strokeDash=[5, 4], color="#696d73")
        .encode(
            y="threshold:Q", tooltip=[alt.Tooltip("threshold:Q", title="E\u015fik")]
        )
    )
    return (points + rule).properties(height=260).configure(**CHART_CONFIG)


def lines(records, x, y, group, *, x_title, y_title, height=250):
    return (
        alt.Chart(pd.DataFrame(records))
        .mark_line(point=True)
        .encode(
            x=alt.X(f"{x}:Q", title=x_title),
            y=alt.Y(f"{y}:Q", title=y_title, scale=alt.Scale(zero=True)),
            color=alt.Color(f"{group}:N", title=None, scale=alt.Scale(range=COLORS)),
            tooltip=[
                alt.Tooltip(f"{x}:Q", title=x_title),
                alt.Tooltip(f"{y}:Q", title=y_title, format=".5f"),
                group,
            ],
        )
        .properties(height=height)
        .configure(**CHART_CONFIG)
        .interactive()
    )


def bars(records, x, y, *, y_title, group=None, height=260, log=False):
    chart = alt.Chart(pd.DataFrame(records)).mark_bar(size=32)
    if log:
        # A bar's zero baseline is undefined on a logarithmic axis.
        chart = chart.mark_point(filled=True, size=130)
    encoding = {
        "x": alt.X(f"{x}:N", title=None, axis=alt.Axis(labelAngle=0)),
        "y": alt.Y(
            f"{y}:Q",
            title=y_title,
            scale=alt.Scale(type="log" if log else "linear", zero=not log),
        ),
        "tooltip": [x, alt.Tooltip(f"{y}:Q", title=y_title, format=".6f")],
        "color": alt.Color(
            f"{group or x}:N", title=None, scale=alt.Scale(range=COLORS)
        ),
    }
    if group:
        encoding["xOffset"] = f"{group}:N"
        encoding["tooltip"].append(group)
    return chart.encode(**encoding).properties(height=height).configure(**CHART_CONFIG)


def triangles(assessments, aggregated, perspective):
    records = []
    for name, number in [
        (f"Uzman {i + 1}", getattr(a, perspective)) for i, a in enumerate(assessments)
    ] + [("Birle\u015fik", getattr(aggregated, perspective))]:
        for point, value in enumerate((number.low, number.modal, number.high)):
            records.append(
                {
                    "score": value,
                    "membership": float(point == 1),
                    "series": name,
                    "order": point,
                }
            )
    return (
        alt.Chart(pd.DataFrame(records))
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=alt.X(
                "score:Q",
                title="G\u00fcvenlik de\u011ferlendirme \u00f6l\u00e7e\u011fi",
                scale=alt.Scale(domain=[0, 1]),
            ),
            y=alt.Y(
                "membership:Q",
                title="\u00dcyelik derecesi",
                scale=alt.Scale(domain=[0, 1]),
            ),
            color=alt.Color("series:N", title=None, scale=alt.Scale(range=COLORS)),
            order="order:Q",
            tooltip=["series:N", "score:Q", "membership:Q"],
        )
        .properties(height=280)
        .configure(**CHART_CONFIG)
    )
