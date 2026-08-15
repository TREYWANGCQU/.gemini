---
name: Global Rule
description: Universal Rules & Engineering Guidelines
---

# Scope Preservation

- Modify only the requested scope.
- Do not rewrite unrelated logic.
- Prefer incremental changes.

# Output Completeness

- No TODO.
- No omitted logic.
- No placeholders.
- No pseudo implementation.

# Fact Separation

- Separate Fact, Judgment and Speculation.
- Unverified assumptions must be marked.

# Context Collection and Document Previews

- For initial research, code scans, or context collection, use structural previews, tables of contents, outlines, or key snippet extractions instead of copying entire raw files.
- Prefer referencing files using absolute links (e.g., `file:///...`) or relative paths over full-text copy-paste.
- Summarization and structural omission are permitted and encouraged in intermediate research notes or material collection artifacts to optimize token usage and focus.

# Document Integrity

- Generated documents must be structurally complete.
- Follow the specific style/principles of the active writing workflow if one is selected (e.g., avoiding corporate jargon in reflective writing).

# Code-Specific Rules
*(Apply the following rules only when writing, editing, or generating source code, configuration files, or scripts)*

## Architecture Preservation

- Preserve existing architecture.
- Preserve naming conventions.
- Preserve interfaces.
- Preserve control flow.

## Dependency Integrity

- Do not invent APIs.
- Do not invent imports.
- Do not invent SDK methods.
- Unknown dependencies must be explicitly marked as unverified.

## Contract Safety

- Verify exported types.
- Verify function signatures.
- Verify parameter contracts.
- Verify module boundaries.

## Delivery Integrity

- Generated code must be executable.

## File Path Rule

Every generated code block representing a file or a patch must begin with a comment indicating its relative path, using the syntax appropriate for that file format. For example:
- TypeScript/JavaScript/Java/Go: `// relative/path/file.ts`
- Python/YAML/Typst/Shell: `# relative/path/file.py`
- CSS/Less/SCSS: `/* relative/path/file.css */`
- HTML/XML: `<!-- relative/path/file.html -->`