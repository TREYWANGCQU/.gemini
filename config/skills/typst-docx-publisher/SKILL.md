---
name: typst-docx-publisher
description: 正向高保真 Word 导出与样式注水引擎：利用 Pandoc 与 AST 预处理，将纯语义 Typst 文档高保真渲染为符合企业标准样式表的 DOCX 文档。
---

# Typst DOCX Publisher Skill

## 1. 概述与核心能力
本 Skill 负责将规范的纯语义 Typst 源码（`=`/`==`/`#table`）高保真编译为带有企业级视觉样式表（多级列表编号、大纲窗格导航、公文字体与三线表）的 Word (`.docx`) 文档。

## 2. CLI 使用规范

```bash
python -m typst_docx_publisher --input <path_to_typ> --output <path_to_docx> [--template <path_to_reference_docx>]
```

或直接执行脚本：
```bash
python "C:\Users\Reaticle\.gemini\config\skills\typst-docx-publisher\scripts\publisher.py" --input <path_to_typ> --output <path_to_docx> [--template <path_to_reference_docx>]
```

## 3. 参数契约与模板回退
- `--input`: 输入 `.typ` 源码文件路径（必填）。
- `--output`: 输出 `.docx` 目标文件路径（必填）。
- `--template`: 样式参考母版（选填）。若未提供，优先寻找 `~/.gemini/config/templates/reference-gbk.docx`，若不存在则回退至工作区 `reference.docx` 或 Pandoc 默认样式。

## 4. 输出契约
脚本执行后向 stdout 输出标准 JSON 诊断信息：
```json
{
  "status": "SUCCESS",
  "diagnostics": ["Found 4 headings", "Mapped 2 tables"],
  "output_files": ["dist/document.docx"]
}
```
