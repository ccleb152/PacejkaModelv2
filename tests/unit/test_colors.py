"""Tests for pacejka.colors -- not a MATLAB port (the original's plots
have no equivalent color scheme), so plain unit tests, per CLAUDE.md's
conventions for non-port utility modules."""

import colorsys

import pytest

from pacejka.colors import (
    HUE_ANCHORS,
    condition_hue,
    lightness_step,
    raw_smoothed_fit_colors,
)


def _hex_to_hls(hex_color):
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    return colorsys.rgb_to_hls(r, g, b)


def test_condition_hue_assigns_in_fixed_order():
    assert condition_hue(0) == HUE_ANCHORS[0]
    assert condition_hue(1) == HUE_ANCHORS[1]
    assert condition_hue(4) == HUE_ANCHORS[4]


def test_condition_hue_wraps_past_the_anchor_set():
    assert condition_hue(len(HUE_ANCHORS)) == HUE_ANCHORS[0]


def test_lightness_step_preserves_hue_and_saturation():
    original_h, _, original_s = _hex_to_hls(HUE_ANCHORS[0])
    stepped = lightness_step(HUE_ANCHORS[0], 0.5)
    h, l, s = _hex_to_hls(stepped)
    assert h == pytest.approx(original_h, abs=1e-2)
    assert s == pytest.approx(original_s, abs=1e-2)
    assert l == pytest.approx(0.5, abs=1e-2)


def test_lightness_step_is_a_valid_hex_color():
    for anchor in HUE_ANCHORS:
        for lightness in (0.0, 0.36, 0.58, 0.8, 1.0):
            result = lightness_step(anchor, lightness)
            assert result.startswith("#")
            assert len(result) == 7
            int(result[1:], 16)  # doesn't raise


def test_raw_smoothed_fit_colors_go_light_to_dark():
    for anchor in HUE_ANCHORS:
        raw, smoothed, fit = raw_smoothed_fit_colors(anchor)
        _, raw_l, _ = _hex_to_hls(raw)
        _, smoothed_l, _ = _hex_to_hls(smoothed)
        _, fit_l, _ = _hex_to_hls(fit)
        assert raw_l > smoothed_l > fit_l


def test_raw_smoothed_fit_colors_share_the_condition_hue():
    anchor = HUE_ANCHORS[2]
    anchor_h, _, _ = _hex_to_hls(anchor)
    for color in raw_smoothed_fit_colors(anchor):
        h, _, _ = _hex_to_hls(color)
        assert h == pytest.approx(anchor_h, abs=1e-2)


def test_different_conditions_get_visibly_different_hues():
    hue_0 = _hex_to_hls(condition_hue(0))[0]
    hue_1 = _hex_to_hls(condition_hue(1))[0]
    assert hue_0 != hue_1
