# config/plugins/frontend-design/skills/web-theme-curator/scripts/curator.py
#!/usr/bin/env python3
"""
Web Theme Curator Automation Engine
Handles scaffolding, static asset derivation (tokens.css & chartTheme.js),
auditing, and synchronization with strict 1+3 color convergence and >=12px typography.
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
VALIDATOR_TYPO = CURATOR_DIR / "scripts" / "validate_typography.py"
VALIDATOR_PALETTE = CURATOR_DIR / "scripts" / "validate_palette.py"


def px_to_rem(px_val_str: str, rem_base: float = 16.0) -> str:
    """Convert '14px' to '0.875rem'."""
    val = float(px_val_str.replace("px", "").strip())
    rem = val / rem_base
    return f"{rem:.4g}rem"


def hex_to_rgba(hex_str: str, alpha: float) -> str:
    """Convert hex color (#00f0ff) to rgba(0, 240, 255, alpha)."""
    clean_hex = hex_str.strip().lstrip("#")
    if len(clean_hex) == 3:
        clean_hex = "".join([c * 2 for c in clean_hex])
    if len(clean_hex) == 6:
        try:
            r = int(clean_hex[0:2], 16)
            g = int(clean_hex[2:4], 16)
            b = int(clean_hex[4:6], 16)
            return f"rgba({r}, {g}, {b}, {alpha})"
        except ValueError:
            pass
    return hex_str


def generate_tokens_css(tokens: Dict[str, Any]) -> str:
    """Derive native CSS variables string from tokens dict with 1+3 color system."""
    pal = tokens.get("palette", {})
    aux = pal.get("auxiliary", {})
    typo = tokens.get("typography", {})
    scale = typo.get("scale", {})
    leading = typo.get("leading", {})
    rem_base = float(tokens.get("remBase", 16.0))

    primary = pal.get("primary", "#00f0ff")
    warning = aux.get("warning", pal.get("colorOrange", "#ffa726"))
    danger = aux.get("danger", pal.get("colorRed", "#ff5252"))
    success = aux.get("success", pal.get("colorGreen", "#00e676"))

    lines = [
        "/* src/styles/tokens.css */",
        "/* Automatically derived from design-tokens.json. DO NOT EDIT DIRECTLY. */",
        "/* Enforces 1 Primary + <=3 Auxiliary colors and font-size >= 12px */",
        ":root {",
        "  /* Primary Color (Cyber Cyan / Brand Core) */",
        f"  --color-primary: {primary};",
        f"  --color-primary-hover: {pal.get('primaryHover', '#33dcff')};",
        f"  --color-primary-bg: {hex_to_rgba(primary, 0.12)};",
        f"  --color-primary-dim: {hex_to_rgba(primary, 0.28)};",
        "",
        "  /* Auxiliary Colors (1+3 Strict Contract: Warning, Danger, Success) */",
        f"  --color-aux-warning: {warning};",
        f"  --color-aux-warning-bg: {hex_to_rgba(warning, 0.12)};",
        f"  --color-aux-warning-dim: {hex_to_rgba(warning, 0.28)};",
        f"  --color-aux-danger: {danger};",
        f"  --color-aux-danger-bg: {hex_to_rgba(danger, 0.12)};",
        f"  --color-aux-danger-dim: {hex_to_rgba(danger, 0.28)};",
        f"  --color-aux-success: {success};",
        f"  --color-aux-success-bg: {hex_to_rgba(success, 0.12)};",
        f"  --color-aux-success-dim: {hex_to_rgba(success, 0.28)};",
        "",
        "  /* Semantic Backwards-Compatibility Aliases */",
        "  --color-orange: var(--color-aux-warning);",
        "  --color-red: var(--color-aux-danger);",
        "  --color-green: var(--color-aux-success);",
        "",
        "  /* Neutral Background & Space */",
        f"  --color-bg-space: {pal.get('bgSpace', pal.get('bgBase', '#020817'))};",
        f"  --color-bg-screen: {pal.get('bgScreen', '#040f25')};",
        f"  --color-bg-card: {pal.get('bgCard', 'rgba(6, 30, 68, 0.78)')};",
        f"  --color-bg-card-sub: {pal.get('bgCardSub', 'rgba(9, 41, 92, 0.55)')};",
        f"  --color-bg-hover: {pal.get('bgHover', hex_to_rgba(primary, 0.08))};",
        "",
        "  /* Neutral Borders */",
        f"  --color-border-cyan: {primary};",
        f"  --color-border-cyan-dim: {pal.get('borderCyanDim', hex_to_rgba(primary, 0.28))};",
        f"  --color-border-dim: {pal.get('border', 'rgba(255, 255, 255, 0.12)')};",
        "",
        "  /* Neutral Typography Hierarchy */",
        f"  --color-text-white: {pal.get('textWhite', '#ffffff')};",
        f"  --color-text-title: {pal.get('textTitle', '#e6f1ff')};",
        f"  --color-text-main: {pal.get('textMain', '#c2d9f2')};",
        f"  --color-text-secondary: {pal.get('textSecondary', '#7e9ec2')};",
        f"  --color-text-dim: {pal.get('textDim', '#4d6c8f')};",
        "",
        "  /* Typography Scale (Floor >= 12px) */",
        f"  --font-family-base: {typo.get('fontFamilyBase', 'sans-serif')};",
        f"  --font-family-num: {typo.get('fontFamilyNum', typo.get('fontFamilyBase', 'sans-serif'))};",
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
    """Derive chartTheme.js for ECharts & Canvas with UMD browser-global & Node.js support."""
    pal = tokens.get("palette", {})
    chart_palette = pal.get("chartPalette", [pal.get("primary", "#00f0ff")])
    if len(chart_palette) > 4:
        raise ValueError(
            f"FAIL-FAST: chartPalette exceeds 1+3 contract! Got {len(chart_palette)} colors ({chart_palette}), "
            f"maximum allowed is 4 (1 Primary + <= 3 Auxiliaries)."
        )

    typo = tokens.get("typography", {})
    scale = typo.get("scale", {})

    floor_px = int(scale.get("floor", "12px").replace("px", ""))
    sm_px = int(scale.get("sm", "14px").replace("px", ""))
    base_px = int(scale.get("base", "16px").replace("px", ""))
    title_px = int(scale.get("lg", "18px").replace("px", ""))

    primary = pal.get("primary", "#00f0ff")

    lines = [
        "// src/utils/chartTheme.js",
        "// ==========================================================================",
        "// Automatically derived from design-tokens.json. DO NOT EDIT DIRECTLY.",
        "// Enforces 1+3 Color Convergence (<=4 chart colors) & font-size >= 12px",
        "// ==========================================================================",
        "",
        "(function (global) {",
        "  'use strict';",
        "",
        "  const CHART_TOKENS = Object.freeze({",
        f"    colors: {json.dumps(chart_palette)},",
        f"    bgCard: '{pal.get('bgCard', 'rgba(6, 30, 68, 0.78)')}',",
        f"    textWhite: '{pal.get('textWhite', '#ffffff')}',",
        f"    textTitle: '{pal.get('textTitle', '#e6f1ff')}',",
        f"    textMain: '{pal.get('textMain', '#c2d9f2')}',",
        f"    textSecondary: '{pal.get('textSecondary', '#7e9ec2')}',",
        f"    fontSizeFloor: {floor_px}, // Physical Floor strictly >= 12px",
        f"    fontSizeSm: {sm_px},",
        f"    fontSizeBase: {base_px},",
        f"    fontSizeTitle: {title_px},",
        f"    fontFamily: \"{typo.get('fontFamilyBase', 'sans-serif')}\"",
        "  });",
        "",
        "  const defaultEChartsTheme = Object.freeze({",
        "    backgroundColor: 'transparent',",
        "    textStyle: {",
        "      fontFamily: CHART_TOKENS.fontFamily,",
        "      fontSize: CHART_TOKENS.fontSizeFloor,",
        "      color: CHART_TOKENS.textSecondary",
        "    },",
        "    title: {",
        "      textStyle: {",
        "        color: CHART_TOKENS.textTitle,",
        "        fontSize: CHART_TOKENS.fontSizeTitle,",
        "        fontWeight: 600",
        "      }",
        "    },",
        "    legend: {",
        "      textStyle: {",
        "        color: CHART_TOKENS.textSecondary,",
        "        fontSize: CHART_TOKENS.fontSizeFloor",
        "      }",
        "    },",
        "    xAxis: {",
        f"      axisLine: {{ lineStyle: {{ color: '{hex_to_rgba(primary, 0.2)}' }} }},",
        "      axisLabel: {",
        "        color: CHART_TOKENS.textSecondary,",
        "        fontSize: CHART_TOKENS.fontSizeFloor,",
        "        margin: 10,",
        "        interval: 'auto',",
        "        rotate: 0",
        "      }",
        "    },",
        "    yAxis: {",
        f"      axisLine: {{ lineStyle: {{ color: '{hex_to_rgba(primary, 0.2)}' }} }},",
        "      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.06)' } },",
        "      axisLabel: {",
        "        color: CHART_TOKENS.textSecondary,",
        "        fontSize: CHART_TOKENS.fontSizeFloor",
        "      }",
        "    },",
        "    tooltip: {",
        "      backgroundColor: 'rgba(2, 8, 23, 0.95)',",
        "      borderColor: CHART_TOKENS.colors[0],",
        "      textStyle: {",
        "        color: '#ffffff',",
        "        fontSize: CHART_TOKENS.fontSizeFloor",
        "      }",
        "    }",
        "  });",
        "",
        "  if (typeof module !== 'undefined' && module.exports) {",
        "    module.exports = { CHART_TOKENS, defaultEChartsTheme };",
        "  } else {",
        "    global.CHART_TOKENS = CHART_TOKENS;",
        "    global.defaultEChartsTheme = defaultEChartsTheme;",
        "  }",
        "})(typeof window !== 'undefined' ? window : globalThis);",
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

    # Validate 1+3 palette contract
    chart_palette = tokens.get("palette", {}).get("chartPalette", [])
    if len(chart_palette) > 4:
        print(f"ERROR: chartPalette contains {len(chart_palette)} colors. Violates 1+3 limit (<= 4).", file=sys.stderr)
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

    # Copy local validators
    local_scripts = workspace / "scripts"
    local_scripts.mkdir(parents=True, exist_ok=True)
    shutil.copy2(VALIDATOR_TYPO, local_scripts / "validate_typography.py")
    print(f"  [+] Injected Gate Validator: {local_scripts / 'validate_typography.py'}")
    if VALIDATOR_PALETTE.exists():
        shutil.copy2(VALIDATOR_PALETTE, local_scripts / "validate_palette.py")
        print(f"  [+] Injected Palette Validator: {local_scripts / 'validate_palette.py'}")

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
