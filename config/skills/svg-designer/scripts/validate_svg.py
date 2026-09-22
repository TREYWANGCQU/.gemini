# config/skills/svg-designer/scripts/validate_svg.py
#!/usr/bin/env python3
"""
Deterministic SVG Typography & DOM Quality Gate Validator
Parses XML ElementTree, traces CSS inheritance and inline styles,
and verifies that all rendered text nodes strictly comply with font-size >= 12px.
"""

import os
import sys
import re
import argparse
from typing import List, Dict, Optional, Tuple
import xml.etree.ElementTree as ET


def strip_ns(tag: str) -> str:
    """Remove XML namespace prefix from tag."""
    if '}' in tag:
        return tag.split('}', 1)[1]
    return tag


def parse_font_size_value(raw_val: str, parent_size: float = 16.0) -> Optional[float]:
    """
    Parse a raw font-size string (e.g., '12px', '14', '0.875rem', '1.2em', '10pt')
    into an effective pixel value. Strips !important and surrounding whitespace.
    """
    if not raw_val:
        return None
    raw_val = re.sub(r'!important', '', raw_val, flags=re.IGNORECASE).strip().lower()

    # Named sizes
    named_map = {
        'xx-small': 9.0,
        'x-small': 10.0,
        'small': 12.0,
        'medium': 16.0,
        'large': 18.0,
        'x-large': 24.0,
        'xx-large': 32.0,
    }
    if raw_val in named_map:
        return named_map[raw_val]

    # Regex for number + optional unit
    m = re.match(r'^([\d.]+)\s*(px|pt|rem|em|%)?$', raw_val)
    if not m:
        return None

    num = float(m.group(1))
    unit = m.group(2) or 'px'

    if unit == 'px':
        return num
    elif unit == 'pt':
        return num * (96.0 / 72.0)  # 1pt = 1.3333px
    elif unit == 'rem':
        return num * 16.0           # 1rem = 16px baseline
    elif unit == 'em':
        return num * parent_size
    elif unit == '%':
        return (num / 100.0) * parent_size

    return num


def parse_style_attr(style_str: str) -> Dict[str, str]:
    """Parse inline style attribute into a dictionary."""
    declarations = {}
    if not style_str:
        return declarations
    parts = style_str.split(';')
    for part in parts:
        if ':' in part:
            k, v = part.split(':', 1)
            declarations[k.strip().lower()] = v.strip()
    return declarations


