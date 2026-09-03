---
name: office-parser
description: Parse and analyze modern Office documents (.docx, .xlsx) and vector PDFs with token-optimized preview, precise slice extraction, and scanned-image alarm defenses.
---

# Office & PDF Parser Skill

This skill allows the agent to analyze modern Office files (`.docx`, `.xlsx`) and Vector PDF documents (`.pdf`) using a token-efficient CLI utility. It is engineered to protect context window limits for `/collector` and provide verifiable fact-slices for `/verifier`.

## File Locations

- Skill Folder: `C:\Users\Reaticle\.gemini\config\skills\office-parser\`
- Execution Script: `C:\Users\Reaticle\.gemini\config\skills\office-parser\scripts\office_parser.py`

## Available Actions

### 1. Document Structure Preview (All Formats)
Extract metadata, outline headings/TOC, health stats, and sample text truncated at 2000 characters:
```powershell
python "C:\Users\Reaticle\.gemini\config\skills\office-parser\scripts\office_parser.py" preview '<file_path>'
```
- **`.docx`**: Paragraph style outline + first 2000 characters.
- **`.xlsx`**: Sheet names, total rows, non-empty counts, top 10 rows preview.
- **`.pdf`**: Document metadata, bookmarks/outline tree, first 3~5 pages sample (<=2000 chars), vector vs scanned image health stats.

### 2. Precise Page / Slice Extraction (`.pdf` only) — *Crucial for `/verifier`*
Extract a specific page or continuous page slice with explicit `=== PAGE N ===` verification anchors:
```powershell
# Single page
python "C:\Users\Reaticle\.gemini\config\skills\office-parser\scripts\office_parser.py" page '<file_path>' 21

# Page range / slice
python "C:\Users\Reaticle\.gemini\config\skills\office-parser\scripts\office_parser.py" page '<file_path>' 21:25
```
> [!NOTE]
> Scanned bitmap pages without vector text are automatically identified and warned with `[WARNING: Page X is a scanned bitmap image. Auto-skipped]`, preventing blank noise from consuming tokens.

### 3. Full Outline / Bookmarks Tree (`.pdf` only)
Extract the complete bookmark and section hierarchy:
```powershell
python "C:\Users\Reaticle\.gemini\config\skills\office-parser\scripts\office_parser.py" outline '<file_path>'
```

### 4. Keyword Context Search (`.docx`, `.xlsx`, `.pdf`) — *Fact Verification*
Search for target terms across all paragraphs, sheets, or pages with immediate `[Prev]`, `[MATCH]`, `[Next]` line contexts and page tracking:
```powershell
python "C:\Users\Reaticle\.gemini\config\skills\office-parser\scripts\office_parser.py" search '<file_path>' '<keyword>'
```

### 5. Specific Sheet Extraction (`.xlsx` only)
Read a specific sheet by name or 1-based index with optional row range:
```powershell
python "C:\Users\Reaticle\.gemini\config\skills\office-parser\scripts\office_parser.py" sheet '<file_path>' <sheet_name_or_index> [start:end]
```

### 6. Full Text Extraction (`.docx` & `.pdf`)
Extract full text (use cautiously on large files):
```powershell
python "C:\Users\Reaticle\.gemini\config\skills\office-parser\scripts\office_parser.py" full '<file_path>'
```

---

## Token Optimization & Workflow Guidelines

### For `/collector` (Rapid Context & Requirement Gathering)
1. **Always run `preview` first**: Grasp document scope, total pages, and section outlines. Never dump entire 50+ page PDFs into prompt context.
2. **Inspect Page Health**: If `preview` detects 100% scanned image pages (`[ALARM: ... OCR required]`), halt vector extraction immediately and inform the user.

### For `/verifier` (Targeted Fact Checking & Boundary Auditing)
1. **Use `search` for targeted discovery**: Locate the exact page numbers containing policy clauses, performance indicators, or numbers.
2. **Use `page` for targeted slice extraction**: Extract only the specific pages (e.g. `page 21:22`) to cross-reference claims and provide strict evidence citations without loading unrelated chapters.

### PowerShell Path Escaping
> [!IMPORTANT]
> Always enclose file paths in single quotes `'...'` in PowerShell on Windows to avoid issues with spaces, brackets, or Chinese quotation marks (`“` and `”`).
