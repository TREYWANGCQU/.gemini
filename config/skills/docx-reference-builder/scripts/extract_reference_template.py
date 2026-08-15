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

def detect_fonts(styles_tree):
    root = styles_tree.getroot()
    fonts = {
        'title': '方正小标宋_GBK',
        'h1': '方正黑体_GBK',
        'h2': '方正楷体_GBK',
        'h3': '方正仿宋_GBK',
        'h4': '方正仿宋_GBK',
        'normal': '方正仿宋_GBK'
    }
    # 扫描 styles.xml 中的中文字体定义
    for s in root.findall(f'{W_NS}style'):
        rPr = s.find(f'{W_NS}rPr')
        if rPr is not None:
            rFonts = rPr.find(f'{W_NS}rFonts')
            if rFonts is not None:
                ea = rFonts.attrib.get(f'{W_NS}eastAsia', '')
                if '小标宋' in ea:
                    fonts['title'] = ea
                elif '黑体' in ea:
                    fonts['h1'] = ea
                elif '楷体' in ea:
                    fonts['h2'] = ea
                elif '仿宋' in ea:
                    fonts['h3'] = ea
                    fonts['h4'] = ea
                    fonts['normal'] = ea
    return fonts

def synthesize_heading_styles(styles_tree, visual_hierarchy, fonts):
    root = styles_tree.getroot()
    
    # 1. 统一更新或合成 Title 样式
    title_nodes = []
    for s in root.findall(f'{W_NS}style'):
        name_el = s.find(f'{W_NS}name')
        name_val = name_el.attrib.get(f'{W_NS}val', '').lower() if name_el is not None else ''
        s_id = s.attrib.get(f'{W_NS}styleId', '')
        if s_id in ['Title', 'a7', 'title'] or name_val == 'title':
            title_nodes.append(s)
            
    title_node = title_nodes[0] if title_nodes else ET.SubElement(root, f'{W_NS}style')
    title_node.attrib[f'{W_NS}type'] = "paragraph"
    title_node.attrib[f'{W_NS}styleId'] = "Title"
    name_el = title_node.find(f'{W_NS}name')
    if name_el is None:
        name_el = ET.SubElement(title_node, f'{W_NS}name')
    name_el.attrib[f'{W_NS}val'] = "Title"
    
    rPr = title_node.find(f'{W_NS}rPr')
    if rPr is None:
        rPr = ET.SubElement(title_node, f'{W_NS}rPr')
    rFonts = rPr.find(f'{W_NS}rFonts')
    if rFonts is None:
        rFonts = ET.SubElement(rPr, f'{W_NS}rFonts')
    rFonts.attrib[f'{W_NS}ascii'] = "Times New Roman"
    rFonts.attrib[f'{W_NS}hAnsi'] = "Times New Roman"
    rFonts.attrib[f'{W_NS}eastAsia'] = fonts['title']
    rFonts.attrib[f'{W_NS}cs'] = "Times New Roman"
    sz_el = rPr.find(f'{W_NS}sz')
    if sz_el is None:
        sz_el = ET.SubElement(rPr, f'{W_NS}sz')
    sz_el.attrib[f'{W_NS}val'] = "44"
    szCs_el = rPr.find(f'{W_NS}szCs')
    if szCs_el is None:
        szCs_el = ET.SubElement(rPr, f'{W_NS}szCs')
    szCs_el.attrib[f'{W_NS}val'] = "44"
    
    pPr = title_node.find(f'{W_NS}pPr')
    if pPr is None:
        pPr = ET.SubElement(title_node, f'{W_NS}pPr')
    jc = pPr.find(f'{W_NS}jc')
    if jc is None:
        jc = ET.SubElement(pPr, f'{W_NS}jc')
    jc.attrib[f'{W_NS}val'] = "center"
    
    # 2. 统一更新或合成 Heading 1~4
    for level, prop in enumerate(visual_hierarchy[:4], start=1):
        target_ids = [f"Heading{level}", f"heading {level}", f"Heading {level}", str(level)]
        matching_nodes = []
        for s in root.findall(f'{W_NS}style'):
            name_el = s.find(f'{W_NS}name')
            name_val = name_el.attrib.get(f'{W_NS}val', '').lower() if name_el is not None else ''
            s_id = s.attrib.get(f'{W_NS}styleId', '')
            if s_id in target_ids or name_val == f"heading {level}":
                matching_nodes.append(s)
                
        # 移除多余重名节点，保留第一个作为标准主节点
        style_node = matching_nodes[0] if matching_nodes else ET.SubElement(root, f'{W_NS}style')
        for extra in matching_nodes[1:]:
            root.remove(extra)
            
        style_node.attrib[f'{W_NS}type'] = "paragraph"
        style_node.attrib[f'{W_NS}styleId'] = f"Heading{level}"
        
        name_el = style_node.find(f'{W_NS}name')
        if name_el is None:
            name_el = ET.SubElement(style_node, f'{W_NS}name')
        name_el.attrib[f'{W_NS}val'] = f"heading {level}"
            
        rPr = style_node.find(f'{W_NS}rPr')
        if rPr is None:
            rPr = ET.SubElement(style_node, f'{W_NS}rPr')
            
        # 清除颜色、斜体与主题覆盖
        for child in list(rPr):
            tag = child.tag.replace(W_NS, '')
            if tag in ['color', 'i', 'iCs', 'strike', 'dstrike']:
                rPr.remove(child)
                
        color = ET.SubElement(rPr, f'{W_NS}color')
        color.attrib[f'{W_NS}val'] = "000000"
            
        rFonts = rPr.find(f'{W_NS}rFonts')
        if rFonts is None:
            rFonts = ET.SubElement(rPr, f'{W_NS}rFonts')
        for att in ['asciiTheme', 'eastAsiaTheme', 'hAnsiTheme', 'cstheme']:
            if f'{W_NS}{att}' in rFonts.attrib:
                del rFonts.attrib[f'{W_NS}{att}']
        rFonts.attrib[f'{W_NS}ascii'] = "Times New Roman"
        rFonts.attrib[f'{W_NS}hAnsi'] = "Times New Roman"
        rFonts.attrib[f'{W_NS}eastAsia'] = prop.get('font', fonts.get(f'h{level}', '黑体'))
        rFonts.attrib[f'{W_NS}cs'] = "Times New Roman"
        
        sz_el = rPr.find(f'{W_NS}sz')
        if sz_el is None:
            sz_el = ET.SubElement(rPr, f'{W_NS}sz')
        sz_val = prop.get('sz', 32)
        sz_el.attrib[f'{W_NS}val'] = str(sz_val)
        
        szCs_el = rPr.find(f'{W_NS}szCs')
        if szCs_el is None:
            szCs_el = ET.SubElement(rPr, f'{W_NS}szCs')
        szCs_el.attrib[f'{W_NS}val'] = str(sz_val)
        
        if prop.get('is_bold', False):
            if rPr.find(f'{W_NS}b') is None:
                ET.SubElement(rPr, f'{W_NS}b')
        else:
            b_el = rPr.find(f'{W_NS}b')
            if b_el is not None:
                rPr.remove(b_el)
                
        pPr = style_node.find(f'{W_NS}pPr')
        if pPr is None:
            pPr = ET.SubElement(style_node, f'{W_NS}pPr')
            
        if prop.get('is_center', False):
            jc = pPr.find(f'{W_NS}jc')
            if jc is None:
                jc = ET.SubElement(pPr, f'{W_NS}jc')
            jc.attrib[f'{W_NS}val'] = 'center'
        else:
            jc = pPr.find(f'{W_NS}jc')
            if jc is not None:
                pPr.remove(jc)
                
        # 缩进处理 (Heading 1~4 首行缩进 2 字符)
        indent_chars = prop.get('indent_chars', 2)
        ind = pPr.find(f'{W_NS}ind')
        if indent_chars > 0:
            if ind is None:
                ind = ET.SubElement(pPr, f'{W_NS}ind')
            ind.attrib[f'{W_NS}firstLine'] = str(indent_chars * sz_val * 10)
            ind.attrib[f'{W_NS}firstLineChars'] = str(indent_chars * 100)
        else:
            if ind is not None:
                pPr.remove(ind)
                
        # 间距与行距处理 (固定值 30磅 / 600 dxa)
        sp = pPr.find(f'{W_NS}spacing')
        if sp is None:
            sp = ET.SubElement(pPr, f'{W_NS}spacing')
        else:
            sp.attrib.clear()
            
        line_exact = prop.get('line_exact_pt', 30)
        sp.attrib[f'{W_NS}line'] = str(int(line_exact * 20))
        sp.attrib[f'{W_NS}lineRule'] = 'exact'
        if prop.get('space_after_pt', 0) > 0:
            sp.attrib[f'{W_NS}after'] = str(int(prop['space_after_pt'] * 20))
        if prop.get('space_before_pt', 0) > 0:
            sp.attrib[f'{W_NS}before'] = str(int(prop['space_before_pt'] * 20))

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
        
        detected_fonts = detect_fonts(styles_tree)
        diagnostics.append(f"Detected document fonts: {detected_fonts}")
        
        hierarchy = [
            {'sz': 32, 'font': detected_fonts['h1'], 'is_bold': False, 'is_center': False, 'indent_chars': 2, 'line_exact_pt': 30, 'space_before_pt': 0, 'space_after_pt': 0}, # 一级: 三号黑体
            {'sz': 32, 'font': detected_fonts['h2'], 'is_bold': False, 'is_center': False, 'indent_chars': 2, 'line_exact_pt': 30, 'space_before_pt': 0, 'space_after_pt': 0}, # 二级: 三号楷体
            {'sz': 32, 'font': detected_fonts['h3'], 'is_bold': True, 'is_center': False, 'indent_chars': 2, 'line_exact_pt': 30, 'space_before_pt': 0, 'space_after_pt': 0},  # 三级: 三号仿宋加粗
            {'sz': 32, 'font': detected_fonts['h4'], 'is_bold': False, 'is_center': False, 'indent_chars': 2, 'line_exact_pt': 30, 'space_before_pt': 0, 'space_after_pt': 0}  # 四级: 三号仿宋常规
        ]
        
        synthesize_heading_styles(styles_tree, hierarchy, detected_fonts)
        styles_tree.write(str(styles_xml_path), xml_declaration=True, encoding="utf-8")
        diagnostics.append("Synthesized and injected Heading 1~4 and Title styles into styles.xml")
        
        # 清空正文内容
        clean_doc = ET.Element(f'{W_NS}document')
        body = ET.SubElement(clean_doc, f'{W_NS}body')
        ET.SubElement(body, f'{W_NS}p')
        
        # 保留原文档节属性（页面尺寸、页边距、页眉页脚关联等）
        sectPr = doc_tree.find(f'.//{W_NS}sectPr')
        if sectPr is not None:
            body.append(sectPr)
            
        clean_tree = ET.ElementTree(clean_doc)
        clean_tree.write(str(doc_xml_path), xml_declaration=True, encoding="utf-8")
        diagnostics.append("Sanitized document body for pure reference template while preserving sectPr.")
        
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
