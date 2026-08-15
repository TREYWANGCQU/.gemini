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

ET.register_namespace('w', NAMESPACES['w'])

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

def clean_template_numpr(template_path: Path):
    """确保参考母版中 Heading 1~4 不携带多余的自动编号 (numPr)，避免与文本内序号冲突"""
    try:
        with zipfile.ZipFile(template_path, 'r') as zin:
            if "word/styles.xml" not in zin.namelist():
                return
            styles_xml = zin.read("word/styles.xml")
            all_files = {item.filename: zin.read(item.filename) for item in zin.infolist()}
            
        tree = ET.fromstring(styles_xml)
        ns = {'w': NAMESPACES['w']}
        modified = False
        for sid in ['Heading1', 'Heading2', 'Heading3', 'Heading4', 'heading 1', 'heading 2', 'heading 3', 'heading 4']:
            for s in tree.findall(f'.//w:style[@w:styleId="{sid}"]', ns):
                pPr = s.find('.//w:pPr', ns)
                if pPr is not None:
                    numPr = pPr.find('.//w:numPr', ns)
                    if numPr is not None:
                        pPr.remove(numPr)
                        modified = True
                        
        if modified:
            all_files["word/styles.xml"] = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
            temp_ref = template_path.with_name(f"temp_{template_path.name}")
            with zipfile.ZipFile(temp_ref, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
                for fname, data in all_files.items():
                    zout.writestr(fname, data)
            temp_ref.replace(template_path)
    except Exception:
        pass

def extract_balanced_brackets(text: str, start_idx: int) -> tuple[str, int]:
    depth = 1
    idx = start_idx + 1
    while idx < len(text) and depth > 0:
        if text[idx] == '[':
            depth += 1
        elif text[idx] == ']':
            depth -= 1
        idx += 1
    if depth == 0:
        return text[start_idx + 1 : idx - 1], idx
    return "", -1

def replace_align_blocks(code: str) -> str:
    pattern = re.compile(r'#align\s*\(\s*(center|left|right)\s*\)\s*\[')
    while True:
        m = pattern.search(code)
        if not m:
            break
        align_type = m.group(1)
        start_bracket = m.end() - 1
        inner, end_idx = extract_balanced_brackets(code, start_bracket)
        if end_idx != -1:
            font_match = re.search(r'#text\([^)]*font:\s*([^,\])]+)', inner)
            font_name = "KaiTi"
            text_content = inner
            if font_match:
                font_raw = font_match.group(1).strip()
                if '楷体' in font_raw or 'Kai' in font_raw:
                    font_name = "KaiTi"
                elif '黑体' in font_raw or 'Hei' in font_raw:
                    font_name = "HeiTi"
                elif '仿宋' in font_raw or 'Fang' in font_raw:
                    font_name = "FangSong"
                elif '小标宋' in font_raw or 'Song' in font_raw:
                    font_name = "XiaoBiaoSong"
            while re.search(r'#text\([^)]*\)\[([\s\S]*?)\]', text_content):
                text_content = re.sub(r'#text\([^)]*\)\[([\s\S]*?)\]', r'\1', text_content)
            text_content = re.sub(r'#text\([^)]*\)', '', text_content).strip()
            
            replacement = f"\n\n[[[ALIGNCENTER:{font_name}]]] {text_content} [[[ENDALIGNCENTER]]]\n\n"
            code = code[:m.start()] + replacement + code[end_idx:]
        else:
            break
    return code

def preprocess_typst_content(typst_code: str) -> str:
    # 1. 移除全局配置
    code = re.sub(r'#import\s+[^:\n]+(?::[^\n]*)?', '', typst_code)
    code = re.sub(r'#show:\s*doc\s*=>\s*conf\s*\([\s\S]*?\)', '', code)
    code = re.sub(r'#show\s+[^:\n]+:\s*set\s+[^\n]+', '', code)
    code = re.sub(r'#show\s+[^:\n]+:\s*flush-left-list', '', code)
    code = re.sub(r'#set\s+page\s*\([\s\S]*?\)', '', code)
    code = re.sub(r'#set\s+text\s*\([\s\S]*?\)', '', code)
    code = re.sub(r'#set\s+par\s*\([\s\S]*?\)', '', code)
    
    # 2. 清理局部控制宏
    code = re.sub(r'#no-indent\b', '', code)
    code = re.sub(r'#h\([^)]*\)', '', code)
    code = re.sub(r'#v\([^)]*\)', '', code)
    
    # 3. 提取并安全标记 #align(center)[...]（支持任意嵌套 #text）
    code = replace_align_blocks(code)
    
    # 解包剩余 #text(...)
    while re.search(r'#text\([^)]*\)\[([\s\S]*?)\]', code):
        code = re.sub(r'#text\([^)]*\)\[([\s\S]*?)\]', r'\1', code)
        
    lines = code.splitlines()
    clean_lines = []
    
    h2_cnt = 0
    h3_cnt = 0
    h4_cnt = 0
    h5_cnt = 0
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            clean_lines.append("")
            continue
        if stripped.startswith('//') or stripped.startswith('#'):
            continue
            
        # 智能匹配 Typst 标题并对齐 GBK 序号与 Word 样式层级
        # Level 1: = 标题 -> Word [标题] (Title)
        # Level 2: == 二级标题 -> Word [一级标题] (Heading 1)
        # Level 3: === 三级标题 -> Word [二级标题] (Heading 2)
        # Level 4: ==== 四级标题 -> Word [三级标题] (Heading 3)
        # Level 5: ===== 五级标题 -> Word [四级标题] (Heading 4)
        h_match = re.match(r'^(={1,5})\s+(.*)$', stripped)
        if h_match:
            eqs, title_body = h_match.groups()
            level = len(eqs)
            title_text = title_body.strip()
            
            if level == 1:
                clean_lines.append(f"\n[[[DOCUMENTTITLE]]] {title_text} [[[ENDDOCUMENTTITLE]]]\n")
            elif level == 2:
                h2_cnt += 1
                h3_cnt = 0
                h4_cnt = 0
                h5_cnt = 0
                if not re.match(r'^[一二三四五六七八九十百]+[、\.\s]|第[一二三四五六七八九十]+[章节条]', title_text):
                    prefix = f"{to_chinese_num(h2_cnt)}、"
                    clean_lines.append(f"= {prefix}{title_text}")
                else:
                    clean_lines.append(f"= {title_text}")
            elif level == 3:
                h3_cnt += 1
                h4_cnt = 0
                h5_cnt = 0
                if not re.match(r'^[（(][一二三四五六七八九十百]+[)）]', title_text):
                    prefix = f"（{to_chinese_num(h3_cnt)}）"
                    clean_lines.append(f"== {prefix}{title_text}")
                else:
                    clean_lines.append(f"== {title_text}")
            elif level == 4:
                h4_cnt += 1
                h5_cnt = 0
                if not re.match(r'^\d+[\.\、\s]', title_text):
                    prefix = f"{h4_cnt}. "
                    clean_lines.append(f"=== {prefix}{title_text}")
                else:
                    clean_lines.append(f"=== {title_text}")
            elif level == 5:
                h5_cnt += 1
                if not re.match(r'^[（(]\d+[)）]', title_text):
                    prefix = f"（{h5_cnt}）"
                    clean_lines.append(f"==== {prefix}{title_text}")
                else:
                    clean_lines.append(f"==== {title_text}")
        else:
            clean_lines.append(line)
            
    return "\n".join(clean_lines) + "\n\n"

def postprocess_docx_xml(docx_path: Path):
    """后处理 DOCX 内部 XML：注入 Word [标题] 与居中/副标题/作者格式，清洗占位符"""
    with zipfile.ZipFile(docx_path, 'r') as zin:
        all_files = {item.filename: zin.read(item.filename) for item in zin.infolist()}
        
    doc_xml = all_files.get("word/document.xml")
    if not doc_xml:
        return
        
    tree = ET.fromstring(doc_xml)
    ns = {'w': NAMESPACES['w']}
    w_pPr = f"{{{ns['w']}}}pPr"
    w_pStyle = f"{{{ns['w']}}}pStyle"
    w_rPr = f"{{{ns['w']}}}rPr"
    w_rFonts = f"{{{ns['w']}}}rFonts"
    w_sz = f"{{{ns['w']}}}sz"
    w_szCs = f"{{{ns['w']}}}szCs"
    w_jc = f"{{{ns['w']}}}jc"
    w_ind = f"{{{ns['w']}}}ind"
    w_val = f"{{{ns['w']}}}val"
    w_eastAsia = f"{{{ns['w']}}}eastAsia"
    w_ascii = f"{{{ns['w']}}}ascii"
    w_hAnsi = f"{{{ns['w']}}}hAnsi"
    w_cs = f"{{{ns['w']}}}cs"
    
    font_map = {
        "KaiTi": "方正楷体_GBK",
        "HeiTi": "方正黑体_GBK",
        "FangSong": "方正仿宋_GBK",
        "XiaoBiaoSong": "方正小标宋_GBK",
    }
    
    modified = False
    
    for p in tree.findall('.//w:p', ns):
        runs = p.findall('.//w:r', ns)
        p_text = "".join("".join(t.text for t in r.findall('.//w:t', ns) if t.text) for r in runs)
        
        # 1. 主标题映射为 Word [标题] (Title 样式)
        if "DOCUMENTTITLE" in p_text:
            modified = True
            cleaned_title = re.sub(r'\[+DOCUMENTTITLE\]+', '', p_text)
            cleaned_title = re.sub(r'\[+ENDDOCUMENTTITLE\]+', '', cleaned_title).strip()
            
            # Put cleaned text in first run and clear others
            first = True
            for r in runs:
                for t in r.findall('.//w:t', ns):
                    if first:
                        t.text = cleaned_title
                        first = False
                    else:
                        t.text = ""
            
            pPr = p.find('.//w:pPr', ns)
            if pPr is None:
                pPr = ET.Element(w_pPr)
                p.insert(0, pPr)
            pStyle = pPr.find('.//w:pStyle', ns)
            if pStyle is None:
                pStyle = ET.Element(w_pStyle)
                pPr.insert(0, pStyle)
            pStyle.attrib[w_val] = "Title"
            
            jc = pPr.find('.//w:jc', ns)
            if jc is None:
                jc = ET.Element(w_jc)
                pPr.append(jc)
            jc.attrib[w_val] = "center"
            
            ind = pPr.find('.//w:ind', ns)
            if ind is not None:
                pPr.remove(ind)
            new_ind = ET.Element(w_ind)
            new_ind.attrib[f"{{{ns['w']}}}firstLine"] = "0"
            new_ind.attrib[f"{{{ns['w']}}}firstLineChars"] = "0"
            pPr.append(new_ind)
            
            for r in runs:
                rPr = r.find('.//w:rPr', ns)
                if rPr is None:
                    rPr = ET.Element(w_rPr)
                    r.insert(0, rPr)
                rFonts = rPr.find('.//w:rFonts', ns)
                if rFonts is None:
                    rFonts = ET.Element(w_rFonts)
                    rPr.insert(0, rFonts)
                rFonts.attrib[w_eastAsia] = "方正小标宋_GBK"
                rFonts.attrib[w_ascii] = "Times New Roman"
                rFonts.attrib[w_hAnsi] = "Times New Roman"
                rFonts.attrib[w_cs] = "Times New Roman"
                
                sz = rPr.find('.//w:sz', ns)
                if sz is None:
                    sz = ET.Element(w_sz)
                    rPr.append(sz)
                sz.attrib[w_val] = "44"
                szCs = rPr.find('.//w:szCs', ns)
                if szCs is None:
                    szCs = ET.Element(w_szCs)
                    rPr.append(szCs)
                szCs.attrib[w_val] = "44"

        # 2. 居中段落 / 副标题 / 作者署名
        align_match = re.search(r'\[+ALIGNCENTER:([A-Za-z0-9]+)\]+', p_text)
        if align_match:
            modified = True
            font_tag = align_match.group(1)
            font_name = font_map.get(font_tag, "方正楷体_GBK")
            
            cleaned_body = re.sub(r'\[+ALIGNCENTER:[A-Za-z0-9]+\]+', '', p_text)
            cleaned_body = re.sub(r'\[+ENDALIGNCENTER\]+', '', cleaned_body).strip()
            
            first = True
            for r in runs:
                for t in r.findall('.//w:t', ns):
                    if first:
                        t.text = cleaned_body
                        first = False
                    else:
                        t.text = ""
                        
            pPr = p.find('.//w:pPr', ns)
            if pPr is None:
                pPr = ET.Element(w_pPr)
                p.insert(0, pPr)
            pStyle = pPr.find('.//w:pStyle', ns)
            if pStyle is None:
                pStyle = ET.Element(w_pStyle)
                pPr.insert(0, pStyle)
            pStyle.attrib[w_val] = "Subtitle"
            
            jc = pPr.find('.//w:jc', ns)
            if jc is None:
                jc = ET.Element(w_jc)
                pPr.append(jc)
            jc.attrib[w_val] = "center"
            
            ind = pPr.find('.//w:ind', ns)
            if ind is not None:
                pPr.remove(ind)
            new_ind = ET.Element(w_ind)
            new_ind.attrib[f"{{{ns['w']}}}firstLine"] = "0"
            new_ind.attrib[f"{{{ns['w']}}}firstLineChars"] = "0"
            pPr.append(new_ind)
            
            for r in runs:
                rPr = r.find('.//w:rPr', ns)
                if rPr is None:
                    rPr = ET.Element(w_rPr)
                    r.insert(0, rPr)
                rFonts = rPr.find('.//w:rFonts', ns)
                if rFonts is None:
                    rFonts = ET.Element(w_rFonts)
                    rPr.insert(0, rFonts)
                rFonts.attrib[w_eastAsia] = font_name
                rFonts.attrib[w_ascii] = "Times New Roman"
                rFonts.attrib[w_hAnsi] = "Times New Roman"
                rFonts.attrib[w_cs] = "Times New Roman"
                
                sz = rPr.find('.//w:sz', ns)
                if sz is None:
                    sz = ET.Element(w_sz)
                    rPr.append(sz)
                sz.attrib[w_val] = "32"
                
                szCs = rPr.find('.//w:szCs', ns)
                if szCs is None:
                    szCs = ET.Element(w_szCs)
                    rPr.append(szCs)
                szCs.attrib[w_val] = "32"

    if modified:
        all_files["word/document.xml"] = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
        temp_docx = docx_path.with_name(f"temp_{docx_path.name}")
        with zipfile.ZipFile(temp_docx, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
            for fname, data in all_files.items():
                zout.writestr(fname, data)
        temp_docx.replace(docx_path)

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
        clean_template_numpr(resolved_template)
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
            
        postprocess_docx_xml(output_path)
        diagnostics.append(f"Successfully generated DOCX at {output_path}")
        
        if output_path.exists():
            with zipfile.ZipFile(output_path, 'r') as z:
                if "word/document.xml" in z.namelist():
                    doc_xml = z.read("word/document.xml")
                    tree = ET.fromstring(doc_xml)
                    heading_style_ids = {"Title", "1", "2", "3", "4", "5", "6", "7", "8", "9", "heading 1", "heading 2", "heading 3", "heading 4", "Heading1", "Heading2", "Heading3", "Heading4"}
                    if "word/styles.xml" in z.namelist():
                        styles_xml = z.read("word/styles.xml")
                        stree = ET.fromstring(styles_xml)
                        for s in stree.findall('.//w:style', NAMESPACES):
                            sid = s.attrib.get(f'{{{NAMESPACES["w"]}}}styleId')
                            sname = s.find('.//w:name', NAMESPACES)
                            sname_val = sname.attrib.get(f'{{{NAMESPACES["w"]}}}val', '').lower() if sname is not None else ''
                            soutline = s.find('.//w:outlineLvl', NAMESPACES)
                            if soutline is not None or 'heading' in sname_val or 'title' in sname_val:
                                if sid:
                                    heading_style_ids.add(sid)
                                    
                    headings = [
                        p for p in tree.findall('.//w:p', NAMESPACES)
                        if p.find('.//w:pStyle', NAMESPACES) is not None and p.find('.//w:pStyle', NAMESPACES).attrib.get(f'{{{NAMESPACES["w"]}}}val') in heading_style_ids
                    ]
                    tables = tree.findall('.//w:tbl', NAMESPACES)
                    diagnostics.append(f"Quality Audit: Mapped {len(headings)} outline/title headings, {len(tables)} tables.")
                    
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
