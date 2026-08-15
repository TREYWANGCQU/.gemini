# C:\Users\Reaticle\.gemini\config\skills\office-parser\scripts\office_parser.py
import os
import sys
import zipfile
import xml.etree.ElementTree as ET

# Namespaces for OOXML
NS_W = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
NS_S = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}

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
    # Look for files like sheet1.xml, sheet2.xml etc
    sheet_filename = f'xl/worksheets/sheet{sheet_index_1based}.xml'
    try:
        sheet_xml = xlsx_zip.read(sheet_filename)
    except KeyError:
        # Best effort fallback: search zip namelist
        sheet_xml = None
        for name in xlsx_zip.namelist():
            if name.startswith('xl/worksheets/sheet') and name.endswith('.xml'):
                # Try to see if this matches
                if name == f'xl/worksheets/sheet{sheet_index_1based}.xml':
                    sheet_xml = xlsx_zip.read(name)
                    break
        if sheet_xml is None:
            return []
            
    sheet_root = ET.fromstring(sheet_xml)
    rows_data = []
    
    # Track max column reference to align row cells nicely
    for row in sheet_root.findall('.//s:row', NS_S):
        # We need to extract cells and align them. In OOXML, empty cells might be omitted.
        # So we look at cell 'r' references (e.g. A1, B1, D1) to place them in correct slots.
        row_num = row.attrib.get('r')
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
            
        # Convert A, B, C, D... dict into a ordered list
        if cells_dict:
            # Simple column order helper up to Z (extendable if needed)
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
            
            # Trim trailing empty values
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
                # Count non-empty rows
                non_empty_rows = [r for r in rows if any(r)]
                report.append(f"Sheet {idx+1}: '{sheet['name']}' (Total rows: {len(rows)}, Non-empty: {len(non_empty_rows)})")
                
                # Show top 10 rows as preview
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
            
            # Find targeted sheet index
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
            
            # Parse row range if present
            start_row = 1
            end_row = len(rows)
            if row_range_str and ":" in row_range_str:
                parts = row_range_str.split(":")
                if parts[0].isdigit():
                    start_row = max(1, int(parts[0]))
                if parts[1].isdigit():
                    end_row = min(len(rows), int(parts[1]))
                    
            sheet_out = [f"=== SHEET: {sheet_name} (Rows {start_row} to {end_row}) ==="]
            
            # Slice list (0-based list matching 1-based indices)
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
                    # Check if keyword is in any cell
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

def main():
    if len(sys.argv) < 3:
        print("Office Parser Utility (No-Dependencies)")
        print("Usage:")
        print("  python office_parser.py preview <file_path>")
        print("  python office_parser.py full <file_path>         (.docx only)")
        print("  python office_parser.py sheet <file_path> <sheet_name_or_index> [row_range_like_10:50] (.xlsx only)")
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
    else:
        print(f"Error: Unsupported file format '{ext}'. Only .docx and .xlsx are supported.")
        sys.exit(1)

if __name__ == '__main__':
    main()