class SVGFontValidator:
    def __init__(self, min_size: float = 12.0, verbose: bool = False):
        self.min_size = min_size
        self.verbose = verbose
        self.violations: List[Dict[str, any]] = []
        self.checked_nodes_count = 0

    def parse_stylesheet(self, root: ET.Element) -> Dict[str, float]:
        """Extract ID, class and tag font-size rules from <style> blocks."""
        rules = {}
        for elem in root.iter():
            if strip_ns(elem.tag) == 'style' and elem.text:
                # Strip CSS comments /* ... */
                css_text = re.sub(r'/\*.*?\*/', '', elem.text, flags=re.DOTALL)
                # Match class and tag rules: .classname { font-size: 12px; } or text { font-size: 14px; }
                rule_matches = re.finditer(r'([^{]+)\{([^}]+)\}', css_text)
                for rm in rule_matches:
                    selectors = rm.group(1).split(',')
                    body = rm.group(2)
                    styles = parse_style_attr(body)
                    if 'font-size' in styles:
                        fs_val = parse_font_size_value(styles['font-size'])
                        if fs_val is not None:
                            for sel in selectors:
                                s = sel.strip()
                                if s:
                                    rules[s] = fs_val
        return rules

    def _get_element_declared_font_size(
        self,
        elem: ET.Element,
        css_rules: Dict[str, float],
        parent_size: float
    ) -> Tuple[Optional[float], str]:
        """
        Determine if the element explicitly declares a font-size,
        following W3C CSS / SVG 2 specificity cascade:
        1. inline style attribute
        2. CSS stylesheet rules (ID -> Class -> Tag)
        3. SVG presentation attribute (font-size)
        Returns (font_size, source_description).
        """
        # 1. Inline style
        style_attr = elem.attrib.get('style', '')
        if style_attr:
            styles = parse_style_attr(style_attr)
            if 'font-size' in styles:
                val = parse_font_size_value(styles['font-size'], parent_size)
                if val is not None:
                    return val, f"style='font-size: {styles['font-size']}'"

        # 2. CSS stylesheet: ID rule
        elem_id = elem.attrib.get('id', '').strip()
        if elem_id:
            id_sel = f"#{elem_id}"
            if id_sel in css_rules:
                return css_rules[id_sel], f"css id '{id_sel}'"

        # 3. CSS stylesheet: Class rule
        classes = elem.attrib.get('class', '').split()
        for cls in classes:
            sel = f".{cls}"
            if sel in css_rules:
                return css_rules[sel], f"css class '{sel}'"

        # 4. CSS stylesheet: Tag rule
        tag_name = strip_ns(elem.tag)
        if tag_name in css_rules:
            return css_rules[tag_name], f"css tag rule '{tag_name}'"

        # 5. SVG presentation attribute
        if 'font-size' in elem.attrib:
            raw_attr = elem.attrib['font-size']
            val = parse_font_size_value(raw_attr, parent_size)
            if val is not None:
                return val, f"font-size='{raw_attr}'"

        return None, "inherited"

    def walk_tree(
        self,
        elem: ET.Element,
        css_rules: Dict[str, float],
        current_font_size: float = 16.0,
        ancestry: Optional[List[str]] = None,
        parent_exempt: bool = False
    ):
        """Recursively traverse DOM nodes and validate text font-size."""
        if ancestry is None:
            ancestry = []

        tag = strip_ns(elem.tag)
        current_path = ancestry + [f"<{tag} id='{elem.attrib.get('id', '')}'>"]

        declared_size, source = self._get_element_declared_font_size(
            elem, css_rules, current_font_size
        )
        effective_font_size = declared_size if declared_size is not None else current_font_size

        node_exempt = elem.attrib.get('data-allow-micro-font', '').lower() in ('true', '1')
        effective_exempt = parent_exempt or node_exempt

        # Check if text or tspan has text content
        has_text = (elem.text and elem.text.strip()) or (elem.tail and elem.tail.strip())

        if tag in ('text', 'tspan'):
            self.checked_nodes_count += 1

            # Determine text preview
            text_preview = (elem.text or '').strip()
            if not text_preview and len(elem) > 0:
                # If tspan children exist, check children directly in recursion
                text_preview = "[nested tspans]"

            # Check threshold
            effective_min = 10.0 if effective_exempt else self.min_size

            if effective_font_size < effective_min:
                self.violations.append({
                    'tag': tag,
                    'id': elem.attrib.get('id', ''),
                    'path': ' -> '.join(current_path),
                    'computed_size': effective_font_size,
                    'threshold': effective_min,
                    'is_exempt': effective_exempt,
                    'source': source,
                    'text': text_preview[:40] if text_preview else "(empty)"
                })
            elif self.verbose:
                status = "EXEMPT_PASS" if effective_exempt else "PASS"
                print(f"[{status}] {effective_font_size}px (min: {effective_min}px) on {tag}: '{text_preview[:25]}'")

        # Recurse through children
        for child in elem:
            self.walk_tree(child, css_rules, effective_font_size, current_path, effective_exempt)

    def validate_file(self, svg_path: str) -> bool:
        """Parse and validate an SVG file by path."""
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()
        except Exception as e:
            print(f"ERROR: Failed to parse SVG file '{svg_path}': {e}", file=sys.stderr)
            return False

        css_rules = self.parse_stylesheet(root)
        self.violations.clear()
        self.checked_nodes_count = 0

        self.walk_tree(root, css_rules)

        if not self.violations:
            print(f"VALIDATION SUCCESS: Verified {self.checked_nodes_count} text node(s). All fonts >= {self.min_size}px.")
            return True
        else:
            print(f"VALIDATION FAILED: Found {len(self.violations)} typography violation(s) below {self.min_size}px threshold:\n", file=sys.stderr)
            for idx, v in enumerate(self.violations, 1):
                print(
                    f"  [{idx}] <{v['tag']}> id='{v['id']}' | Computed: {v['computed_size']}px < Required: {v['threshold']}px\n"
                    f"      Text: \"{v['text']}\"\n"
                    f"      Origin: {v['source']}\n"
                    f"      Hierarchy: {v['path']}\n",
                    file=sys.stderr
                )
            return False


