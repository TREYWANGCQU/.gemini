# scripts/office_parser.py
# C:\Users\Reaticle\.gemini\config\skills\office-parser\scripts\office_parser.py
import os
import sys
import zipfile
import xml.etree.ElementTree as ET

# Namespaces for OOXML
NS_W = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
NS_S = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}

# ==============================================================================
# DOCX Parser Section (Zero Third-Party Dependencies)
# ==============================================================================

def parse_docx_paragraphs(file_path):
    """Extract list of paragraphs and their style names from a .docx file."""
    paragraphs = []
    with zipfile.ZipFile(file_path) as docx:
        xml_content = docx.read('word/document.xml')
        root = ET.fromstring(xml_content)
        
        # Traverse all paragraph elements
        for p in root.findall('.//w:p', NS_W):
            text_parts = []
            # Gather all text run elements within this paragraph
            for t in p.findall('.//w:t', NS_W):
                text_parts.append(t.text or "")
            
            p_text = "".join(text_parts).strip()
            
            # Identify headings if style is set
            p_style = "Normal"
            pStyle_elem = p.find('.//w:pStyle', NS_W)
            if pStyle_elem is not None:
                p_style = pStyle_elem.attrib.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', "Normal")
                
            paragraphs.append({'text': p_text, 'style': p_style})
    return paragraphs

def docx_preview(file_path):
    """Return an outline (headings) and the first 2000 characters of text."""
    try:
        paragraphs = parse_docx_paragraphs(file_path)
        
        # 1. Build Heading Outline
        outline = []
        for p in paragraphs:
            if p['style'].startswith('Heading') or 'title' in p['style'].lower() or 'subtitle' in p['style'].lower():
                outline.append(f"- [{p['style']}] {p['text']}")
        
        outline_str = "\n".join(outline) if outline else "(No headings found)"
        
        # 2. Extract first 2000 chars of body text
        full_text = "\n".join([p['text'] for p in paragraphs if p['text']])
        preview_text = full_text[:2000]
        if len(full_text) > 2000:
            preview_text += "\n\n... [Truncated! Total character count: {}]".format(len(full_text))
            
        return f"=== DOCUMENT OUTLINE ===\n{outline_str}\n\n=== TEXT PREVIEW ===\n{preview_text}"
    except Exception as e:
        return f"Error previewing DOCX: {str(e)}"

def docx_full(file_path):
    """Return all text paragraphs."""
    try:
        paragraphs = parse_docx_paragraphs(file_path)
        return "\n".join([p['text'] for p in paragraphs if p['text']])
    except Exception as e:
        return f"Error extracting DOCX: {str(e)}"

def docx_search(file_path, keyword):
    """Return paragraph segments matching keyword."""
    try:
        paragraphs = parse_docx_paragraphs(file_path)
        keyword_lower = keyword.lower()
        matches = []
        for idx, p in enumerate(paragraphs):
            if keyword_lower in p['text'].lower():
                # Provide a bit of context if possible
                context_prev = paragraphs[idx-1]['text'] if idx > 0 and paragraphs[idx-1]['text'] else ""
                context_next = paragraphs[idx+1]['text'] if idx < len(paragraphs)-1 and paragraphs[idx+1]['text'] else ""
                
                match_entry = []
                if context_prev:
                    match_entry.append(f"  [Prev] {context_prev}")
                match_entry.append(f"  [MATCH (Style: {p['style']})] -> {p['text']}")
                if context_next:
                    match_entry.append(f"  [Next] {context_next}")
                
                matches.append("\n".join(match_entry))
                
        if not matches:
            return f"No matches found for keyword: '{keyword}'"
        return f"=== SEARCH RESULTS FOR '{keyword}' ===\n\n" + "\n\n---\n\n".join(matches)
    except Exception as e:
        return f"Error searching DOCX: {str(e)}"

# ==============================================================================
# XLSX Parser Section (Zero Third-Party Dependencies)
# ==============================================================================

