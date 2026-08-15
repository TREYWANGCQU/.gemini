# -*- coding: utf-8 -*-
# scripts/publisher.py
import os
import sys
import re
import json
import argparse
import subprocess
import tempfile
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

NAMESPACES = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
}

def preprocess_typst_content(typst_code: str) -> str:
    lines = typst_code.splitlines()
    clean_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#import ') or stripped.startswith('#show '):
            continue
        if stripped.startswith('#set page(') or stripped.startswith('#set text('):
            continue
        clean_lines.append(line)
        
    return "\n".join(clean_lines)

def run_publisher(input_path: Path, output_path: Path, template_path: Path = None) -> dict:
    diagnostics = []
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not input_path.exists():
        return {
            "status": "FAIL",
            "diagnostics": [f"Input file not found: {input_path}"],
            "output_files": []
        }
        
    typ_content = input_path.read_text(encoding='utf-8')
    cleaned_typ = preprocess_typst_content(typ_content)
    
    ref_arg = []
    if template_path and template_path.exists():
        ref_arg = [f"--reference-doc={template_path}"]
        diagnostics.append(f"Using explicit template: {template_path}")
    else:
        global_ref = Path.home() / ".gemini" / "config" / "templates" / "enterprise-reference.docx"
        if global_ref.exists():
            ref_arg = [f"--reference-doc={global_ref}"]
            diagnostics.append(f"Using global template: {global_ref}")
        elif Path("reference.docx").exists():
            ref_arg = ["--reference-doc=reference.docx"]
            diagnostics.append("Using workspace reference.docx")
            
    with tempfile.NamedTemporaryFile(suffix=".typ", delete=False, mode='w', encoding='utf-8') as tmp_typ:
        tmp_typ.write(cleaned_typ)
        tmp_typ_path = tmp_typ.name
        
    try:
        cmd = [
            "pandoc",
            tmp_typ_path,
            "-f", "typst",
            "-t", "docx",
            "-o", str(output_path)
        ] + ref_arg
        
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        if proc.returncode != 0:
            return {
                "status": "FAIL",
                "diagnostics": [f"Pandoc error: {proc.stderr.strip()}"],
                "output_files": []
            }
            
        diagnostics.append(f"Successfully generated DOCX at {output_path}")
        
        if output_path.exists():
            with zipfile.ZipFile(output_path, 'r') as z:
                if "word/document.xml" in z.namelist():
                    doc_xml = z.read("word/document.xml")
                    tree = ET.fromstring(doc_xml)
                    headings = tree.findall('.//w:pStyle[@w:val="Heading1"]', NAMESPACES) +                                tree.findall('.//w:pStyle[@w:val="Heading2"]', NAMESPACES) +                                tree.findall('.//w:pStyle[@w:val="Heading3"]', NAMESPACES) +                                tree.findall('.//w:pStyle[@w:val="heading 1"]', NAMESPACES) +                                tree.findall('.//w:pStyle[@w:val="heading 2"]', NAMESPACES)
                    tables = tree.findall('.//w:tbl', NAMESPACES)
                    diagnostics.append(f"Quality Audit: Mapped {len(headings)} outline headings, {len(tables)} tables.")
                    
        return {
            "status": "SUCCESS",
            "diagnostics": diagnostics,
            "output_files": [str(output_path)]
        }
    finally:
        if os.path.exists(tmp_typ_path):
            os.remove(tmp_typ_path)

def main():
    parser = argparse.ArgumentParser(description="Typst to Word High-Fidelity Publisher")
    parser.add_argument("--input", "-i", required=True, help="Path to input .typ file")
    parser.add_argument("--output", "-o", required=True, help="Path to output .docx file")
    parser.add_argument("--template", "-t", default=None, help="Path to reference .docx template")
    
    args = parser.parse_args()
    result = run_publisher(Path(args.input), Path(args.output), Path(args.template) if args.template else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "FAIL":
        sys.exit(1)

if __name__ == "__main__":
    main()