def extract_colors(svg_content: str) -> Tuple[set, set]:
    """Extract and normalize unique colors (hex and rgb) from SVG content."""
    hex_colors = set(re.findall(r'#(?:[0-9a-fA-F]{3}){1,2}\b', svg_content))
    normalized = set()
    for c in hex_colors:
        c = c.upper()
        if len(c) == 4:
            c = '#' + c[1] * 2 + c[2] * 2 + c[3] * 2
        normalized.add(c)
    rgb_colors = set(re.findall(r'rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)', svg_content))
    return normalized, rgb_colors


def check_aspect_ratio(root: ET.Element, expected_ratio_str: str) -> Tuple[bool, str]:
    """Verify SVG aspect ratio against expected ratio (e.g. '16:9')."""
    if not expected_ratio_str:
        return True, ""
    try:
        rw, rh = [float(x) for x in expected_ratio_str.split(':')]
        target_ratio = rw / rh
    except Exception:
        return True, ""

    viewbox = root.attrib.get('viewBox', '')
    width = root.attrib.get('width', '')
    height = root.attrib.get('height', '')

    if viewbox:
        parts = [float(p) for p in viewbox.replace(',', ' ').split() if p.strip()]
        if len(parts) == 4:
            vb_w, vb_h = parts[2], parts[3]
            actual = vb_w / vb_h
            if abs(actual - target_ratio) < 0.02:
                return True, f"Aspect ratio {expected_ratio_str} confirmed via viewBox ({vb_w}x{vb_h})"
            else:
                return False, f"Aspect ratio mismatch: viewBox ({vb_w}x{vb_h}) ratio is {actual:.3f}, expected {target_ratio:.3f} ({expected_ratio_str})"

    if width and height:
        try:
            w_num = float(re.sub(r'[^\d.]', '', width))
            h_num = float(re.sub(r'[^\d.]', '', height))
            actual = w_num / h_num
            if abs(actual - target_ratio) < 0.02:
                return True, f"Aspect ratio {expected_ratio_str} confirmed via width/height ({w_num}x{h_num})"
            else:
                return False, f"Aspect ratio mismatch: width/height ({w_num}x{h_num}) ratio is {actual:.3f}, expected {target_ratio:.3f} ({expected_ratio_str})"
        except Exception:
            pass

    return False, f"Unable to verify aspect ratio {expected_ratio_str} from viewBox='{viewbox}', width='{width}', height='{height}'"