def parse_xlsx_shared_strings(xlsx_zip):
    """Extract list of shared strings in Excel workbook."""
    shared_strings = []
    try:
        ss_xml = xlsx_zip.read('xl/sharedStrings.xml')
        ss_root = ET.fromstring(ss_xml)
        for t in ss_root.findall('.//s:t', NS_S):
            shared_strings.append(t.text or "")
    except KeyError:
        pass # No shared strings xml file exists
    return shared_strings

def parse_xlsx_sheets_list(xlsx_zip):
    """Extract sheet metadata list."""
    workbook_xml = xlsx_zip.read('xl/workbook.xml')
    wb_root = ET.fromstring(workbook_xml)
    sheets = []
    for sheet_elem in wb_root.findall('.//s:sheet', NS_S):
        name = sheet_elem.attrib.get('name')
        sheet_id = sheet_elem.attrib.get('sheetId')
        r_id = sheet_elem.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        sheets.append({'name': name, 'sheetId': sheet_id, 'rId': r_id})
    return sheets

def parse_sheet_rows(xlsx_zip, sheet_index_1based, shared_strings):
    """Extract rows of data for a sheet index (1-based)."""
    sheet_filename = f'xl/worksheets/sheet{sheet_index_1based}.xml'
    try:
        sheet_xml = xlsx_zip.read(sheet_filename)
    except KeyError:
        sheet_xml = None
        for name in xlsx_zip.namelist():
            if name.startswith('xl/worksheets/sheet') and name.endswith('.xml'):
                if name == f'xl/worksheets/sheet{sheet_index_1based}.xml':
                    sheet_xml = xlsx_zip.read(name)
                    break
        if sheet_xml is None:
            return []
            
    sheet_root = ET.fromstring(sheet_xml)
    rows_data = []
    
    for row in sheet_root.findall('.//s:row', NS_S):
        cells_dict = {}
        for cell in row.findall('.//s:c', NS_S):
            cell_ref = cell.attrib.get('r') # e.g. B3
            cell_type = cell.attrib.get('t') # e.g. s
            val_elem = cell.find('s:v', NS_S)
            
            val = ""
            if val_elem is not None:
                val = val_elem.text or ""
                if cell_type == 's' and val.isdigit():
                    idx = int(val)
                    if idx < len(shared_strings):
                        val = shared_strings[idx]
            
            # Deduce column letter
            col_letter = "".join([c for c in cell_ref if c.isalpha()])
            cells_dict[col_letter] = val
            
        if cells_dict:
            def col_to_num(col_str):
                num = 0
                for char in col_str:
                    num = num * 26 + (ord(char.upper()) - ord('A') + 1)
                return num
                
            sorted_cols = sorted(cells_dict.keys(), key=col_to_num)
            max_col_num = col_to_num(sorted_cols[-1]) if sorted_cols else 0
            
            row_cells = [""] * max_col_num
            for col, val in cells_dict.items():
                col_idx = col_to_num(col) - 1
                if col_idx < len(row_cells):
                    row_cells[col_idx] = val
            
            while row_cells and not row_cells[-1]:
                row_cells.pop()
                
            rows_data.append(row_cells)
        else:
            rows_data.append([])
            
    return rows_data

def xlsx_preview(file_path):
    """List sheets, row counts, table headers, and first 10 rows."""
    try:
        with zipfile.ZipFile(file_path) as xlsx:
            shared_strings = parse_xlsx_shared_strings(xlsx)
            sheets = parse_xlsx_sheets_list(xlsx)
            
            report = ["=== SPREADSHEET STRUCTURE ==="]
            for idx, sheet in enumerate(sheets):
                rows = parse_sheet_rows(xlsx, idx + 1, shared_strings)
                non_empty_rows = [r for r in rows if any(r)]
                report.append(f"Sheet {idx+1}: '{sheet['name']}' (Total rows: {len(rows)}, Non-empty: {len(non_empty_rows)})")
                
                if non_empty_rows:
                    report.append("  [First 10 rows preview]")
                    for r_idx, row in enumerate(non_empty_rows[:10]):
                        row_str = " | ".join([str(item) for item in row])
                        report.append(f"    Row {r_idx+1}: {row_str}")
                    if len(non_empty_rows) > 10:
                        report.append(f"    ... and {len(non_empty_rows) - 10} more rows")
                else:
                    report.append("  (Empty sheet)")
                report.append("")
                
            return "\n".join(report)
    except Exception as e:
        return f"Error previewing XLSX: {str(e)}"

