---
name: office-parser
description: Parse and analyze modern Office documents (.docx and .xlsx) without any third-party python dependencies, with token-optimized preview and targeted range options.
---

# Office Parser Skill

This skill allows the agent to analyze modern Office files (`.docx` and `.xlsx`) using a local, zero-dependency Python script. It is designed to be token-efficient by offering preview-first and targeted range/keyword-search actions.

## File Locations

- Skill Folder: `C:\Users\Reaticle\.gemini\config\skills\office-parser\`
- Execution Script: `C:\Users\Reaticle\.gemini\config\skills\office-parser\scripts\office_parser.py`

## Available Actions

### 1. Document & Spreadsheet Structure Preview
Get heading outline and first 2000 characters (for `.docx`), or sheet names, row counts, and top 10 rows (for `.xlsx`):
`python "C:\Users\Reaticle\.gemini\config\skills\office-parser\scripts\office_parser.py" preview <file_path>`

### 2. Full Text Extraction (.docx)
Extract all text from a Word document:
`python "C:\Users\Reaticle\.gemini\config\skills\office-parser\scripts\office_parser.py" full <file_path>`

### 3. Specific Sheet Extraction (.xlsx)
Read a specific sheet by name or 1-based index, with optional row range (e.g. `1:50` for first 50 rows):
`python "C:\Users\Reaticle\.gemini\config\skills\office-parser\scripts\office_parser.py" sheet <file_path> <sheet_name_or_index> [row_range]`

### 4. Text/Keyword Search (.docx & .xlsx)
Extract only paragraphs or rows containing the specified search term:
`python "C:\Users\Reaticle\.gemini\config\skills\office-parser\scripts\office_parser.py" search <file_path> <keyword>`

---

## Token Optimization Guidelines

> [!IMPORTANT]
> **PowerShell Path Escaping**: On Windows (especially in PowerShell), if the `<file_path>` contains spaces or curly double quotes (`“` and `”`), do not wrap the path in double quotes. Instead, **always wrap the path in single quotes `'...'`** (e.g., `'d:\path\to\“four”\file.docx'`). This prevents PowerShell from treating curly quotes as string delimiters and splitting the path into multiple arguments.

When the user asks you to analyze, search, or summarize an Office document:
1. **Always run the `preview` action first** to grasp the layout (TOC, Sheet counts, column names) without consuming excessive tokens.
2. Based on the preview and the user's specific request:
   - Use the `sheet` action with row ranges to extract specific parts of a spreadsheet.
   - Use the `search` action to find relevant segments within large files.
   - Only use `full` if the file is small, or the user explicitly asks for a complete full-text extraction/conversion.