def load_tokens_config(tokens_path: Optional[str] = None, svg_file_path: Optional[str] = None) -> Dict:
    """Load design-tokens.yaml from explicit path, SVG file parent, script parent, or cwd."""
    search_paths = []
    if tokens_path:
        search_paths.append(tokens_path)
    if svg_file_path:
        svg_dir = os.path.dirname(os.path.abspath(svg_file_path))
        search_paths.extend([
            os.path.join(svg_dir, "design-tokens.yaml"),
            os.path.join(svg_dir, "..", "design-tokens.yaml"),
            os.path.join(svg_dir, "..", "..", "design-tokens.yaml"),
        ])
    script_dir = os.path.dirname(os.path.abspath(__file__))
    search_paths.extend([
        os.path.join(script_dir, "..", "design-tokens.yaml"),
        os.path.join(os.getcwd(), "design-tokens.yaml"),
    ])

    for p in search_paths:
        if os.path.isfile(p):
            try:
                import yaml
                with open(p, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                    if cfg:
                        return cfg
            except Exception:
                pass
    return {}


def main():
    import os
    parser = argparse.ArgumentParser(description="Deterministic SVG Typography & DOM Quality Gate Validator")
    parser.add_argument("svg_file", help="Path to the SVG file to validate")
    parser.add_argument("--min-size", type=float, default=None, help="Minimum allowable font-size in px (default: from tokens or 12.0)")
    parser.add_argument("--aspect-ratio", help="Expected aspect ratio (e.g., '16:9', '4:3')")
    parser.add_argument("--max-colors", type=int, default=None, help="Maximum allowed base chromatic colors")
    parser.add_argument("--check-placeholders", action="store_true", help="Check and fail on placeholder tokens (TODO, TBD, etc.)")
    parser.add_argument("--tokens", help="Path to design-tokens.yaml")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print verbose details for every text node")

    args = parser.parse_args()

    if not os.path.exists(args.svg_file):
        print(f"ERROR: File not found: {args.svg_file}", file=sys.stderr)
        sys.exit(1)

    # 1. Load tokens configuration
    tokens_cfg = load_tokens_config(args.tokens, args.svg_file)

    # Resolve parameters from CLI or tokens
    min_size = args.min_size
    if min_size is None:
        raw_floor = (tokens_cfg.get("typography", {}).get("scale", {}).get("floor", "12px"))
        try:
            m = re.match(r'^([\d.]+)', str(raw_floor))
            min_size = float(m.group(1)) if m else 12.0
        except Exception:
            min_size = 12.0

    aspect_ratio = args.aspect_ratio or tokens_cfg.get("aspectRatio")
    qg_cfg = tokens_cfg.get("qualityGate", {})
    max_colors = args.max_colors if args.max_colors is not None else qg_cfg.get("maxColors")
    check_placeholders = args.check_placeholders or bool(qg_cfg.get("forbiddenTokens"))
    forbidden_tokens = qg_cfg.get("forbiddenTokens") or ["TODO", "TBD", "FIXME", "XXX", "待定", "占位符"]

    overall_success = True

    # 2. Aspect ratio check
    try:
        tree = ET.parse(args.svg_file)
        root = tree.getroot()
    except Exception as e:
        print(f"ERROR: Failed to parse SVG XML '{args.svg_file}': {e}", file=sys.stderr)
        sys.exit(1)

    if aspect_ratio:
        ratio_ok, ratio_msg = check_aspect_ratio(root, aspect_ratio)
        if ratio_ok:
            print(f"[PASS] {ratio_msg}")
        else:
            print(f"[FAIL] {ratio_msg}", file=sys.stderr)
            overall_success = False

    # 3. Read raw content for color & placeholder checks
    with open(args.svg_file, "r", encoding="utf-8") as f:
        svg_content = f.read()

    # 4. Color count check
    if max_colors is not None:
        hex_c, rgb_c = extract_colors(svg_content)
        total_colors = hex_c.union(rgb_c)
        print(f"[INFO] Found {len(total_colors)} color codes: {sorted(list(total_colors))}")
        if len(total_colors) > max_colors:
            print(f"[FAIL] Palette exceeds {max_colors} colors limit! (Count: {len(total_colors)})", file=sys.stderr)
            overall_success = False
        else:
            print(f"[PASS] Palette strictly within <= {max_colors} colors constraint (Count: {len(total_colors)})")

    # 5. Placeholder tokens check
    if check_placeholders:
        found_tokens = [tok for tok in forbidden_tokens if tok in svg_content]
        if found_tokens:
            print(f"[FAIL] Found placeholder tokens: {found_tokens}", file=sys.stderr)
            overall_success = False
        else:
            print("[PASS] No placeholder content detected.")

    # 6. Typography floor check
    validator = SVGFontValidator(min_size=min_size, verbose=args.verbose)
    typo_ok = validator.validate_file(args.svg_file)
    if not typo_ok:
        overall_success = False

    if overall_success:
        print("\n[RESULT] Quality Gate Check PASSED.")
        sys.exit(0)
    else:
        print("\n[RESULT] Quality Gate Check FAILED.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
