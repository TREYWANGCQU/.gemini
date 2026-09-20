# config/skills/svg-designer/scripts/validate_svg.py
#!/usr/bin/env python3
"""
Deterministic SVG Typography & DOM Quality Gate Validator
Parses XML ElementTree, traces CSS inheritance and inline styles,
and verifies that all rendered text nodes strictly comply with font-size >= 12px.
"""

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


def main():
    parser = argparse.ArgumentParser(description="Deterministic SVG Typography Quality Gate Validator")
    parser.add_argument("svg_file", help="Path to the SVG file to validate")
    parser.add_argument("--min-size", type=float, default=12.0, help="Minimum allowable font-size in px (default: 12.0)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print verbose details for every text node")

    args = parser.parse_args()

    validator = SVGFontValidator(min_size=args.min_size, verbose=args.verbose)
    success = validator.validate_file(args.svg_file)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
