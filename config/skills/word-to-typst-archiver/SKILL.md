---
name: word-to-typst-archiver
description: Word 逆向两阶段清洗与差异合流归档引擎：包含四层清洗（解包资产、语义大纲恢复、表格网格解析、Typst序列化）与 Reconcile 安全合流能力。
---

# Word to Typst Archiver Skill

## 1. 概述与核心能力
本 Skill 负责将修改后的 Dirty Word（无原生样式、硬编码编号、全角空格缩进、表格断裂）逆向为纯净的 Typst，并通过两阶段架构安全归档或合流回主文档，绝不破坏主工程的模板引用和自定义宏。

## 2. CLI 使用规范

### 阶段 1：独立逆向净化（Stage 1）
```bash
python "C:\Users\Reaticle\.gemini\config\skills\word-to-typst-archiver\scripts\archiver.py" --input <modified.docx> --output-dir .staging --mode stage1
```

### 阶段 2：双向会签合流（Reconcile Mode）
```bash
python "C:\Users\Reaticle\.gemini\config\skills\word-to-typst-archiver\scripts\archiver.py" --input <modified.docx> --target-main <src/main.typ> --mode reconcile
```

### 单向全新归档（Archive-Only Mode）
```bash
python "C:\Users\Reaticle\.gemini\config\skills\word-to-typst-archiver\scripts\archiver.py" --input <history.docx> --output-dir <docs/archive/target_folder> --mode archive
```

## 3. 四层清洗机制
- **Layer 1: 解包与资产提取**：抽取图片至 `assets/`，维护 `rId` 映射。
- **Layer 2: 启发式语义恢复**：公文正则匹配标题层级（`=` 至 `====`），剥离行首全角空格与硬回车。
- **Layer 3: 表格规范化**：解析 `colspan`/`rowspan`，生成标准 `#table(...)`。
- **Layer 4: Typst 序列化**：输出干净语法，保护头部宏包依赖。

## 4. 输出契约
```json
{
  "status": "SUCCESS",
  "diagnostics": [
    "Extracted 3 images to assets/",
    "Recovered 8 headings (1x H1, 3x H2, 4x H3)",
    "Normalized 2 tables",
    "Safely reconciled main.typ without altering template headers"
  ],
  "output_files": ["src/main.typ"]
}
```
