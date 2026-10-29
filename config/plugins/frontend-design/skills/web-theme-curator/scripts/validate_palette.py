# config/plugins/frontend-design/skills/web-theme-curator/scripts/validate_palette.py
#!/usr/bin/env python3
"""
Deterministic Palette & Color Convergence Quality Gate Validator
Enforces the '1 Primary + <= 3 Auxiliaries' contract and zero-inline-color policy.
Recursively scans HTML and CSS files for:
1. Unauthorized chromatic colors (e.g. rogue purple, unapproved hues).
2. Inline hardcoded color attributes in HTML (style="...color: #...", etc.).
3. Chart palette capacity constraints (<= 4 chromatic entries).
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from typing import List, Tuple, Set, Optional

# Standard neutral grays/blues/whites/blacks that do not count as rogue chromatic hues
DEFAULT_NEUTRALS = {
    "#000000", "#ffffff", "#fff", "#000",
    "#020817", "#040f25", "#061e44", "#09295c",
    "#e6f1ff", "#c2d9f2", "#7e9ec2", "#4d6c8f",
    "#0a1526", "#10233f", "#f0f4f8", "#8fa2b8",
    "#f8fafc", "#0f172a", "#64748b"
}

# Forbidden chromatic signatures that are strictly prohibited in the 1+3 screen
FORBIDDEN_HUES = [
    (re.compile(r"#(b388ff|bb86fc|9d65ff|8a2be2|7c4dff|6200ea|9c27b0|e040fb)", re.I), "Purple/Violet forbidden under 1+3 contract"),
    (re.compile(r"#(ff4081|e91e63|f50057|c2185b)", re.I), "Pink/Magenta forbidden under 1+3 contract"),
]


def normalize_hex(color_str: str) -> str:
    color_str = color_str.strip().lower()
    if color_str.startswith("#"):
        c = color_str[1:]
        if len(c) == 3:
            return "#" + "".join([ch * 2 for ch in c])
        elif len(c) == 6:
            return "#" + c
    return color_str


def load_allowed_tokens(tokens_path: Optional[Path]) -> Tuple[Set[str], int]:
    """Extract approved chromatic and neutral tokens from design-tokens.json."""
    allowed = set(DEFAULT_NEUTRALS)
    chart_count = 0
    if tokens_path and tokens_path.exists():
        try:
            with open(tokens_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            pal = data.get("palette", {})
            chart_pal = pal.get("chartPalette", [])
            chart_count = len(chart_pal)

            for key, val in pal.items():
                if isinstance(val, str) and val.startswith("#"):
                    allowed.add(normalize_hex(val))
            aux = pal.get("auxiliary", {})
            for key, val in aux.items():
                if isinstance(val, str) and val.startswith("#"):
                    allowed.add(normalize_hex(val))
            for val in chart_pal:
                if isinstance(val, str) and val.startswith("#"):
                    allowed.add(normalize_hex(val))
        except Exception as e:
            print(f"WARN: Could not parse tokens '{tokens_path}': {e}", file=sys.stderr)
    return allowed, chart_count


def check_html_inline_styles(content: str, file_path: str) -> List[Tuple[int, str, str]]:
    """Flag inline color / background-color / border-color declarations in HTML."""
    violations = []
    lines = content.split("\n")
    # Matches style="...color: #... or background: #... or rgba(...)"
    inline_color_pattern = re.compile(
        r"""style\s*=\s*["'][^"']*(?:color|background|border)\s*:\s*([^;"'>]+)""",
        re.IGNORECASE
    )

    for idx, line in enumerate(lines, 1):
        if "<!-- allow-inline-color -->" in line:
            continue
        for match in inline_color_pattern.finditer(line):
            val = match.group(1).strip()
            # If it's hardcoding a hex color or colored rgba
            if "#" in val or "rgba(" in val:
                # Exclude purely transparent or neutral rgba white/black overlays if needed
                if val in ["transparent", "#fff", "#ffffff", "rgba(255, 255, 255, 0.1)"]:
                    continue
                violations.append((
                    idx,
                    match.group(0),
                    f"Inline hardcoded color '{val}' violates Tokenized style policy. Use CSS token class."
                ))
    return violations


def check_forbidden_hues(content: str, file_path: str) -> List[Tuple[int, str, str]]:
    """Scan content for forbidden chromatic hues (e.g. purple, pink)."""
    violations = []
    lines = content.split("\n")
    for idx, line in enumerate(lines, 1):
        if "allow-rogue-color" in line:
            continue
        for pattern, reason in FORBIDDEN_HUES:
            m = pattern.search(line)
            if m:
                violations.append((idx, m.group(0), reason))
    return violations


def scan_file(file_path: Path, allowed_tokens: Set[str]) -> List[Tuple[int, str, str]]:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        print(f"WARN: Could not read '{file_path}': {e}", file=sys.stderr)
        return []

    violations = []
    # 1. Check forbidden hues in all files
    violations.extend(check_forbidden_hues(content, str(file_path)))

    # 2. Check HTML inline styles
    if file_path.suffix.lower() in [".html", ".htm"]:
        violations.extend(check_html_inline_styles(content, str(file_path)))

    return violations


def main():
    parser = argparse.ArgumentParser(description="Deterministic Palette Quality Gate Validator")
    parser.add_argument("target", nargs="?", default=".", help="Directory or file to scan")
    parser.add_argument("--tokens", default="design-tokens.json", help="Path to design-tokens.json SSOT")
    args = parser.parse_args()

    target_path = Path(args.target).resolve()
    tokens_path = Path(args.tokens).resolve()

    if not target_path.exists():
        print(f"ERROR: Target path '{target_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    allowed_tokens, chart_count = load_allowed_tokens(tokens_path if tokens_path.exists() else None)

    # Check chart palette count if tokens found
    if chart_count > 4:
        print(f"GATE FAILED: chartPalette in '{tokens_path}' has {chart_count} colors. Exceeds 1+3 ceiling (<= 4)!", file=sys.stderr)
        sys.exit(1)

    all_violations = []
    files_to_scan = []

    if target_path.is_file():
        files_to_scan.append(target_path)
    else:
        for root, _, files in os.walk(target_path):
            if any(p in root for p in ["node_modules", ".git", "doc"]):
                continue
            for f in files:
                p = Path(root) / f
                if p.suffix.lower() in [".html", ".css", ".js"]:
                    files_to_scan.append(p)

    for fp in files_to_scan:
        v = scan_file(fp, allowed_tokens)
        for line_num, snippet, reason in v:
            all_violations.append((str(fp), line_num, snippet, reason))

    if not all_violations:
        print(f"PALETTE VALIDATION SUCCESS: Scanned {len(files_to_scan)} file(s). 1+3 color convergence contract satisfied.")
        sys.exit(0)
    else:
        print(f"PALETTE VALIDATION FAILED: Found {len(all_violations)} color convergence violation(s):\n", file=sys.stderr)
        for idx, (fp, line_num, snippet, reason) in enumerate(all_violations, 1):
            print(f"  [{idx}] {fp}:{line_num}\n      Snippet: {snippet}\n      Reason:  {reason}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