def xlsx_sheet(file_path, sheet_name_or_index, row_range_str=""):
    """Extract specific sheet with optional range filter (e.g. '1:100')."""
    try:
        with zipfile.ZipFile(file_path) as xlsx:
            shared_strings = parse_xlsx_shared_strings(xlsx)
            sheets = parse_xlsx_sheets_list(xlsx)
            
            sheet_idx = None
            sheet_name = ""
            
            if sheet_name_or_index.isdigit():
                idx_val = int(sheet_name_or_index) - 1
                if 0 <= idx_val < len(sheets):
                    sheet_idx = idx_val + 1
                    sheet_name = sheets[idx_val]['name']
            else:
                for idx, s in enumerate(sheets):
                    if s['name'].lower() == sheet_name_or_index.lower():
                        sheet_idx = idx + 1
                        sheet_name = s['name']
                        break
                        
            if sheet_idx is None:
                sheet_list = ", ".join([f"'{s['name']}'" for s in sheets])
                return f"Error: Sheet '{sheet_name_or_index}' not found. Available sheets: {sheet_list}"
                
            rows = parse_sheet_rows(xlsx, sheet_idx, shared_strings)
            
            start_row = 1
            end_row = len(rows)
            if row_range_str and ":" in row_range_str:
                parts = row_range_str.split(":")
                if parts[0].isdigit():
                    start_row = max(1, int(parts[0]))
                if parts[1].isdigit():
                    end_row = min(len(rows), int(parts[1]))
                    
            sheet_out = [f"=== SHEET: {sheet_name} (Rows {start_row} to {end_row}) ==="]
            for r_idx in range(start_row - 1, end_row):
                if r_idx < len(rows):
                    row = rows[r_idx]
                    row_str = " | ".join([str(item) for item in row])
                    sheet_out.append(f"Row {r_idx+1}: {row_str}")
                    
            return "\n".join(sheet_out)
    except Exception as e:
        return f"Error reading sheet: {str(e)}"

def xlsx_search(file_path, keyword):
    """Search all cells in all sheets for keyword."""
    try:
        with zipfile.ZipFile(file_path) as xlsx:
            shared_strings = parse_xlsx_shared_strings(xlsx)
            sheets = parse_xlsx_sheets_list(xlsx)
            keyword_lower = keyword.lower()
            
            results = [f"=== SEARCH RESULTS FOR '{keyword}' ==="]
            found = False
            
            for idx, sheet in enumerate(sheets):
                rows = parse_sheet_rows(xlsx, idx + 1, shared_strings)
                sheet_matches = []
                for r_idx, row in enumerate(rows):
                    row_str_combined = " ".join([str(item) for item in row]).lower()
                    if keyword_lower in row_str_combined:
                        cell_match = " | ".join([str(item) for item in row])
                        sheet_matches.append(f"  Row {r_idx+1}: {cell_match}")
                        
                if sheet_matches:
                    found = True
                    results.append(f"\nSheet '{sheet['name']}':")
                    results.extend(sheet_matches)
                    
            if not found:
                return f"No matches found in workbook for keyword: '{keyword}'"
            return "\n".join(results)
    except Exception as e:
        return f"Error searching XLSX: {str(e)}"

# ==============================================================================
# PDF Parser Section (Vector PDF Support with Scanned Image Guard)
# ==============================================================================

def ensure_pypdf():
    """Lazy-import pypdf with informative error if missing."""
    try:
        import pypdf
        return pypdf
    except ImportError:
        print("Error: 'pypdf' library is required to process PDF files.")
        print("Please install it in your Python environment: pip install pypdf")
        sys.exit(1)

