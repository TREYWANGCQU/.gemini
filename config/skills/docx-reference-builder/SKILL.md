---
name: docx-reference-builder
description: 标杆 Word 逆向提取与虚拟样式合成引擎：从纯视觉无大纲样式的标杆 DOCX 中提取视觉指纹并合成标准 Heading 1~4 样式，生成合规 reference.docx。
---

# DOCX Reference Builder Skill

## 1. 概述与核心能力
解决协作方标杆文档“全靠手工选中文本调字号加粗、样式底层全是 Normal、无大纲结构”的提取痛点。
通过扫描 `document.xml` 视觉指纹并聚类推导，合成标准 `Heading 1~4` 节点注入 `styles.xml`，并清空正文打包生成高保真 `reference.docx`。

## 2. CLI 使用规范

```bash
python "C:\Users\Reaticle\.gemini\config\skills\docx-reference-builder\scripts\extract_reference_template.py" --input <benchmark.docx> --output <reference.docx>
```

## 3. 参数与工作模式
- `--input`: 标杆 Word 文档路径（必填）。
- `--output`: 生成的参考模板输出路径（必填，可输出至 `~/.gemini/config/templates/reference-gbk.docx`）。

## 4. 输出契约
标准 JSON 诊断信息，包含推导出的层级样式映射表：
```json
{
  "status": "SUCCESS",
  "diagnostics": [
    "Analyzed 120 paragraphs",
    "Synthesized Heading 1: 方正小标宋简体 44 (22pt)",
    "Synthesized Heading 2: 黑体 32 (16pt, Bold)"
  ],
  "output_files": ["C:/.../reference-gbk.docx"]
}
```
