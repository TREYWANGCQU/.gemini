# -*- coding: utf-8 -*-
# scripts/publisher.py
import os
import sys
import re
import json
import argparse
import subprocess
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
        target_sids = ['Heading1', 'Heading2', 'Heading3', 'Heading4', 'heading 1', 'heading 2', 'heading 3', 'heading 4', '1', '2', '3', '4']
        for sid in target_sids:
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

def extract_balanced_brackets(text: str, start_idx: int, open_char: str = '[', close_char: str = ']') -> tuple[str, int]:
    depth = 1
    idx = start_idx + 1
    while idx < len(text) and depth > 0:
        if text[idx] == open_char:
            depth += 1
        elif text[idx] == close_char:
            depth -= 1
        idx += 1
    if depth == 0:
        return text[start_idx + 1 : idx - 1], idx
    return "", -1

def extract_conf_metadata(typst_code: str) -> dict:
    meta = {}
    m = re.search(r'#show:\s*doc\s*=>\s*conf\s*\(', typst_code)
    if not m:
        return meta
    start_paren = m.end() - 1
    conf_body, _ = extract_balanced_brackets(typst_code, start_paren, open_char='(', close_char=')')
    if not conf_body:
        return meta
        
    tm = re.search(r'title:\s*["\']([^"\']+)["\']', conf_body)
    if tm:
        meta['title'] = tm.group(1).strip()
        
    stm = re.search(r'subtitle:\s*["\']([^"\']+)["\']', conf_body)
    if stm:
        meta['subtitle'] = stm.group(1).strip()
        
    authors = []
    for am in re.finditer(r'name:\s*["\']([^"\']+)["\'](?:\s*,\s*affiliation:\s*["\']([^"\']+)["\'])?', conf_body):
        name = am.group(1).strip()
        affil = am.group(2).strip() if am.group(2) else ""
        if affil:
            authors.append(f"{name}（{affil}）")
        else:
            authors.append(name)
    if authors:
        meta['authors'] = "，".join(authors)
        
    ab_m = re.search(r'abstract:\s*\[', conf_body)
    if ab_m:
        ab_inner, _ = extract_balanced_brackets(conf_body, ab_m.end() - 1, open_char='[', close_char=']')
        if ab_inner:
            meta['abstract'] = ab_inner.strip()
            
    kw_m = re.search(r'keywords:\s*\(([\s\S]*?)\)', conf_body)
    if kw_m:
        kws = [k.strip().strip('"\'') for k in kw_m.group(1).split(',') if k.strip().strip('"\'')]
        if kws:
            meta['keywords'] = "；".join(kws)
            
    return meta

def replace_align_blocks(code: str) -> str:
    pattern = re.compile(r'#align\s*\(\s*(center|left|right)\s*\)\s*\[')
    while True:
        m = pattern.search(code)
        if not m:
            break
        align_type = m.group(1).lower()
        start_bracket = m.end() - 1
        inner, end_idx = extract_balanced_brackets(code, start_bracket)
        if end_idx != -1:
            font_match = re.search(r'#text\([^)]*font:\s*([^,\])]+)', inner)
            font_name = "FangSong" if align_type == "right" else "KaiTi"
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
            
            lines = [l.strip() for l in re.split(r'\\|\n', text_content) if l.strip()]
            tag = f"ALIGN{align_type.upper()}:{font_name}"
            end_tag = f"ENDALIGN{align_type.upper()}"
            replacements = [f"[[[{tag}]]] {l} [[[{end_tag}]]]" for l in lines]
            replacement = "\n\n" + "\n\n".join(replacements) + "\n\n"
            code = code[:m.start()] + replacement + code[end_idx:]
        else:
            break
    return code