def inspect_pdf_page(page):
    """
    Inspect page and return (text, state, reason).
    State: 'VECTOR_TEXT', 'SCANNED_IMAGE', 'BLANK_PAGE', 'SPARSE_TEXT'
    """
    text = (page.extract_text() or "").strip()
    has_images = False
    try:
        if getattr(page, 'images', None) and len(page.images) > 0:
            has_images = True
    except Exception:
        pass
    
    if len(text) >= 15:
        return text, 'VECTOR_TEXT', ""
    elif has_images and len(text) < 15:
        return text, 'SCANNED_IMAGE', f"Contains image(s) with negligible vector text ({len(text)} chars)"
    elif len(text) == 0 and not has_images:
        return text, 'BLANK_PAGE', "Completely empty page"
    else:
        return text, 'SPARSE_TEXT' if text else 'BLANK_PAGE', f"Sparse text ({len(text)} chars)"

def extract_pdf_outline_tree(outline, reader, level=0):
    """Recursively extract PDF bookmarks/outline items."""
    items = []
    if not outline:
        return items
    for item in outline:
        if isinstance(item, list):
            items.extend(extract_pdf_outline_tree(item, reader, level + 1))
        else:
            title = getattr(item, 'title', str(item))
            page_num = None
            try:
                page_num = reader.get_destination_page_number(item) + 1
            except Exception:
                pass
            items.append((level, title, page_num))
    return items

def pdf_preview(file_path):
    """Return metadata, outline, sampled pages, and page health stats."""
    pypdf = ensure_pypdf()
    try:
        reader = pypdf.PdfReader(file_path)
        total_pages = len(reader.pages)
        meta = reader.metadata or {}
        title = meta.get('/Title', '') or os.path.basename(file_path)
        author = meta.get('/Author', '') or "Unknown"
        
        report = ["=== PDF DOCUMENT PREVIEW ==="]
        report.append(f"Title: {title}")
        report.append(f"Author: {author}")
        report.append(f"Total Pages: {total_pages}\n")
        
        # 1. Outline extraction
        outline_items = extract_pdf_outline_tree(reader.outline, reader)
        report.append("=== OUTLINE / BOOKMARKS ===")
        if outline_items:
            for lvl, ot, pn in outline_items[:20]:
                indent = "  " * lvl
                p_str = f" (Page {pn})" if pn else ""
                report.append(f"{indent}- {ot}{p_str}")
            if len(outline_items) > 20:
                report.append(f"  ... [{len(outline_items) - 20} more outline items omitted]")
        else:
            report.append("(No outline bookmarks found)")
        report.append("")
        
        # 2. Page sampling (first 3-5 pages or up to 2000 chars)
        report.append("=== TEXT PREVIEW (Sample Pages) ===")
        sample_text = []
        vector_pages = 0
        scanned_pages = 0
        blank_pages = 0
        
        accumulated_chars = 0
        sample_limit = min(5, total_pages)
        
        for i in range(sample_limit):
            page = reader.pages[i]
            txt, state, reason = inspect_pdf_page(page)
            if state == 'SCANNED_IMAGE':
                scanned_pages += 1
                sample_text.append(f"[Page {i+1}: WARNING - Scanned bitmap image detected. Auto-skipped]")
            elif state == 'BLANK_PAGE':
                blank_pages += 1
                sample_text.append(f"[Page {i+1}: Blank page skipped]")
            else:
                vector_pages += 1
                page_sample = txt[:500]
                if len(txt) > 500:
                    page_sample += f" ... (Page {i+1} truncated, total {len(txt)} chars)"
                sample_text.append(f"--- Page {i+1} ---\n{page_sample}")
                accumulated_chars += len(page_sample)
                if accumulated_chars >= 2000:
                    sample_text.append("\n... [Preview text truncated at 2000 chars]")
                    break
                    
        report.append("\n\n".join(sample_text))
        report.append("")
        report.append("=== PAGE HEALTH & STATS ===")
        report.append(f"Sampled {sample_limit}/{total_pages} pages: {vector_pages} Vector text, {scanned_pages} Scanned image (skipped), {blank_pages} Blank")
        if vector_pages == 0 and scanned_pages > 0:
            report.append("[ALARM: Sample pages indicate this is a SCANNED IMAGE PDF without embedded text layer. OCR is required!]")
            
        return "\n".join(report)
    except Exception as e:
        return f"Error previewing PDF: {str(e)}"

