import pytest

from imagen.aspect import (
    comfyui_dimensions,
    gemini_aspect,
    openai_size,
    parse_aspect,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1:1", "1:1"),
        ("9:16", "9:16"),
        ("16:9", "16:9"),
        ("4:3", "4:3"),
        ("3:4", "3:4"),
        ("2:2", "1:1"),  # reduces
    ],
)
def test_parse_aspect_ratio_str(value, expected):
    assert parse_aspect(value).ratio_str == expected


def test_parse_aspect_pixels():
    p = parse_aspect("1024x1536")
    assert p.pixels == (1024, 1536)
    assert p.ratio_w == 1024 and p.ratio_h == 1536


def test_parse_aspect_invalid():
    with pytest.raises(Exception):
        parse_aspect("garbage")
    with pytest.raises(Exception):
        parse_aspect("0:1")


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1:1", "1:1"),
        ("9:16", "9:16"),
        ("16:9", "16:9"),
        ("3:4", "3:4"),
        ("4:3", "4:3"),
    ],
)
def test_gemini_aspect_passthrough(value, expected):
    assert gemini_aspect(parse_aspect(value)) == expected


def test_gemini_aspect_nearest():
    # Unusual ratio falls back to nearest supported.
    assert gemini_aspect(parse_aspect("5:4")) in {"1:1", "4:3"}


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1:1", "1024x1024"),
        ("9:16", "1024x1536"),
        ("16:9", "1536x1024"),
        ("3:4", "1024x1536"),  # nearest portrait
        ("4:3", "1536x1024"),  # nearest landscape
    ],
)
def test_openai_size(value, expected):
    assert openai_size(parse_aspect(value)) == expected


def test_comfyui_dimensions_pixels_passthrough():
    p = parse_aspect("1024x1536")
    assert comfyui_dimensions(p, "auto") == (1024, 1536)


def test_comfyui_dimensions_square_targets():
    assert comfyui_dimensions(parse_aspect("1:1"), "low") == (512, 512)
    assert comfyui_dimensions(parse_aspect("1:1"), "medium") == (1024, 1024)
    assert comfyui_dimensions(parse_aspect("1:1"), "high") == (1280, 1280)


def test_comfyui_dimensions_3_4_medium_matches_sdxl_preset():
    # SDXL recommended 3:4 preset is 896x1152.
    assert comfyui_dimensions(parse_aspect("3:4"), "medium") == (896, 1152)


def test_comfyui_dimensions_4_3_medium_matches_sdxl_preset():
    assert comfyui_dimensions(parse_aspect("4:3"), "medium") == (1152, 896)


def test_comfyui_dimensions_target_area_is_close():
    # Each preset's W*H should be within ±15% of the nominal target.
    targets = {"low": 512 * 512, "medium": 1024 * 1024, "high": 1280 * 1280}
    for ratio in ("1:1", "9:16", "16:9", "3:4", "4:3"):
        for level, expected in targets.items():
            w, h = comfyui_dimensions(parse_aspect(ratio), level)
            assert abs(w * h - expected) / expected < 0.15
            assert w % 64 == 0 and h % 64 == 0