def preprocess_typst_content(typst_code: str, is_paper_mode: bool = False) -> str:
    # 0. 提取学术/方案元数据 (conf)
    meta = extract_conf_metadata(typst_code)
    
    # 1. 移除全局配置与宏
    code = re.sub(r'#import\s+[^:\n]+(?::[^\n]*)?', '', typst_code)
    
    # 彻底清除 #show: doc => conf(...)
    m_conf = re.search(r'#show:\s*doc\s*=>\s*conf\s*\(', code)
    if m_conf:
        start_paren = m_conf.end() - 1
        _, end_idx = extract_balanced_brackets(code, start_paren, open_char='(', close_char=')')
        if end_idx != -1:
            code = code[:m_conf.start()] + code[end_idx:]
            
    code = re.sub(r'#show\s+[^:\n]+:\s*set\s+[^\n]+', '', code)
    code = re.sub(r'#show\s+[^:\n]+:\s*flush-left-list', '', code)
    code = re.sub(r'#set\s+page\s*\([\s\S]*?\)', '', code)
    code = re.sub(r'#set\s+text\s*\([\s\S]*?\)', '', code)
    code = re.sub(r'#set\s+par\s*\([\s\S]*?\)', '', code)
    
    # 2. 清理局部控制宏
    code = re.sub(r'#indent\b', '', code)
    code = re.sub(r'#no-indent\s*', '[[[NOINDENT]]] ', code)
    code = re.sub(r'#h\([^)]*\)', '', code)
    code = re.sub(r'#v\([^)]*\)', '', code)
    
    # 3. 展开或替换自定义 #todo[...] 宏
    while True:
        m = re.search(r'#todo\s*\[', code)
        if not m:
            break
        start_pos = m.start()
        start_bracket = m.end() - 1
        inner, end_idx = extract_balanced_brackets(code, start_bracket)
        if end_idx != -1:
            code = code[:start_pos] + f"【待补充：{inner.strip()}】" + code[end_idx:]
        else:
            break

    # 4. 彻底移除所有 #let 定义（包括跨行宏定义与嵌套表达式）
    while True:
        m = re.search(r'#let\s+[a-zA-Z0-9_-]+(?:\([^)]*\))?\s*=', code)
        if not m:
            break
        start_pos = m.start()
        bracket_pos = code.find('[', m.end())
        line_end = code.find('\n', m.end())
        if bracket_pos != -1 and (line_end == -1 or bracket_pos - m.end() < 100):
            _, end_idx = extract_balanced_brackets(code, bracket_pos)
            if end_idx != -1:
                while end_idx < len(code) and code[end_idx] in [']', ')', ';', ' ']:
                    end_idx += 1
                code = code[:start_pos] + code[end_idx:]
                continue
        code = code[:start_pos] + (code[line_end:] if line_end != -1 else '')
    
    # 5. 替换三线表宏并修复 table.header
    code = re.sub(r'\bthree-line-table\b', 'table', code)
    code = re.sub(r'\bheader:\s*table\.header\b', 'table.header', code)
    
    # 6. 提取并安全标记 #align(...)
    code = replace_align_blocks(code)
    
    # 7. 解包剩余 #text(...)
    while re.search(r'#text\([^)]*\)\[([\s\S]*?)\]', code):
        code = re.sub(r'#text\([^)]*\)\[([\s\S]*?)\]', r'\1', code)
        
    # 8. 模式判定：若存在 conf 元数据或正文中存在多个一级章节标题，自动激活学术方案模式
    h1_in_raw = len(re.findall(r'^=\s+(.*)$', code, re.MULTILINE))
    has_conf_meta = bool(meta.get('title'))
    if has_conf_meta or h1_in_raw > 1:
        is_paper_mode = True
        
    lines = code.splitlines()
    clean_lines = []
    
    # 注入文档元信息 (Title, Subtitle, Authors, Abstract, Keywords)
    if is_paper_mode and has_conf_meta:
        if meta.get('title'):
            clean_lines.append(f"\n[[[DOCUMENTTITLE]]] {meta['title']} [[[ENDDOCUMENTTITLE]]]\n")
        if meta.get('subtitle'):
            clean_lines.append(f"\n[[[DOCUMENTSUBTITLE]]] {meta['subtitle']} [[[ENDDOCUMENTSUBTITLE]]]\n")
        if meta.get('authors'):
            clean_lines.append(f"\n[[[DOCUMENTAUTHOR]]] {meta['authors']} [[[ENDDOCUMENTAUTHOR]]]\n")
        if meta.get('abstract'):
            clean_lines.append(f"\n[[[DOCUMENTABSTRACT]]] **【摘要】** {meta['abstract']} [[[ENDDOCUMENTABSTRACT]]]\n")
        if meta.get('keywords'):
            clean_lines.append(f"\n[[[DOCUMENTKEYWORDS]]] **【关键词】** {meta['keywords']} [[[ENDDOCUMENTKEYWORDS]]]\n")
            
    h1_cnt = 0
    h2_cnt = 0
    h3_cnt = 0
    h4_cnt = 0
    h5_cnt = 0
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            clean_lines.append("")
            continue
        if stripped.startswith('//'):
            continue
        if stripped.startswith('#') and not any(stripped.startswith(prefix) for prefix in ['#table', '#figure', '#image', '#grid', '#rect', '#box', '#list', '#enum', '#link']):
            continue
            
        h_match = re.match(r'^(={1,5})\s+(.*)$', stripped)
        if h_match:
            eqs, title_body = h_match.groups()
            level = len(eqs)
            title_text = title_body.strip()
            
            # 检查标题是否自带序号或阶段前缀
            has_existing_number = bool(re.match(
                r'^(?:[一二三四五六七八九十百]+[、\.\s]|第[一二三四五六七八九十\d]+[步章节条周期次阶段]|机制[一二三四五六七八九十\d]+|Q\d+|[（(][\d一二三四五六七八九十]+[)）]|\d+(?:\.\d+)*[\s\.\、])',
                title_text
            ))
            
            if is_paper_mode:
                # 学术方案模式：保持标准 1, 1.1, 1.1.1 层次
                if level == 1:
                    h1_cnt += 1
                    h2_cnt = 0
                    h3_cnt = 0
                    h4_cnt = 0
                    h5_cnt = 0
                    prefix = f"{h1_cnt} " if not has_existing_number else ""
                    clean_lines.append(f"= {prefix}{title_text}")
                elif level == 2:
                    h2_cnt += 1
                    h3_cnt = 0
                    h4_cnt = 0
                    h5_cnt = 0
                    prefix = f"{h1_cnt}.{h2_cnt} " if not has_existing_number else ""
                    clean_lines.append(f"== {prefix}{title_text}")
                elif level == 3:
                    h3_cnt += 1
                    h4_cnt = 0
                    h5_cnt = 0
                    prefix = f"{h1_cnt}.{h2_cnt}.{h3_cnt} " if not has_existing_number else ""
                    clean_lines.append(f"=== {prefix}{title_text}")
                elif level == 4:
                    h4_cnt += 1
                    h5_cnt = 0
                    prefix = f"{h1_cnt}.{h2_cnt}.{h3_cnt}.{h4_cnt} " if not has_existing_number else ""
                    clean_lines.append(f"==== {prefix}{title_text}")
                elif level == 5:
                    h5_cnt += 1
                    clean_lines.append(f"===== {title_text}")
            else:
                # 传统公文红头模式：首个 = 映射为标题，== 映射为 一、
                if level == 1 and h1_cnt == 0 and not has_conf_meta:
                    h1_cnt += 1
                    clean_lines.append(f"\n[[[DOCUMENTTITLE]]] {title_text} [[[ENDDOCUMENTTITLE]]]\n")
                elif level == 2 or (level == 1 and h1_cnt > 0):
                    h2_cnt += 1
                    h3_cnt = 0
                    h4_cnt = 0
                    h5_cnt = 0
                    prefix = f"{to_chinese_num(h2_cnt)}、" if not has_existing_number else ""
                    clean_lines.append(f"= {prefix}{title_text}")
                elif level == 3:
                    h3_cnt += 1
                    h4_cnt = 0
                    h5_cnt = 0
                    prefix = f"（{to_chinese_num(h3_cnt)}）" if not has_existing_number else ""
                    clean_lines.append(f"== {prefix}{title_text}")
                elif level == 4:
                    h4_cnt += 1
                    h5_cnt = 0
                    prefix = f"{h4_cnt}. " if not has_existing_number else ""
                    clean_lines.append(f"=== {prefix}{title_text}")
                elif level == 5:
                    h5_cnt += 1
                    prefix = f"（{h5_cnt}）" if not has_existing_number else ""
                    clean_lines.append(f"==== {prefix}{title_text}")
        else:
            clean_lines.append(line)
            
    return "\n".join(clean_lines) + "\n\n"

