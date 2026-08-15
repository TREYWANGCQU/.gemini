---
name: Typst Writer
description: Generate clean Typst markup content without inline styles or format definitions, referencing locally-defined templates from the @local namespace, with explicit lifecycle exit decisions.
---

# Typst Writer Guideline

When writing, editing, or generating Typst documents:

## 1. No Style/Layout Definitions
Do NOT generate any global or inline styling commands unless specifically requested. This includes (but is not limited to):
- `#set page(...)`
- `#set text(...)`
- `#set par(...)`
- `#set heading(...)`

All layout, font sizes, margins, headers, and footers must be handled by the imported template.

## 2. Reference Local Templates (`@local`)
The user's local Typst packages/templates are located under `$env:APPDATA\typst\packages\local\`. Always import the required package from the `@local/` namespace at the beginning of the file.

### Example Syntax:
```typst
#import "@local/GBK-writing:0.1.0": conf, no-indent, 字体, 字号

#show: doc => conf(
  doc: doc,
)
```

*Note: Choose or ask the user which template to use from their context (e.g., `@local/GBK-writing:0.1.0`). If unspecified, use a standard template reference or placeholder comment like `#import "@local/<template-name>:<version>": *`.*

## 3. Focus on Semantic Content
Ensure the Typst output consists strictly of semantic markup:
- Headings: `= Heading 1`, `== Heading 2`, `=== Heading 3`, `==== Heading 4`
- Lists: `- Item`, `+ Numbered Item`
- Formatting: `*bold*`, `_italic_`
- Tables: `#table(...)` or `#figure(table(...), caption: [...])`
- Figures: `#figure(image("assets/..."), caption: [...])`
- Math equations: `$ ... $`

## 4. Delivery Boundary & Explicit Exit Decision
> [!IMPORTANT]
> **No Silent Auto-Compilation**: Typst Writer strictly outputs `.typ` source files and related asset folders (`assets/`). The agent MUST NOT automatically or implicitly trigger `typst compile` or document conversion tools without user instruction.

At the conclusion of drafting/editing, clearly present the **Delivery Exit Matrix** to the user for human decision:
1. **Option 1: Native High-Fidelity PDF** (For internal reporting / final visual delivery)
   - Command: `typst compile <file>.typ <file>.pdf`
2. **Option 2: Cross-Department Word Collaboration** (For co-signing / review in Word format)
   - Workflow: Run `/typst-publisher` or execute `typst-docx-publisher`
3. **Option 3: Source Retention & Library Asset** (Continue iterative editing or save as shared library component)