def pdf_outline(file_path):
    """Extract full hierarchical outline tree."""
    pypdf = ensure_pypdf()
    try:
        reader = pypdf.PdfReader(file_path)
        outline_items = extract_pdf_outline_tree(reader.outline, reader)
        if not outline_items:
            return f"No outline bookmarks found in PDF: '{os.path.basename(file_path)}'"
            
        report = [f"=== OUTLINE: {os.path.basename(file_path)} ==="]
        for lvl, ot, pn in outline_items:
            indent = "  " * lvl
            p_str = f" [Page {pn}]" if pn else ""
            report.append(f"{indent}- {ot}{p_str}")
        return "\n".join(report)
    except Exception as e:
        return f"Error extracting PDF outline: {str(e)}"

def pdf_page(file_path, page_range_str):
    """Extract specific single page or slice range (e.g. '5' or '5:10')."""
    pypdf = ensure_pypdf()
    try:
        reader = pypdf.PdfReader(file_path)
        total_pages = len(reader.pages)
        
        start_p = 1
        end_p = 1
        if ":" in page_range_str:
            parts = page_range_str.split(":")
            if parts[0].isdigit():
                start_p = max(1, int(parts[0]))
            if parts[1].isdigit():
                end_p = min(total_pages, int(parts[1]))
        elif page_range_str.isdigit():
            start_p = max(1, min(total_pages, int(page_range_str)))
            end_p = start_p
        else:
            return f"Error: Invalid page argument '{page_range_str}'. Expected single page (e.g. '5') or range (e.g. '5:10')."
            
        if start_p > end_p:
            return f"Error: Start page {start_p} cannot be greater than end page {end_p}."
            
        results = [f"=== EXTRACTED PAGES {start_p} TO {end_p} (Total in doc: {total_pages}) ==="]
        for p_num in range(start_p, end_p + 1):
            page = reader.pages[p_num - 1]
            txt, state, reason = inspect_pdf_page(page)
            results.append(f"\n=== PAGE {p_num} ===")
            if state == 'SCANNED_IMAGE':
                results.append(f"[WARNING: Page {p_num} is a scanned bitmap image with no vector text. Auto-skipped. Reason: {reason}]")
            elif state == 'BLANK_PAGE':
                results.append(f"(Blank page)")
            else:
                results.append(txt)
                
        return "\n".join(results)
    except Exception as e:
        return f"Error extracting PDF pages: {str(e)}"

def pdf_search(file_path, keyword):
    """Search for keyword across all pages with context and page number tracking."""
    pypdf = ensure_pypdf()
    try:
        reader = pypdf.PdfReader(file_path)
        keyword_lower = keyword.lower()
        total_pages = len(reader.pages)
        
        matches = []
        matched_pages = set()
        
        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            txt, state, _ = inspect_pdf_page(page)
            if state == 'SCANNED_IMAGE' or not txt:
                continue
                
            if keyword_lower in txt.lower():
                matched_pages.add(page_num)
                lines = [l.strip() for l in txt.splitlines() if l.strip()]
                for l_idx, line in enumerate(lines):
                    if keyword_lower in line.lower():
                        prev_l = lines[l_idx - 1] if l_idx > 0 else ""
                        next_l = lines[l_idx + 1] if l_idx < len(lines) - 1 else ""
                        entry = [f"=== PAGE {page_num} (Match) ==="]
                        if prev_l:
                            entry.append(f"  [Prev] {prev_l}")
                        entry.append(f"  [MATCH] -> {line}")
                        if next_l:
                            entry.append(f"  [Next] {next_l}")
                        matches.append("\n".join(entry))
                        
        if not matches:
            return f"No matches found in PDF for keyword: '{keyword}'"
            
        pages_sorted = sorted(list(matched_pages))
        summary_header = [
            f"=== SEARCH RESULTS FOR '{keyword}' ===",
            f"Total Matches: {len(matches)} | Discovered in Pages: {pages_sorted}\n"
        ]
        return "\n".join(summary_header) + "\n\n---\n\n".join(matches)
    except Exception as e:
        return f"Error searching PDF: {str(e)}"

