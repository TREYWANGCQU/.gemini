# config/plugins/frontend-design/skills/web-theme-curator/scripts/color_math.py
#!/usr/bin/env python3
"""
Color Mathematics & Perceptual Space Engine (OKLCH, WCAG Contrast, and Grayscale)
Provides mathematical color conversions between sRGB, OKLCH, and relative luminance
for deterministic color aesthetics and quality gate validation without external dependencies.
"""

import math
import re
from typing import Tuple, Optional


def normalize_hex(hex_str: str) -> str:
    """Normalize 3, 4, 6, or 8-digit hex string into standardized lowercase #rrggbb."""
    s = hex_str.strip().lower()
    if not s.startswith("#"):
        s = "#" + s
    clean = s[1:]
    if len(clean) == 3:
        return "#" + "".join([c * 2 for c in clean])
    elif len(clean) == 4:
        return "#" + "".join([c * 2 for c in clean[:3]])
    elif len(clean) == 6:
        return "#" + clean
    elif len(clean) == 8:
        return "#" + clean[:6]
    return s


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Convert hex string (#rgb or #rrggbb) to (R, G, B) tuple [0..255]."""
    norm = normalize_hex(hex_str).lstrip("#")
    if len(norm) != 6:
        raise ValueError(f"Invalid hex color string: {hex_str}")
    r = int(norm[0:2], 16)
    g = int(norm[2:4], 16)
    b = int(norm[4:6], 16)
    return r, g, b


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert (R, G, B) [0..255] to #rrggbb."""
    r_clamped = max(0, min(255, int(round(r))))
    g_clamped = max(0, min(255, int(round(g))))
    b_clamped = max(0, min(255, int(round(b))))
    return f"#{r_clamped:02x}{g_clamped:02x}{b_clamped:02x}"


def parse_color_to_rgb(color_str: str) -> Optional[Tuple[int, int, int]]:
    """Parse hex, rgb(...), or rgba(...) string to (R, G, B) [0..255]."""
    if not color_str:
        return None
    s = color_str.strip()
    if s.startswith("#"):
        try:
            return hex_to_rgb(s)
        except Exception:
            return None
    
    m_rgb = re.match(r'rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', s, re.IGNORECASE)
    if m_rgb:
        return int(m_rgb.group(1)), int(m_rgb.group(2)), int(m_rgb.group(3))
    
    return None


def srgb_channel_to_linear(c_byte: float) -> float:
    """Convert 8-bit sRGB channel [0..255] to linear light float [0..1]."""
    c = c_byte / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb_channel(c_lin: float) -> int:
    """Convert linear light float [0..1] to 8-bit sRGB channel [0..255]."""
    c_lin = max(0.0, min(1.0, c_lin))
    if c_lin <= 0.0031308:
        c = c_lin * 12.92
    else:
        c = 1.055 * (c_lin ** (1.0 / 2.4)) - 0.055
    return int(round(max(0.0, min(1.0, c)) * 255.0))


def srgb_to_oklch(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """
    Convert sRGB (r, g, b in [0..255]) to OKLCH (L in [0..1], C in [0..], h in [0..360)).
    Uses the Björn Ottosson Oklab color model.
    """
    r_lin = srgb_channel_to_linear(r)
    g_lin = srgb_channel_to_linear(g)
    b_lin = srgb_channel_to_linear(b)

    # Convert linear sRGB to LMS cone space
    l = 0.4122214708 * r_lin + 0.5363325363 * g_lin + 0.0514459929 * b_lin
    m = 0.2119034982 * r_lin + 0.6806995451 * g_lin + 0.1073969566 * b_lin
    s = 0.0883024619 * r_lin + 0.2817188376 * g_lin + 0.6299787005 * b_lin

    # Non-linear LMS
    l_ = (l ** (1.0 / 3.0)) if l > 0.0 else 0.0
    m_ = (m ** (1.0 / 3.0)) if m > 0.0 else 0.0
    s_ = (s ** (1.0 / 3.0)) if s > 0.0 else 0.0

    # LMS to Oklab (L, a, b)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b_lab = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_

    # Oklab to OKLCH (L, C, h)
    C = math.sqrt(a * a + b_lab * b_lab)
    h_rad = math.atan2(b_lab, a)
    h_deg = (h_rad * 180.0 / math.pi) % 360.0

    return L, C, h_deg


def hex_to_oklch(hex_str: str) -> Tuple[float, float, float]:
    """Convert hex color string directly to OKLCH (L, C, h)."""
    r, g, b = hex_to_rgb(hex_str)
    return srgb_to_oklch(r, g, b)


def relative_luminance(r: int, g: int, b: int) -> float:
    """Calculate WCAG 2.1 relative luminance Y in [0..1]."""
    r_lin = srgb_channel_to_linear(r)
    g_lin = srgb_channel_to_linear(g)
    b_lin = srgb_channel_to_linear(b)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def wcag_contrast_ratio(color_a: str, color_b: str) -> float:
    """Calculate WCAG 2.1 contrast ratio between two hex/rgb colors [1.0 .. 21.0]."""
    rgb_a = parse_color_to_rgb(color_a)
    rgb_b = parse_color_to_rgb(color_b)
    if rgb_a is None or rgb_b is None:
        return 1.0

    l1 = relative_luminance(*rgb_a)
    l2 = relative_luminance(*rgb_b)

    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def grayscale_luminance(r: int, g: int, b: int) -> float:
    """Standard ITU-R BT.601 grayscale perceptual luminance: 0.299*R + 0.587*G + 0.114*B in [0..255]."""
    return 0.299 * r + 0.587 * g + 0.114 * b


def is_chroma_excessive(color_str: str, max_chroma: float = 0.22) -> bool:
    """Return True if OKLCH Chroma exceeds ceiling, indicating piercing glare/fluorescence."""
    rgb = parse_color_to_rgb(color_str)
    if rgb is None:
        return False
    _, C, _ = srgb_to_oklch(*rgb)
    return C > max_chroma


def is_neutral(color_str: str, max_chroma: float = 0.02) -> bool:
    """Return True if color is considered neutral gray/black/white (Chroma <= 0.02)."""
    rgb = parse_color_to_rgb(color_str)
    if rgb is None:
        return False
    _, C, _ = srgb_to_oklch(*rgb)
    return C <= max_chroma
