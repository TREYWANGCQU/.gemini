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

def to_chinese_num(n: int) -> str:
    digits = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
    if n <= 10:
        return digits[n]
    elif n < 20:
        return f"十{digits[n % 10] if n % 10 != 0 else ''}"
    elif n < 100:
        tens, rem = divmod(n, 10)
        return f"{digits[tens]}十{digits[rem] if rem != 0 else ''}"
    return str(n)

def preprocess_typst_content(typst_code: str) -> str:
    # 1. 移除 #import、#show 与 #set 规则
    code = re.sub(r'#import\s+[^:\n]+(?::[^\n]*)?', '', typst_code)
    code = re.sub(r'#show:\s*doc\s*=>\s*conf\s*\([\s\S]*?\)', '', code)
    code = re.sub(r'#show\s+[^:\n]+:\s*set\s+[^\n]+', '', code)
    code = re.sub(r'#show\s+[^:\n]+:\s*flush-left-list', '', code)
    code = re.sub(r'#set\s+page\s*\([\s\S]*?\)', '', code)
    code = re.sub(r'#set\s+text\s*\([\s\S]*?\)', '', code)
    code = re.sub(r'#set\s+par\s*\([\s\S]*?\)', '', code)
    
    # 2. 清理自定义宏与辅助标签（#no-indent, #h(...), #v(...)）
    code = re.sub(r'#no-indent\b', '', code)
    code = re.sub(r'#h\([^)]*\)', '', code)
    code = re.sub(r'#v\([^)]*\)', '', code)
    
    # 3. 解包 #text(font: ...)[content] 或 #text(...)[content]
    while re.search(r'#text\([^)]*\)\[([\s\S]*?)\]', code):
        code = re.sub(r'#text\([^)]*\)\[([\s\S]*?)\]', r'\1', code)
    
    lines = code.splitlines()
    clean_lines = []
    
    # 计数器模拟 Typst @local/GBK-writing:0.1.0 逻辑
    h2_cnt = 0
    h3_cnt = 0
    h4_cnt = 0
    h5_cnt = 0
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('//'):
            continue
        if stripped.startswith('#import ') or stripped.startswith('#show:') or stripped.startswith('#show '):
            continue
        if stripped.startswith('#set '):
            continue
            
        # 智能匹配 Typst 标题并对齐 GBK 序号
        # Level 1: = 标题 (无序号 / 主标题)
        # Level 2: == 二级标题 (注入 一、, 二、 若原标题未带)
        # Level 3: === 三级标题 (注入 （一）, （二） 若原标题未带)
        # Level 4: ==== 四级标题 (注入 1., 2. 若原标题未带)
        # Level 5: ===== 五级标题 (注入 （1）, （2） 若原标题未带)
        h_match = re.match(r'^(={1,5})\s+(.*)$', line)
        if h_match:
            eqs, title_body = h_match.groups()
            level = len(eqs)
            title_text = title_body.strip()
            
            if level == 1:
                clean_lines.append(f"= {title_text}")
            elif level == 2:
                h2_cnt += 1
                h3_cnt = 0
                h4_cnt = 0
                h5_cnt = 0
                # 检查是否已含有 一、 或 第一章 等字样
                if not re.match(r'^[一二三四五六七八九十百]+[、\.\s]|第[一二三四五六七八九十]+[章节条]', title_text):
                    prefix = f"{to_chinese_num(h2_cnt)}、"
                    clean_lines.append(f"== {prefix}{title_text}")
                else:
                    clean_lines.append(f"== {title_text}")
            elif level == 3:
                h3_cnt += 1
                h4_cnt = 0
                h5_cnt = 0
                if not re.match(r'^[（(][一二三四五六七八九十百]+[)）]', title_text):
                    prefix = f"（{to_chinese_num(h3_cnt)}）"
                    clean_lines.append(f"=== {prefix}{title_text}")
                else:
                    clean_lines.append(f"=== {title_text}")
            elif level == 4:
                h4_cnt += 1
                h5_cnt = 0
                if not re.match(r'^\d+[\.\、\s]', title_text):
                    prefix = f"{h4_cnt}. "
                    clean_lines.append(f"==== {prefix}{title_text}")
                else:
                    clean_lines.append(f"==== {title_text}")
            elif level == 5:
                h5_cnt += 1
                if not re.match(r'^[（(]\d+[)）]', title_text):
                    prefix = f"（{h5_cnt}）"
                    clean_lines.append(f"===== {prefix}{title_text}")
                else:
                    clean_lines.append(f"===== {title_text}")
        else:
            clean_lines.append(line)
            
    return "\n".join(clean_lines).strip()

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
    resolved_template = None
    if template_path:
        if template_path.exists():
            resolved_template = template_path
        else:
            global_candidate = Path.home() / ".gemini" / "config" / "templates" / template_path.name
            if global_candidate.exists():
                resolved_template = global_candidate
            elif (Path.home() / ".gemini" / "config" / "templates" / f"{template_path.name}.docx").exists():
                resolved_template = Path.home() / ".gemini" / "config" / "templates" / f"{template_path.name}.docx"

    if not resolved_template:
        canonical_ref = Path.home() / ".gemini" / "config" / "templates" / "reference-gbk.docx"
        if canonical_ref.exists():
            resolved_template = canonical_ref
        elif Path("reference.docx").exists():
            resolved_template = Path("reference.docx")

    if resolved_template and resolved_template.exists():
        ref_arg = [f"--reference-doc={resolved_template}"]
        diagnostics.append(f"Using template: {resolved_template}")
            
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
                    heading_style_ids = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "heading 1", "heading 2", "heading 3", "heading 4", "Heading1", "Heading2", "Heading3", "Heading4"}
                    if "word/styles.xml" in z.namelist():
                        styles_xml = z.read("word/styles.xml")
                        stree = ET.fromstring(styles_xml)
                        for s in stree.findall('.//w:style', NAMESPACES):
                            sid = s.attrib.get(f'{{{NAMESPACES["w"]}}}styleId')
                            sname = s.find('.//w:name', NAMESPACES)
                            sname_val = sname.attrib.get(f'{{{NAMESPACES["w"]}}}val', '').lower() if sname is not None else ''
                            soutline = s.find('.//w:outlineLvl', NAMESPACES)
                            if soutline is not None or 'heading' in sname_val:
                                if sid:
                                    heading_style_ids.add(sid)
                                    
                    headings = [
                        p for p in tree.findall('.//w:p', NAMESPACES)
                        if p.find('.//w:pStyle', NAMESPACES) is not None and p.find('.//w:pStyle', NAMESPACES).attrib.get(f'{{{NAMESPACES["w"]}}}val') in heading_style_ids
                    ]
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
