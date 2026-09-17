# -*- coding: utf-8 -*-
# scripts/archiver.py
import os
import sys
import re
import json
import shutil
import zipfile
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

NAMESPACES = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
}
W_NS = f"{{{NAMESPACES['w']}}}"
R_NS = f"{{{NAMESPACES['r']}}}"

def extract_media_and_rels(docx_zip, staging_assets_dir: Path) -> dict:
    staging_assets_dir.mkdir(parents=True, exist_ok=True)
    rid_to_rel_path = {}
    
    # 解析关系表
    rels_file = "word/_rels/document.xml.rels"
    if rels_file in docx_zip.namelist():
        rels_xml = docx_zip.read(rels_file)
        tree = ET.fromstring(rels_xml)
        for rel in tree.findall('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
            r_id = rel.attrib.get('Id')
            target = rel.attrib.get('Target')
            target_mode = rel.attrib.get('TargetMode', '')
            if target and target_mode != 'External' and 'media/' in target:
                media_path_in_zip = f"word/{target.lstrip('/')}"
                if media_path_in_zip in docx_zip.namelist():
                    img_data = docx_zip.read(media_path_in_zip)
                    ext = Path(target).suffix or ".png"
                    out_img_name = f"image_{len(rid_to_rel_path) + 1}{ext}"
                    out_img_file = staging_assets_dir / out_img_name
                    out_img_file.write_bytes(img_data)
                    rid_to_rel_path[r_id] = f"assets/{out_img_name}"
                    
    return rid_to_rel_path

def parse_paragraph_heuristic(p, rid_map: dict) -> str:
    # 检查是否包含图片
    blip_nodes = p.findall(f'.//{W_NS}drawing//{{http://schemas.openxmlformats.org/drawingml/2006/main}}blip')
    if blip_nodes:
        for blip in blip_nodes:
            embed_id = blip.attrib.get(f'{R_NS}embed')
            if embed_id in rid_map:
                return f'#figure(\n  image("{rid_map[embed_id]}"),\n  caption: [插图],\n)\n'
                
    text_nodes = p.findall(f'.//{W_NS}t')
    text = "".join([t.text for t in text_nodes if t.text]).strip()
    if not text:
        return ""
        
    # 清理行首全角/半角空格
    text = re.sub(r'^[ \t\u3000]+', '', text)
    
    # 启发式大纲判定
    # 1级章标题: 第X章
    if re.match(r'^第[一二三四五六七八九十百]+[章]\s*[:：]?', text):
        return f'= {text}\n'
    # 多级数字序号: 4.1.1.1 或 1.1.1.1 -> 4级
    elif re.match(r'^\d+\.\d+\.\d+\.\d+\s+', text):
        clean_title = re.sub(r'^\d+\.\d+\.\d+\.\d+\s*', '', text)
        return f'==== {clean_title}\n'
    # 3级数字序号: 4.1.1 或 1.1.1 -> 3级
    elif re.match(r'^\d+\.\d+\.\d+\s+', text):
        clean_title = re.sub(r'^\d+\.\d+\.\d+\s*', '', text)
        return f'=== {clean_title}\n'
    # 2级数字序号: 4.1 或 1.1 -> 2级
    elif re.match(r'^\d+\.\d+\s+', text):
        clean_title = re.sub(r'^\d+\.\d+\s*', '', text)
        return f'== {clean_title}\n'
    # 1级标题: 一、 或 第一节
    elif re.match(r'^(第[一二三四五六七八九十百]+[节]|[一二三四五六七八九十]+、)', text):
        clean_title = re.sub(r'^(第[一二三四五六七八九十百]+[节]|[一二三四五六七八九十]+、)\s*', '', text)
        return f'= {clean_title}\n'
    # 2级标题: （一）
    elif re.match(r'^[（\(][一二三四五六七八九十]+[）\)]', text):
        clean_title = re.sub(r'^[（\(][一二三四五六七八九十]+[）\)]\s*', '', text)
        return f'== {clean_title}\n'
    # 3级标题: 1. 或 1、
    elif re.match(r'^([0-9]+\.|[0-9]+、)\s+', text):
        clean_title = re.sub(r'^([0-9]+\.|[0-9]+、)\s*', '', text)
        return f'=== {clean_title}\n'
    # 4级标题: （1）
    elif re.match(r'^[（\(][0-9]+[）\)]', text):
        clean_title = re.sub(r'^[（\(][0-9]+[）\)]\s*', '', text)
        return f'==== {clean_title}\n'
        
    # 普通正文
    return f'{text}\n'

def parse_table_element(tbl) -> str:
    rows = tbl.findall(f'{W_NS}tr')
    if not rows:
        return ""
        
    grid_cols = tbl.findall(f'{W_NS}tblGrid/{W_NS}gridCol')
    col_count = len(grid_cols) if grid_cols else 0
    
    table_lines = []
    for tr in rows:
        cells = tr.findall(f'{W_NS}tc')
        if not col_count:
            col_count = len(cells)
        for tc in cells:
            p_nodes = tc.findall(f'{W_NS}p')
            cell_texts = []
            for p in p_nodes:
                t_nodes = p.findall(f'.//{W_NS}t')
                t = "".join([n.text for n in t_nodes if n.text]).strip()
                if t:
                    cell_texts.append(t)
            cell_content = " ".join(cell_texts)
            
            # 跨行跨列解析
            grid_span = tc.find(f'{W_NS}tcPr/{W_NS}gridSpan')
            colspan = int(grid_span.attrib.get(f'{W_NS}val', '1')) if grid_span is not None else 1
            
            if colspan > 1:
                table_lines.append(f'  table.cell(colspan: {colspan})[{cell_content}],')
            else:
                table_lines.append(f'  [{cell_content}],')
                
    cols_def = ", ".join(["1fr"] * max(col_count, 1))
    return f'#table(\n  columns: ({cols_def}),\n' + "\n".join(table_lines) + "\n)\n"

def stage1_ingestion(docx_path: Path, staging_dir: Path) -> dict:
    staging_dir.mkdir(parents=True, exist_ok=True)
    staging_assets = staging_dir / "assets"
    
    with zipfile.ZipFile(docx_path, 'r') as z:
        rid_map = extract_media_and_rels(z, staging_assets)
        doc_xml = z.read("word/document.xml")
        tree = ET.fromstring(doc_xml)
        
    body = tree.find(f'{W_NS}body')
    if body is None:
        return {"status": "FAIL", "diagnostics": ["Empty document body"], "output_files": []}
        
    typst_parts = []
    heading_count = 0
    table_count = 0
    
    for elem in body:
        if elem.tag == f'{W_NS}p':
            p_out = parse_paragraph_heuristic(elem, rid_map)
            if p_out:
                if p_out.startswith("="):
                    heading_count += 1
                typst_parts.append(p_out)
        elif elem.tag == f'{W_NS}tbl':
            tbl_out = parse_table_element(elem)
            if tbl_out:
                table_count += 1
                typst_parts.append(tbl_out)
                
    staging_typ = staging_dir / "staging.typ"
    staging_typ.write_text("\n".join(typst_parts), encoding='utf-8')
    
    return {
        "status": "SUCCESS",
        "diagnostics": [
            f"Extracted {len(rid_map)} images to assets/",
            f"Recovered {heading_count} headings",
            f"Normalized {table_count} tables",
            f"Saved staging file at {staging_typ}"
        ],
        "output_files": [str(staging_typ)]
    }

def stage2_reconcile(staging_dir: Path, target_main_path: Path) -> dict:
    staging_typ = staging_dir / "staging.typ"
    if not staging_typ.exists() or not target_main_path.exists():
        return {
            "status": "FAIL",
            "diagnostics": [f"Missing staging ({staging_typ}) or main ({target_main_path})"],
            "output_files": []
        }
        
    main_text = target_main_path.read_text(encoding='utf-8')
    staging_text = staging_typ.read_text(encoding='utf-8')
    
    # 提取 main.typ 头部模板与宏（从文件起始到第一个一级标题 '=' 之前的所有内容）
    heading_match = re.search(r'(?m)^=\s+', main_text)
    if heading_match:
        header_block = main_text[:heading_match.start()].strip()
    else:
        main_lines = main_text.splitlines()
        header_lines = []
        for line in main_lines:
            if line.strip().startswith('#') or line.strip().startswith('//') or not line.strip():
                header_lines.append(line)
            else:
                break
        header_block = "\n".join(header_lines).strip()
        
    reconciled_content = (header_block + "\n\n" + staging_text) if header_block else staging_text
    
    # 备份原 main.typ
    backup_path = target_main_path.with_suffix(".typ.bak")
    shutil.copy2(target_main_path, backup_path)
    
    # 写入新内容
    target_main_path.write_text(reconciled_content, encoding='utf-8')
    
    # 合并 assets
    staging_assets = staging_dir / "assets"
    target_assets = target_main_path.parent / "assets"
    if staging_assets.exists():
        target_assets.mkdir(parents=True, exist_ok=True)
        for img in staging_assets.glob('*'):
            shutil.copy2(img, target_assets / img.name)
            
    return {
        "status": "SUCCESS",
        "diagnostics": [
            f"Preserved header macros ({len(header_block.splitlines())} lines)",
            f"Created backup at {backup_path}",
            f"Safely reconciled main.typ at {target_main_path}"
        ],
        "output_files": [str(target_main_path)]
    }

def main():
    parser = argparse.ArgumentParser(description="Word to Typst Archiver & Reconciler")
    parser.add_argument("--input", "-i", required=True, help="Path to input .docx")
    parser.add_argument("--output-dir", "-o", default=".staging", help="Staging or archive output dir")
    parser.add_argument("--target-main", "-m", default=None, help="Target main.typ for reconcile")
    parser.add_argument("--mode", choices=["stage1", "reconcile", "archive"], default="stage1")
    
    args = parser.parse_args()
    docx_path = Path(args.input)
    staging_dir = Path(args.output_dir)
    
    s1_res = stage1_ingestion(docx_path, staging_dir)
    if s1_res["status"] == "FAIL":
        print(json.dumps(s1_res, ensure_ascii=False, indent=2))
        sys.exit(1)
        
    if args.mode == "reconcile" and args.target_main:
        s2_res = stage2_reconcile(staging_dir, Path(args.target_main))
        print(json.dumps(s2_res, ensure_ascii=False, indent=2))
    elif args.mode == "archive":
        # 封装为独立归档工程
        staging_typ = staging_dir / "staging.typ"
        archived_typ = staging_dir / "main.typ"
        header = '#import "@local/report:0.1.0": *\n\n#show: report.with()\n\n'
        archived_typ.write_text(header + staging_typ.read_text(encoding="utf-8"), encoding="utf-8")
        print(json.dumps({
            "status": "SUCCESS",
            "diagnostics": ["Packaged as standalone Typst archive project"],
            "output_files": [str(archived_typ)]
        }, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(s1_res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