def pdf_full(file_path):
    """Extract full text of PDF with automatic scanned-image warnings."""
    pypdf = ensure_pypdf()
    try:
        reader = pypdf.PdfReader(file_path)
        total_pages = len(reader.pages)
        out = [f"=== FULL TEXT EXTRACTION (Total pages: {total_pages}) ==="]
        
        scanned_pages = 0
        for idx, page in enumerate(reader.pages):
            p_num = idx + 1
            txt, state, _ = inspect_pdf_page(page)
            out.append(f"\n=== PAGE {p_num} ===")
            if state == 'SCANNED_IMAGE':
                scanned_pages += 1
                out.append(f"[WARNING: Page {p_num} contains only scanned bitmap image. Auto-skipped]")
            elif state == 'BLANK_PAGE':
                out.append("(Blank page)")
            else:
                out.append(txt)
                
        if scanned_pages == total_pages:
            out.append("\n[ALARM: All pages are scanned images. No text could be extracted. OCR required.]")
            
        return "\n".join(out)
    except Exception as e:
        return f"Error extracting full PDF: {str(e)}"

# ==============================================================================
# CLI Entrypoint
# ==============================================================================

def main():
    if len(sys.argv) < 3:
        print("Office & PDF Parser Utility")
        print("Usage:")
        print("  python office_parser.py preview <file_path>")
        print("  python office_parser.py full <file_path>         (.docx / .pdf)")
        print("  python office_parser.py page <file_path> <page_or_range> (.pdf only, e.g. '5' or '10:20')")
        print("  python office_parser.py outline <file_path>      (.pdf only)")
        print("  python office_parser.py sheet <file_path> <sheet_name_or_index> [row_range] (.xlsx only)")
        print("  python office_parser.py search <file_path> <keyword>")
        sys.exit(1)
        
    action = sys.argv[1].lower()
    file_path = sys.argv[2]
    
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        sys.exit(1)
        
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.docx':
        if action == 'preview':
            print(docx_preview(file_path))
        elif action == 'full':
            print(docx_full(file_path))
        elif action == 'search':
            if len(sys.argv) < 4:
                print("Error: Missing search keyword argument.")
                sys.exit(1)
            print(docx_search(file_path, sys.argv[3]))
        else:
            print(f"Error: Unsupported action '{action}' for .docx files.")
            sys.exit(1)
            
    elif ext == '.xlsx':
        if action == 'preview':
            print(xlsx_preview(file_path))
        elif action == 'sheet':
            if len(sys.argv) < 4:
                print("Error: Missing sheet name or 1-based index argument.")
                sys.exit(1)
            sheet_arg = sys.argv[3]
            range_arg = sys.argv[4] if len(sys.argv) > 4 else ""
            print(xlsx_sheet(file_path, sheet_arg, range_arg))
        elif action == 'search':
            if len(sys.argv) < 4:
                print("Error: Missing search keyword argument.")
                sys.exit(1)
            print(xlsx_search(file_path, sys.argv[3]))
        else:
            print(f"Error: Unsupported action '{action}' for .xlsx files.")
            sys.exit(1)
            
    elif ext == '.pdf':
        if action == 'preview':
            print(pdf_preview(file_path))
        elif action == 'page':
            if len(sys.argv) < 4:
                print("Error: Missing page argument (e.g. '5' or '10:20').")
                sys.exit(1)
            print(pdf_page(file_path, sys.argv[3]))
        elif action == 'outline':
            print(pdf_outline(file_path))
        elif action == 'search':
            if len(sys.argv) < 4:
                print("Error: Missing search keyword argument.")
                sys.exit(1)
            print(pdf_search(file_path, sys.argv[3]))
        elif action == 'full':
            print(pdf_full(file_path))
        else:
            print(f"Error: Unsupported action '{action}' for .pdf files.")
            sys.exit(1)
            
    else:
        print(f"Error: Unsupported file format '{ext}'. Supported formats: .docx, .xlsx, .pdf")
        sys.exit(1)

if __name__ == '__main__':
    main()
