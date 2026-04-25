"""Aspect-ratio and resolution normalization across providers.

The CLI accepts a small set of aspect strings (`1:1`, `9:16`, `16:9`, `4:3`,
`3:4`) plus arbitrary `WxH` pixel pairs. Each provider has its own native
representation, so this module owns the conversion in one place.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Literal

from imagen.errors import ImagenError

Resolution = Literal["low", "medium", "high", "auto"]

# Allowed sizes for OpenAI gpt-image-1 family.
OPENAI_SIZES = ("1024x1024", "1024x1536", "1536x1024")

# Native aspect strings supported by Gemini ImageConfig.aspect_ratio.
GEMINI_ASPECTS = {"1:1", "9:16", "16:9", "4:3", "3:4", "21:9", "9:21"}

_RATIO_RE = re.compile(r"^(\d+):(\d+)$")
_PIXELS_RE = re.compile(r"^(\d+)x(\d+)$")

# resolution -> target total pixel count for ComfyUI (W*H ≈ this).
_TARGET_PIXELS: dict[Resolution, int] = {
    "low": 512 * 512,        # 0.26 MP
    "medium": 1024 * 1024,   # 1.05 MP
    "high": 1280 * 1280,     # 1.64 MP
    "auto": 1024 * 1024,
}


@dataclass
class ParsedAspect:
    """Normalized aspect representation."""

    ratio_w: float
    ratio_h: float
    pixels: tuple[int, int] | None  # set when user passed WxH directly

    @property
    def ratio_str(self) -> str:
        # Reduce to integers if possible.
        if self.ratio_w.is_integer() and self.ratio_h.is_integer():
            w, h = int(self.ratio_w), int(self.ratio_h)
            g = math.gcd(w, h)
            return f"{w // g}:{h // g}"
        return f"{self.ratio_w:g}:{self.ratio_h:g}"


def parse_aspect(value: str) -> ParsedAspect:
    s = value.strip().lower()
    m = _RATIO_RE.match(s)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
        if w <= 0 or h <= 0:
            raise ImagenError(f"Invalid aspect '{value}'")
        return ParsedAspect(ratio_w=float(w), ratio_h=float(h), pixels=None)
    m = _PIXELS_RE.match(s)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
        if w <= 0 or h <= 0:
            raise ImagenError(f"Invalid pixel size '{value}'")
        return ParsedAspect(ratio_w=float(w), ratio_h=float(h), pixels=(w, h))
    raise ImagenError(
        f"Invalid aspect '{value}': expected RATIO (e.g. 9:16) or WxH (e.g. 1024x1536)"
    )


def gemini_aspect(parsed: ParsedAspect) -> str:
    """Closest supported Gemini aspect ratio string."""
    target = parsed.ratio_w / parsed.ratio_h
    candidate = parsed.ratio_str
    if candidate in GEMINI_ASPECTS:
        return candidate
    # Pick nearest by |log ratio|.
    best = min(
        GEMINI_ASPECTS,
        key=lambda a: abs(math.log(_aspect_to_float(a)) - math.log(target)),
    )
    return best


def openai_size(parsed: ParsedAspect) -> str:
    """Map to one of OpenAI's three supported sizes."""
    target = parsed.ratio_w / parsed.ratio_h
    return min(
        OPENAI_SIZES,
        key=lambda s: abs(math.log(_size_to_float(s)) - math.log(target)),
    )


def comfyui_dimensions(
    parsed: ParsedAspect, resolution: Resolution
) -> tuple[int, int]:
    """Compute (width, height) for ComfyUI templates."""
    if parsed.pixels is not None:
        w, h = parsed.pixels
        return _round_to_multiple(w, 8), _round_to_multiple(h, 8)
    target_area = _TARGET_PIXELS[resolution]
    ratio = parsed.ratio_w / parsed.ratio_h
    # W*H = target_area, W/H = ratio  =>  H = sqrt(target_area / ratio)
    h_exact = math.sqrt(target_area / ratio)
    w_exact = h_exact * ratio
    return _round_to_multiple(int(round(w_exact)), 64), _round_to_multiple(
        int(round(h_exact)), 64
    )


def _round_to_multiple(value: int, m: int) -> int:
    return max(m, int(round(value / m)) * m)


def _aspect_to_float(s: str) -> float:
    a, b = s.split(":")
    return int(a) / int(b)


def _size_to_float(s: str) -> float:
    a, b = s.split("x")
    return int(a) / int(b)
