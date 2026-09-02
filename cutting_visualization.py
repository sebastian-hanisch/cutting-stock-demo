"""Plotly figures for the cutting-stock demo."""

import plotly.graph_objects as go

WASTE_COLOR = "#D9D9D9"
PALETTE = ["#3E8E86", "#D68A2E", "#35486A", "#8E3E86", "#86A83E", "#B03A2E"]


def pattern_figure(problem, patterns, counts, title: str) -> go.Figure:
    """One horizontal bar per distinct cutting pattern, segmented by piece
    type, with the unused remainder shown in gray - so waste is directly
    visible per pattern, not just as a single aggregate percentage."""
    order = sorted((j for j in range(len(counts)) if counts[j] > 0), key=lambda j: -counts[j])
    y_labels = [f"Muster {rank + 1} (×{counts[j]})" for rank, j in enumerate(order)]

    fig = go.Figure()
    color_for = {label: PALETTE[i % len(PALETTE)] for i, label in enumerate(problem.labels)}

    for i, label in enumerate(problem.labels):
        widths = [patterns[j, i] * problem.lengths[i] for j in order]
        if not any(w > 0 for w in widths):
            continue
        fig.add_trace(go.Bar(
            y=y_labels, x=widths, orientation="h", name=label,
            marker_color=color_for[label],
            text=[f"{patterns[j, i]}×{label}" if patterns[j, i] > 0 else "" for j in order],
            textposition="inside",
            hovertemplate=f"{label}: %{{x:.2f}} m<extra></extra>",
        ))

    waste_widths = [problem.roll_length - float(sum(patterns[j] * problem.lengths)) for j in order]
    fig.add_trace(go.Bar(
        y=y_labels, x=waste_widths, orientation="h", name="Verschnitt",
        marker_color=WASTE_COLOR,
        hovertemplate="Verschnitt: %{x:.2f} m<extra></extra>",
    ))

    fig.update_layout(
        barmode="stack", title=title,
        xaxis_title="Länge (m)", yaxis_title=None,
        xaxis=dict(fixedrange=True), yaxis=dict(fixedrange=True, autorange="reversed"),
        legend_title="Position", height=max(280, 42 * len(y_labels) + 120),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig
