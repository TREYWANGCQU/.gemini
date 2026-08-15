# -*- coding: utf-8 -*-
# scripts/extract_reference_template.py
import os
import sys
import json
import shutil
import zipfile
import tempfile
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

NAMESPACES = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
}
for prefix, uri in NAMESPACES.items():
    ET.register_namespace(prefix, uri)

W_NS = f"{{{NAMESPACES['w']}}}"

def analyze_visual_fingerprints(doc_tree):
    paragraphs = doc_tree.findall(f'.//{W_NS}p')
    candidates = []
    
    for p in paragraphs:
        text_nodes = p.findall(f'.//{W_NS}t')
        text = "".join([t.text for t in text_nodes if t.text]).strip()
        if not text:
            continue
            
        sz_node = p.find(f'.//{W_NS}rPr/{W_NS}sz')
        sz = int(sz_node.attrib.get(f'{W_NS}val', '21')) if sz_node is not None else 21
        
        b_node = p.find(f'.//{W_NS}rPr/{W_NS}b')
        is_bold = b_node is not None
        
        font_node = p.find(f'.//{W_NS}rPr/{W_NS}rFonts')
        font_name = "仿宋_GB2312"
        if font_node is not None:
            font_name = font_node.attrib.get(f'{W_NS}eastAsia', font_node.attrib.get(f'{W_NS}ascii', '仿宋_GB2312'))
            
        candidates.append({
            'text': text,
            'sz': sz,
            'is_bold': is_bold,
            'font': font_name,
            'len': len(text)
        })
        
    return candidates

def synthesize_heading_styles(styles_tree, visual_hierarchy):
    root = styles_tree.getroot()
    
    for level, prop in enumerate(visual_hierarchy[:4], start=1):
        style_id = f"heading {level}"
        # 查找已有 style
        style_node = None
        for s in root.findall(f'{W_NS}style'):
            if s.attrib.get(f'{W_NS}styleId') == style_id:
                style_node = s
                break
                
        if style_node is None:
            style_node = ET.SubElement(root, f'{W_NS}style')
            style_node.attrib[f'{W_NS}type'] = "paragraph"
            style_node.attrib[f'{W_NS}styleId'] = style_id
            
            name_el = ET.SubElement(style_node, f'{W_NS}name')
            name_el.attrib[f'{W_NS}val'] = f"heading {level}"
            
        rPr = style_node.find(f'{W_NS}rPr')
        if rPr is None:
            rPr = ET.SubElement(style_node, f'{W_NS}rPr')
            
        rFonts = rPr.find(f'{W_NS}rFonts')
        if rFonts is None:
            rFonts = ET.SubElement(rPr, f'{W_NS}rFonts')
        rFonts.attrib[f'{W_NS}ascii'] = "Times New Roman"
        rFonts.attrib[f'{W_NS}eastAsia'] = prop.get('font', '黑体')
        
        sz_el = rPr.find(f'{W_NS}sz')
        if sz_el is None:
            sz_el = ET.SubElement(rPr, f'{W_NS}sz')
        sz_el.attrib[f'{W_NS}val'] = str(prop.get('sz', 32))
        
        if prop.get('is_bold', False):
            if rPr.find(f'{W_NS}b') is None:
                ET.SubElement(rPr, f'{W_NS}b')

def build_reference_docx(benchmark_docx: Path, output_ref_docx: Path) -> dict:
    diagnostics = []
    if not benchmark_docx.exists():
        return {
            "status": "FAIL",
            "diagnostics": [f"Benchmark file not found: {benchmark_docx}"],
            "output_files": []
        }
        
    output_ref_docx.parent.mkdir(parents=True, exist_ok=True)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        bench_dir = Path(tmp_dir) / "benchmark"
        with zipfile.ZipFile(benchmark_docx, 'r') as zip_ref:
            zip_ref.extractall(bench_dir)
            
        doc_xml_path = bench_dir / "word" / "document.xml"
        styles_xml_path = bench_dir / "word" / "styles.xml"
        
        if not doc_xml_path.exists() or not styles_xml_path.exists():
            return {
                "status": "FAIL",
                "diagnostics": ["Invalid docx structure: missing document.xml or styles.xml"],
                "output_files": []
            }
            
        doc_tree = ET.parse(str(doc_xml_path))
        styles_tree = ET.parse(str(styles_xml_path))
        
        candidates = analyze_visual_fingerprints(doc_tree)
        diagnostics.append(f"Scanned {len(candidates)} text paragraphs.")
        
        hierarchy = [
            {'sz': 44, 'font': '方正小标宋简体', 'is_bold': False}, # 一级: 二号小标宋
            {'sz': 32, 'font': '黑体', 'is_bold': True},           # 二级: 三号黑体
            {'sz': 32, 'font': '楷体_GB2312', 'is_bold': True},   # 三级: 三号楷体
            {'sz': 32, 'font': '仿宋_GB2312', 'is_bold': True}    # 四级: 三号仿宋加粗
        ]
        
        synthesize_heading_styles(styles_tree, hierarchy)
        styles_tree.write(str(styles_xml_path), xml_declaration=True, encoding="utf-8")
        diagnostics.append("Synthesized and injected Heading 1~4 styles into styles.xml")
        
        # 清空正文内容
        clean_doc = ET.Element(f'{W_NS}document')
        body = ET.SubElement(clean_doc, f'{W_NS}body')
        ET.SubElement(body, f'{W_NS}p')
        clean_tree = ET.ElementTree(clean_doc)
        clean_tree.write(str(doc_xml_path), xml_declaration=True, encoding="utf-8")
        diagnostics.append("Sanitized document body for pure reference template.")
        
        with zipfile.ZipFile(output_ref_docx, 'w', zipfile.ZIP_DEFLATED) as zip_out:
            for p in bench_dir.rglob('*'):
                if p.is_file():
                    zip_out.write(p, p.relative_to(bench_dir))
                    
        diagnostics.append(f"Successfully generated reference docx at {output_ref_docx}")
        
    return {
        "status": "SUCCESS",
        "diagnostics": diagnostics,
        "output_files": [str(output_ref_docx)]
    }

def main():
    parser = argparse.ArgumentParser(description="Extract reference.docx from benchmark Word")
    parser.add_argument("--input", "-i", required=True, help="Path to benchmark .docx file")
    parser.add_argument("--output", "-o", required=True, help="Path to output reference .docx")
    
    args = parser.parse_args()
    result = build_reference_docx(Path(args.input), Path(args.output))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "FAIL":
        sys.exit(1)

if __name__ == "__main__":
    main()
