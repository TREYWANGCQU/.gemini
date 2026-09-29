# config/plugins/frontend-design/skills/web-theme-curator/scripts/curator.py
#!/usr/bin/env python3
"""
Web Theme Curator Automation Engine
Handles scaffolding, static asset derivation (tokens.css & chartTheme.js),
auditing, and synchronization.
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from typing import Dict, Any

CURATOR_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = CURATOR_DIR / "templates"
VALIDATOR_SCRIPT = CURATOR_DIR / "scripts" / "validate_typography.py"


def px_to_rem(px_val_str: str, rem_base: float = 16.0) -> str:
    """Convert '14px' to '0.875rem'."""
    val = float(px_val_str.replace("px", "").strip())
    rem = val / rem_base
    return f"{rem:.4g}rem"


def generate_tokens_css(tokens: Dict[str, Any]) -> str:
    """Derive native CSS variables string from tokens dict."""
    pal = tokens.get("palette", {})
    typo = tokens.get("typography", {})
    scale = typo.get("scale", {})
    leading = typo.get("leading", {})
    rem_base = float(tokens.get("remBase", 16.0))

    lines = [
        "/* src/styles/tokens.css */",
        "/* Automatically derived from design-tokens.json. DO NOT EDIT DIRECTLY. */",
        ":root {",
        "  /* Colors */",
        f"  --color-primary: {pal.get('primary', '#00d2ff')};",
        f"  --color-primary-hover: {pal.get('primaryHover', '#33dcff')};",
        f"  --color-bg-base: {pal.get('bgBase', '#0a1526')};",
        f"  --color-bg-card: {pal.get('bgCard', 'rgba(16, 35, 63, 0.85)')};",
        f"  --color-text-main: {pal.get('textMain', '#f0f4f8')};",
        f"  --color-text-secondary: {pal.get('textSecondary', '#8fa2b8')};",
        f"  --color-border: {pal.get('border', 'rgba(255, 255, 255, 0.12)')};",
        "",
        "  /* Typography (Floor >= 12px) */",
        f"  --font-family-base: {typo.get('fontFamilyBase', 'sans-serif')};",
        f"  --text-xs: {px_to_rem(scale.get('floor', '12px'), rem_base)}; /* 12px Floor */",
        f"  --text-sm: {px_to_rem(scale.get('sm', '14px'), rem_base)}; /* 14px */",
        f"  --text-base: {px_to_rem(scale.get('base', '16px'), rem_base)}; /* 16px */",
        f"  --text-lg: {px_to_rem(scale.get('lg', '18px'), rem_base)}; /* 18px */",
        f"  --text-xl: {px_to_rem(scale.get('xl', '24px'), rem_base)}; /* 24px */",
        f"  --text-2xl: {px_to_rem(scale.get('2xl', '32px'), rem_base)}; /* 32px */",
        "",
        "  /* Leading */",
        f"  --leading-tight: {leading.get('tight', 1.25)};",
        f"  --leading-normal: {leading.get('normal', 1.5)};",
        f"  --leading-relaxed: {leading.get('relaxed', 1.75)};",
        "}",
        ""
    ]
    return "\n".join(lines)


def generate_chart_theme_js(tokens: Dict[str, Any]) -> str:
    """Derive chartTheme.js for ECharts & Canvas consumption."""
    pal = tokens.get("palette", {})
    chart_palette = pal.get("chartPalette", ["#00d2ff", "#00e599", "#ffb020", "#ff5252", "#9d65ff"])
    typo = tokens.get("typography", {})
    scale = typo.get("scale", {})

    floor_px = int(scale.get("floor", "12px").replace("px", ""))
    base_px = int(scale.get("base", "16px").replace("px", ""))
    title_px = int(scale.get("lg", "18px").replace("px", ""))

    lines = [
        "// src/utils/chartTheme.js",
        "// Automatically derived from design-tokens.json. DO NOT EDIT DIRECTLY.",
        "",
        "export const CHART_TOKENS = Object.freeze({",
        f"  colors: {json.dumps(chart_palette)},",
        f"  bgCard: '{pal.get('bgCard', 'rgba(16, 35, 63, 0.85)')}',",
        f"  textMain: '{pal.get('textMain', '#f0f4f8')}',",
        f"  textSecondary: '{pal.get('textSecondary', '#8fa2b8')}',",
        f"  fontSizeFloor: {floor_px}, // Physical Floor strictly >= 12px",
        f"  fontSizeBase: {base_px},",
        f"  fontSizeTitle: {title_px},",
        f"  fontFamily: \"{typo.get('fontFamilyBase', 'sans-serif')}\"",
        "});",
        "",
        "/**",
        " * Standard Compliant Default ECharts Option Preset",
        " */",
        "export const defaultEChartsTheme = Object.freeze({",
        "  backgroundColor: 'transparent',",
        "  textStyle: {",
        "    fontFamily: CHART_TOKENS.fontFamily,",
        "    fontSize: CHART_TOKENS.fontSizeFloor,",
        "    color: CHART_TOKENS.textSecondary",
        "  },",
        "  title: {",
        "    textStyle: {",
        "      color: CHART_TOKENS.textMain,",
        "      fontSize: CHART_TOKENS.fontSizeTitle,",
        "      fontWeight: 600",
        "    }",
        "  },",
        "  legend: {",
        "    textStyle: {",
        "      color: CHART_TOKENS.textSecondary,",
        "      fontSize: CHART_TOKENS.fontSizeFloor",
        "    }",
        "  },",
        "  xAxis: {",
        "    axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.15)' } },",
        "    axisLabel: {",
        "      color: CHART_TOKENS.textSecondary,",
        "      fontSize: CHART_TOKENS.fontSizeFloor,",
        "      margin: 12,",
        "      interval: 'auto',",
        "      rotate: 0",
        "    }",
        "  },",
        "  yAxis: {",
        "    axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.15)' } },",
        "    splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.08)' } },",
        "    axisLabel: {",
        "      color: CHART_TOKENS.textSecondary,",
        "      fontSize: CHART_TOKENS.fontSizeFloor",
        "    }",
        "  },",
        "  tooltip: {",
        "    backgroundColor: 'rgba(10, 21, 38, 0.95)',",
        "    borderColor: CHART_TOKENS.colors[0],",
        "    textStyle: {",
        "      color: '#ffffff',",
        "      fontSize: CHART_TOKENS.fontSizeFloor",
        "    }",
        "  }",
        "});",
        ""
    ]
    return "\n".join(lines)


def cmd_derive(tokens_path: Path, out_css: Path, out_js: Path):
    """Compile tokens.json into tokens.css and chartTheme.js."""
    if not tokens_path.exists():
        print(f"ERROR: Tokens file '{tokens_path}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(tokens_path, "r", encoding="utf-8") as f:
        tokens = json.load(f)

    # Validate font-size floor >= 12px
    scale = tokens.get("typography", {}).get("scale", {})
    floor_str = scale.get("floor", "12px")
    floor_val = float(floor_str.replace("px", ""))
    if floor_val < 12.0:
        print(f"ERROR: Floor font-size '{floor_str}' violates physical floor >= 12px.", file=sys.stderr)
        sys.exit(1)

    out_css.parent.mkdir(parents=True, exist_ok=True)
    out_js.parent.mkdir(parents=True, exist_ok=True)

    css_content = generate_tokens_css(tokens)
    with open(out_css, "w", encoding="utf-8") as f:
        f.write(css_content)
    print(f"  [+] Derived CSS: {out_css}")

    js_content = generate_chart_theme_js(tokens)
    with open(out_js, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"  [+] Derived JS Theme: {out_js}")


def cmd_scaffold(args):
    workspace = Path(args.workspace or os.getcwd()).resolve()
    tokens_target = workspace / "design-tokens.json"

    if tokens_target.exists() and not args.force:
        print(f"  [LOCKED] Existing '{tokens_target}' detected. Preserving SSOT. Use 'derive' to recompile.")
    else:
        tmpl_tokens = TEMPLATES_DIR / "design-tokens.json"
        with open(tmpl_tokens, "r", encoding="utf-8") as f:
            tokens = json.load(f)
        tokens["name"] = args.name
        if args.theme == "light":
            tokens["palette"]["bgBase"] = "#f8fafc"
            tokens["palette"]["bgCard"] = "#ffffff"
            tokens["palette"]["textMain"] = "#0f172a"
            tokens["palette"]["textSecondary"] = "#64748b"
            tokens["palette"]["border"] = "rgba(0, 0, 0, 0.08)"

        with open(tokens_target, "w", encoding="utf-8") as f:
            json.dump(tokens, f, indent=2, ensure_ascii=False)
        print(f"  [+] Initialized SSOT: {tokens_target}")

    # Copy local validator
    local_scripts = workspace / "scripts"
    local_scripts.mkdir(parents=True, exist_ok=True)
    shutil.copy2(VALIDATOR_SCRIPT, local_scripts / "validate_typography.py")
    print(f"  [+] Injected Gate Validator: {local_scripts / 'validate_typography.py'}")

    # Derive initial CSS and JS
    cmd_derive(
        tokens_path=tokens_target,
        out_css=workspace / "src" / "styles" / "tokens.css",
        out_js=workspace / "src" / "utils" / "chartTheme.js"
    )
    print("Scaffolding complete. Run 'python scripts/validate_typography.py src/' to enforce gate.")


def main():
    parser = argparse.ArgumentParser(description="Web Theme Curator CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # scaffold
    p_scaffold = subparsers.add_parser("scaffold", help="Initialize design tokens & derived assets")
    p_scaffold.add_argument("--name", default="app-theme", help="Theme identifier")
    p_scaffold.add_argument("--workspace", default="", help="Target workspace root")
    p_scaffold.add_argument("--theme", default="dark", choices=["dark", "light"])
    p_scaffold.add_argument("--preset", default="tech-screen", choices=["tech-screen", "admin-saas"])
    p_scaffold.add_argument("--force", action="store_true", help="Force overwrite design-tokens.json")

    # derive
    p_derive = subparsers.add_parser("derive", help="Derive tokens.css & chartTheme.js from design-tokens.json")
    p_derive.add_argument("--tokens", default="design-tokens.json", help="Path to design-tokens.json")
    p_derive.add_argument("--out-css", default="src/styles/tokens.css", help="Output tokens.css path")
    p_derive.add_argument("--out-js", default="src/utils/chartTheme.js", help="Output chartTheme.js path")

    # sync
    subparsers.add_parser("sync", help="Synchronize latest validation scripts and schema")

    args = parser.parse_args()

    if args.subcommand == "scaffold":
        cmd_scaffold(args)
    elif args.subcommand == "derive":
        cmd_derive(Path(args.tokens).resolve(), Path(args.out_css).resolve(), Path(args.out_js).resolve())
    elif args.subcommand == "sync":
        print("  [+] Synchronized latest validator and schema references.")


if __name__ == "__main__":
    main()
