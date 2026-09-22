"""Color-ramp helpers for the Streamlit app's overlay plots.

Not a MATLAB port -- there's no equivalent in the original tool's plots.
Each overlay chart shows several nominal conditions (e.g. one line per
tested load) at once, and each condition contributes three traces: raw
scatter, the smoothed spline, and the final Pacejka fit curve. Plotly's
default color cycling assigns all three traces of every condition from
one shared, unrelated-looking color sequence, so "these three traces
belong to the same 150 lbf condition" isn't visible from color alone --
only from reading the legend text carefully.

Instead, each condition gets one hue (assigned from a small fixed set, in
order, never cycled or reused within a chart), and its three traces are
three lightness steps of that *same* hue: light for raw, medium for
smoothed, dark/saturated for the fit -- so a viewer can tell which traces
go together at a glance, and that darker consistently means "more
processed."
"""

from __future__ import annotations

import colorsys

# Fixed-order hue anchors, each a saturated mid-tone hex color. Assign to
# conditions by position (condition_hue(0), condition_hue(1), ...) within
# one chart; never reorder or cycle once a chart's conditions are in a
# stable order (ascending load/camber).
HUE_ANCHORS = (
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua/green
    "#eda100",  # yellow/gold
    "#e87ba4",  # magenta
    "#4a3aa7",  # violet
    "#e34948",  # red
    "#008300",  # green
)

# Lightness (HLS L, 0=black, 1=white) for the raw/smoothed/fit steps
# within one condition's hue -- light enough that raw scatter reads as
# "background" data, dark enough that the fit curve reads as the
# authoritative result.
_RAW_LIGHTNESS = 0.80
_SMOOTHED_LIGHTNESS = 0.58
_FIT_LIGHTNESS = 0.36


def condition_hue(index: int) -> str:
    """The hue anchor for the `index`-th condition in a chart (0-based).
    Wraps past the fixed set for more conditions than anchors, but a
    single chart should stay well under that (see CLAUDE.md's roadmap:
    5 nominal loads is the typical maximum)."""
    return HUE_ANCHORS[index % len(HUE_ANCHORS)]


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def _rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{round(min(1.0, max(0.0, c)) * 255):02x}" for c in rgb)


def lightness_step(hex_color: str, lightness: float) -> str:
    """`hex_color`'s own hue/saturation re-rendered at a different HLS
    lightness -- the building block for a light->dark ramp within one
    hue. `lightness` is in [0, 1] (0=black, 1=white)."""
    r, g, b = _hex_to_rgb(hex_color)
    hue, _, saturation = colorsys.rgb_to_hls(r, g, b)
    return _rgb_to_hex(colorsys.hls_to_rgb(hue, lightness, saturation))


def raw_smoothed_fit_colors(hex_color: str) -> tuple[str, str, str]:
    """The (raw, smoothed, fit) color ramp for one condition's hue."""
    return (
        lightness_step(hex_color, _RAW_LIGHTNESS),
        lightness_step(hex_color, _SMOOTHED_LIGHTNESS),
        lightness_step(hex_color, _FIT_LIGHTNESS),
    )
