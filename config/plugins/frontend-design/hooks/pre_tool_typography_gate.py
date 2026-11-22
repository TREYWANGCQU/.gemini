# config/plugins/frontend-design/hooks/pre_tool_typography_gate.py
#!/usr/bin/env python3
"""
PreToolUse hook for frontend-design plugin.
Enforces the >= 12px typography readability floor on write_file / edit_file
for SVG and frontend style/script files before content is written to disk.
"""

import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "skills" / "web-theme-curator" / "scripts"))
sys.path.insert(0, str(PLUGIN_ROOT / "skills" / "svg-designer" / "scripts"))

from validate_svg import SVGFontValidator  # noqa: E402
from validate_typography import SUPPORTED_EXTS, check_css_content, check_js_content  # noqa: E402


def _allow() -> dict:
    return {"decision": "allow"}


def _deny(reason: str) -> dict:
    return {"decision": "deny", "reason": reason}


def validate_payload(payload: dict) -> dict:
    """Validate PreToolUse toolCall arguments against typography floor rules."""
    tool_call = payload.get("toolCall") or {}
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args") or {}

    target_path = args.get("Path") or args.get("path") or ""
    if not target_path:
        return _allow()

    ext = Path(target_path).suffix.lower()
    if tool_name == "write_file":
        content = args.get("Content") or args.get("content") or ""
    elif tool_name == "edit_file":
        content = args.get("Replacement") or args.get("replacement") or ""
    else:
        return _allow()

    if not content:
        return _allow()

    if ext in SUPPORTED_EXTS:
        violations = check_css_content(content, target_path)
        if ext not in {".css", ".scss", ".less"}:
            violations.extend(check_js_content(content, target_path))
        if violations:
            details = "; ".join(f"L{line}: {reason}" for line, _, reason in violations[:5])
            return _deny(f"Typography floor violation (<12px) in {target_path}: {details}")
        return _allow()

    if ext == ".svg" and tool_name == "write_file":
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".svg", encoding="utf-8", delete=False
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(buf):
                validator = SVGFontValidator(min_size=12.0, verbose=False)
                passed = validator.validate_file(tmp_path)

            if not passed:
                output = buf.getvalue().strip().splitlines()
                summary = " | ".join(output[-3:]) if output else "SVG font-size < 12px"
                return _deny(f"SVG typography floor violation in {target_path}: {summary}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    return _allow()


def main() -> None:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            print(json.dumps(_allow()))
            return
        payload = json.loads(raw)
        result = validate_payload(payload)
    except Exception as exc:
        print(f"[pre_tool_typography_gate] fallback allow due to error: {exc}", file=sys.stderr)
        result = _allow()

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