def postprocess_docx_xml(docx_path: Path):
    """后处理 DOCX 内部 XML：注入 Word [标题] 与居中/副标题/作者格式，清洗占位符并规范段落排版"""
    with zipfile.ZipFile(docx_path, 'r') as zin:
        all_files = {item.filename: zin.read(item.filename) for item in zin.infolist()}
        
    doc_xml = all_files.get("word/document.xml")
    styles_xml = all_files.get("word/styles.xml")
    if not doc_xml:
        return
        
    ns = {'w': NAMESPACES['w']}
    
    # 动态解析样式表中的 styleId 映射
    style_map = {}
    if styles_xml:
        stree = ET.fromstring(styles_xml)
        for s in stree.findall('.//w:style', ns):
            sid = s.attrib.get(f'{{{ns["w"]}}}styleId')
            name_elem = s.find('.//w:name', ns)
            name = name_elem.attrib.get(f'{{{ns["w"]}}}val', '').lower() if name_elem is not None else ''
            if sid:
                style_map[name] = sid
                style_map[sid.lower()] = sid
                
    title_sid = style_map.get('title', 'Title')
    subtitle_sid = style_map.get('subtitle', 'Subtitle')
    author_sid = style_map.get('author', 'Author')
    abstract_sid = style_map.get('abstract', style_map.get('body text', 'Normal'))
    
    tree = ET.fromstring(doc_xml)
    w_pPr = f"{{{ns['w']}}}pPr"
    w_pStyle = f"{{{ns['w']}}}pStyle"
    w_rPr = f"{{{ns['w']}}}rPr"
    w_jc = f"{{{ns['w']}}}jc"
    w_ind = f"{{{ns['w']}}}ind"
    w_val = f"{{{ns['w']}}}val"
    
    font_map = {
        "KaiTi": "楷体",
        "HeiTi": "黑体",
        "FangSong": "仿宋",
        "XiaoBiaoSong": "方正小标宋_GBK",
    }
    
    modified = False
    
    # 排除首行缩进的样式集合
    excluded_indent_styles = {
        "title", "subtitle", "author", "heading 1", "heading 2", "heading 3", "heading 4",
        "1", "2", "3", "4", "caption", "tablecaption", "imagecaption", "sourcecode",
        "table", "normal table", "captionedfigure", title_sid.lower(), subtitle_sid.lower(),
        author_sid.lower()
    }
    
    for p in tree.findall('.//w:p', ns):
        runs = p.findall('.//w:r', ns)
        p_text = "".join("".join(t.text for t in r.findall('.//w:t', ns) if t.text) for r in runs)
        
        # 1. 标题 (Title)
        if "DOCUMENTTITLE" in p_text:
            modified = True
            cleaned = re.sub(r'\[+DOCUMENTTITLE\]+', '', p_text)
            cleaned = re.sub(r'\[+ENDDOCUMENTTITLE\]+', '', cleaned).strip()
            
            first = True
            for r in runs:
                for t in r.findall('.//w:t', ns):
                    if first:
                        t.text = cleaned
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
            pStyle.attrib[w_val] = title_sid
            
            jc = pPr.find('.//w:jc', ns)
            if jc is None:
                jc = ET.Element(w_jc)
                pPr.append(jc)
            jc.attrib[w_val] = "center"
            
            ind = pPr.find('.//w:ind', ns)
            if ind is not None:
                pPr.remove(ind)
            continue
            
        # 2. 副标题 (Subtitle)
        if "DOCUMENTSUBTITLE" in p_text:
            modified = True
            cleaned = re.sub(r'\[+DOCUMENTSUBTITLE\]+', '', p_text)
            cleaned = re.sub(r'\[+ENDDOCUMENTSUBTITLE\]+', '', cleaned).strip()
            first = True
            for r in runs:
                for t in r.findall('.//w:t', ns):
                    if first:
                        t.text = cleaned
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
            pStyle.attrib[w_val] = subtitle_sid
            jc = pPr.find('.//w:jc', ns)
            if jc is None:
                jc = ET.Element(w_jc)
                pPr.append(jc)
            jc.attrib[w_val] = "center"
            ind = pPr.find('.//w:ind', ns)
            if ind is not None:
                pPr.remove(ind)
            continue

        # 3. 署名作者 (Author)
        if "DOCUMENTAUTHOR" in p_text:
            modified = True
            cleaned = re.sub(r'\[+DOCUMENTAUTHOR\]+', '', p_text)
            cleaned = re.sub(r'\[+ENDDOCUMENTAUTHOR\]+', '', cleaned).strip()
            first = True
            for r in runs:
                for t in r.findall('.//w:t', ns):
                    if first:
                        t.text = cleaned
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
            pStyle.attrib[w_val] = author_sid
            jc = pPr.find('.//w:jc', ns)
            if jc is None:
                jc = ET.Element(w_jc)
                pPr.append(jc)
            jc.attrib[w_val] = "center"
            ind = pPr.find('.//w:ind', ns)
            if ind is not None:
                pPr.remove(ind)
            continue

        # 4. 摘要与关键词 (Abstract / Keywords)
        if "DOCUMENTABSTRACT" in p_text or "DOCUMENTKEYWORDS" in p_text:
            modified = True
            cleaned = re.sub(r'\[+DOCUMENT(ABSTRACT|KEYWORDS)\]+', '', p_text)
            cleaned = re.sub(r'\[+ENDDOCUMENT(ABSTRACT|KEYWORDS)\]+', '', cleaned).strip()
            first = True
            for r in runs:
                for t in r.findall('.//w:t', ns):
                    if first:
                        t.text = cleaned
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
            pStyle.attrib[w_val] = abstract_sid
            ind = pPr.find('.//w:ind', ns)
            if ind is None:
                ind = ET.Element(w_ind)
                ind.attrib[f"{{{ns['w']}}}firstLineChars"] = "200"
                ind.attrib[f"{{{ns['w']}}}firstLine"] = "480"
                pPr.append(ind)
            continue

        # 5. 自定义 ALIGN 标签
        align_match = re.search(r'\[+ALIGN(CENTER|RIGHT|LEFT):([A-Za-z0-9]+)\]+', p_text)
        if align_match:
            modified = True
            align_dir = align_match.group(1).lower()
            cleaned_body = re.sub(r'\[+ALIGN(CENTER|RIGHT|LEFT):[A-Za-z0-9]+\]+', '', p_text)
            cleaned_body = re.sub(r'\[+ENDALIGN(CENTER|RIGHT|LEFT)\]+', '', cleaned_body).strip()
            
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
            pStyle.attrib[w_val] = subtitle_sid if align_dir == "center" else "Normal"
            jc = pPr.find('.//w:jc', ns)
            if jc is None:
                jc = ET.Element(w_jc)
                pPr.append(jc)
            jc.attrib[w_val] = align_dir
            ind = pPr.find('.//w:ind', ns)
            if ind is not None:
                pPr.remove(ind)
            continue

        # 5.5 自定义 NOINDENT 标签（主送机关或顶格段落）
        if "NOINDENT" in p_text:
            modified = True
            cleaned_body = re.sub(r'\[+NOINDENT\]+', '', p_text).strip()
            first = True
            for r in runs:
                for t in r.findall('.//w:t', ns):
                    if first:
                        t.text = cleaned_body
                        first = False
                    else:
                        t.text = ""
            pPr = p.find('.//w:pPr', ns)
            if pPr is not None:
                ind = pPr.find('.//w:ind', ns)
                if ind is not None:
                    pPr.remove(ind)
            continue

        # 6. 正文段落缩进 (2 字符)
        p_style_elem = p.find('.//w:pStyle', ns)
        p_style_val = (p_style_elem.attrib.get(w_val) if p_style_elem is not None else '').lower()
        has_num = p.find('.//w:numPr', ns) is not None
        
        if not has_num and p_style_val not in excluded_indent_styles:
            if p_style_val in ['bodytext', 'firstparagraph', 'normal', 'a', 'a0', '']:
                pPr = p.find('.//w:pPr', ns)
                if pPr is None:
                    pPr = ET.Element(w_pPr)
                    p.insert(0, pPr)
                ind = pPr.find('.//w:ind', ns)
                if ind is None:
                    ind = ET.Element(w_ind)
                    ind.attrib[f"{{{ns['w']}}}firstLineChars"] = "200"
                    ind.attrib[f"{{{ns['w']}}}firstLine"] = "480"
                    pPr.append(ind)
                    modified = True
                elif not ind.attrib.get(f"{{{ns['w']}}}firstLineChars") and not ind.attrib.get(f"{{{ns['w']}}}firstLine"):
                    ind.attrib[f"{{{ns['w']}}}firstLineChars"] = "200"
                    ind.attrib[f"{{{ns['w']}}}firstLine"] = "480"
                    modified = True

    # 7. 高亮与着色所有 【待补充：...】 标记
    for p in tree.findall('.//w:p', ns):
        runs_list = list(p.findall('.//w:r', ns))
        for r in runs_list:
            t_elem = r.find('.//w:t', ns)
            if t_elem is None or not t_elem.text or '【待补充：' not in t_elem.text:
                continue
            text = t_elem.text
            parts = re.split(r'(【待补充：.*?】)', text)
            if len(parts) <= 1:
                continue
            r_idx = list(p).index(r)
            p.remove(r)
            offset = 0
            for part in parts:
                if not part:
                    continue
                new_r = ET.Element(f"{{{ns['w']}}}r")
                new_rPr = ET.Element(w_rPr)
                new_r.append(new_rPr)
                rPr_orig = r.find('.//w:rPr', ns)
                if rPr_orig is not None:
                    for child in rPr_orig:
                        new_rPr.append(ET.fromstring(ET.tostring(child)))
                if part.startswith('【待补充：') and part.endswith('】'):
                    if new_rPr.find('.//w:b', ns) is None:
                        new_rPr.append(ET.Element(f"{{{ns['w']}}}b"))
                    col = new_rPr.find('.//w:color', ns)
                    if col is None:
                        col = ET.Element(f"{{{ns['w']}}}color")
                        new_rPr.append(col)
                    col.attrib[w_val] = "B91C1C"
                    shd = new_rPr.find('.//w:shd', ns)
                    if shd is None:
                        shd = ET.Element(f"{{{ns['w']}}}shd")
                        new_rPr.append(shd)
                    shd.attrib[w_val] = "clear"
                    shd.attrib[f"{{{ns['w']}}}color"] = "auto"
                    shd.attrib[f"{{{ns['w']}}}fill"] = "FEE2E2"
                new_t = ET.Element(f"{{{ns['w']}}}t")
                new_t.attrib['{http://www.w3.org/XML/1998/namespace}space'] = 'preserve'
                new_t.text = part
                new_r.append(new_t)
                p.insert(r_idx + offset, new_r)
                offset += 1
            modified = True

    # 8. 映射规范表格样式（如三线表）
    table_sid = style_map.get('三线表') or style_map.get('table grid') or style_map.get('ad')
    if table_sid:
        for tbl in tree.findall('.//w:tbl', ns):
            tblPr = tbl.find('.//w:tblPr', ns)
            if tblPr is not None:
                tblStyle = tblPr.find('.//w:tblStyle', ns)
                if tblStyle is not None:
                    curr_val = tblStyle.attrib.get(w_val, '').lower()
                    if curr_val in ['table', 'normal table', 'a1', '']:
                        tblStyle.attrib[w_val] = table_sid
                        modified = True

    if modified:
        all_files["word/document.xml"] = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
        temp_docx = docx_path.with_name(f"temp_{docx_path.name}")
        with zipfile.ZipFile(temp_docx, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
            for fname, data in all_files.items():
                zout.writestr(fname, data)
        temp_docx.replace(docx_path)

def run_publisher(input_path: Path, output_path: Path, template_path: Path = None) -> dict:
    diagnostics = []
    input_path = input_path.resolve()
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not input_path.exists():
        return {
            "status": "FAIL",
            "diagnostics": [f"Input file not found: {input_path}"],
            "output_files": []
        }
        
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

    is_paper_mode = False
    if resolved_template and resolved_template.exists():
        tname = resolved_template.stem.lower()
        if 'paper' in tname or 'report' in tname or 'academic' in tname:
            is_paper_mode = True
        clean_template_numpr(resolved_template)
        ref_arg = [f"--reference-doc={resolved_template}"]
        diagnostics.append(f"Using template: {resolved_template}")
            
    typ_content = input_path.read_text(encoding='utf-8')
    cleaned_typ = preprocess_typst_content(typ_content, is_paper_mode=is_paper_mode)
    
    # 为保证相对路径资产（如 assets/xxx.svg）被正确解析，临时文件生成在源码同级目录
    tmp_typ_path = input_path.parent / f".tmp_{input_path.stem}.typ"
    tmp_typ_path.write_text(cleaned_typ, encoding='utf-8')
        
    try:
        cmd = [
            "pandoc",
            str(tmp_typ_path),
            "-f", "typst",
            "-t", "docx",
            "-o", str(output_path)
        ] + ref_arg
        
        proc = subprocess.run(cmd, cwd=str(input_path.parent), capture_output=True, text=True, encoding='utf-8')
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
                    heading_style_ids = {"Title", "1", "2", "3", "4", "5", "6", "7", "8", "9", "heading 1", "heading 2", "heading 3", "heading 4", "Heading1", "Heading2", "Heading3", "Heading4", "a5", "a7"}
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
        if tmp_typ_path.exists():
            tmp_typ_path.unlink()

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
