# config/skills/web-theme-curator/scripts/validate_typography.py
#!/usr/bin/env python3
"""
Deterministic Typography Quality Gate Validator for Frontend Code
Recursively scans CSS, SCSS, LESS, Vue, JSX, TSX, JS, and TS files.
Flags any declared font-size < 12px or < 0.75rem.
Supports inline exemption: '/* allow-micro-font */' or '// allow-micro-font'.
"""

import os
import sys
import re
import argparse
from pathlib import Path
from typing import List, Tuple

SUPPORTED_EXTS = {".css", ".scss", ".less", ".vue", ".jsx", ".tsx", ".js", ".ts"}


def check_css_content(content: str, file_path: str) -> List[Tuple[int, str, str]]:
    """Scan CSS text for font-size < 12px or < 0.75rem."""
    violations = []
    lines = content.split("\n")
    for idx, raw_line in enumerate(lines, 1):
        if "allow-micro-font" in raw_line:
            continue
        # Strip comments
        line = re.sub(r"/\*.*?\*/", "", raw_line)
        # Match font-size: <val>
        m = re.search(r"font-size\s*:\s*([^;!}\n]+)", line, re.IGNORECASE)
        if m:
            val_str = m.group(1).strip().lower()
            px_m = re.match(r"^([0-9.]+)\s*px$", val_str)
            rem_m = re.match(r"^([0-9.]+)\s*rem$", val_str)
            if px_m and float(px_m.group(1)) < 12.0:
                violations.append((idx, m.group(0), f"{px_m.group(1)}px < 12px floor"))
            elif rem_m and float(rem_m.group(1)) < 0.75:
                computed_px = float(rem_m.group(1)) * 16.0
                violations.append((idx, m.group(0), f"{rem_m.group(1)}rem ({computed_px:.1f}px) < 12px floor"))
    return violations


def check_js_content(content: str, file_path: str) -> List[Tuple[int, str, str]]:
    """Scan JS/TS/Vue script for fontSize: < 12 or Canvas ctx.font < 12px."""
    violations = []
    lines = content.split("\n")
    for idx, raw_line in enumerate(lines, 1):
        if "allow-micro-font" in raw_line:
            continue
        line = raw_line
        if "//" in line:
            line = line.split("//", 1)[0]
        # Match fontSize: 10 or fontSize: '10px'
        for m in re.finditer(r"fontSize\s*:\s*([0-9.]+|['\"][0-9.]+(?:px)?['\"])", line):
            raw = m.group(1).strip("'\"")
            num_m = re.match(r"^([0-9.]+)", raw)
            if num_m and float(num_m.group(1)) < 12.0:
                violations.append((idx, m.group(0), f"fontSize: {num_m.group(1)} < 12px floor"))
        # Match Canvas .font = '10px ...'
        for m in re.finditer(r"\.font\s*=\s*['\"][^'\"]*?\b([0-9.]+)px\b", line):
            if float(m.group(1)) < 12.0:
                violations.append((idx, m.group(0), f"Canvas font: {m.group(1)}px < 12px floor"))
    return violations


def scan_file(file_path: Path) -> List[Tuple[int, str, str]]:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        print(f"WARN: Could not read '{file_path}': {e}", file=sys.stderr)
        return []

    ext = file_path.suffix.lower()
    if ext in {".css", ".scss", ".less"}:
        return check_css_content(content, str(file_path))
    else:
        # Check both CSS blocks and JS in Vue/JSX/TS
        v_css = check_css_content(content, str(file_path))
        v_js = check_js_content(content, str(file_path))
        return v_css + v_js


def main():
    parser = argparse.ArgumentParser(description="Deterministic Typography Quality Gate Validator")
    parser.add_argument("target", nargs="?", default=".", help="Directory or file to scan (default: current dir)")
    args = parser.parse_args()

    target_path = Path(args.target).resolve()
    if not target_path.exists():
        print(f"ERROR: Target path '{target_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    all_violations = []
    files_to_scan = []
    if target_path.is_file():
        files_to_scan.append(target_path)
    else:
        for root, _, files in os.walk(target_path):
            if any(p in root for p in ["node_modules", ".git", "dist", ".agents"]):
                continue
            for f in files:
                p = Path(root) / f
                if p.suffix.lower() in SUPPORTED_EXTS:
                    files_to_scan.append(p)

    for fp in files_to_scan:
        v = scan_file(fp)
        for line_num, code_snippet, reason in v:
            all_violations.append((str(fp), line_num, code_snippet, reason))

    if not all_violations:
        print(f"VALIDATION SUCCESS: Scanned {len(files_to_scan)} file(s). All fonts >= 12px.")
        sys.exit(0)
    else:
        print(f"VALIDATION FAILED: Found {len(all_violations)} typography violation(s) below 12px threshold:\n", file=sys.stderr)
        for idx, (fp, line_num, snippet, reason) in enumerate(all_violations, 1):
            print(f"  [{idx}] {fp}:{line_num}\n      Snippet: {snippet}\n      Reason:  {reason}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
