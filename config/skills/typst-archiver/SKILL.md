---
name: typst-archiver
description: 逆向两阶段清洗与差异合流归档工作流：接收会签修改或历史 Word 文档、Stage 1 独立逆向净化、Stage 2 差异比对安全合流至 main.typ 或独立归档。
---

# Typst Archiver

# Role

Word-to-Typst 逆向归档与会签合流专家。

# Mission

驱动两阶段逆向归档管道，将协作方返回的可能已被破坏结构（无样式、硬编码序号、全角空格、表格断裂）的 Dirty Word 文档安全逆向为结构纯净的 Typst，并精准合流至主工程或独立数字化归档。

---

# Pipeline Workflow

```mermaid
flowchart TD
    Start["收到会签/历史 DOCX"] --> Stage1["Stage 1: 独立逆向净化 (Staging Ingestion)"]
    Stage1 --> S1_1["OpenXML 解包与多媒体抽取 -> .staging/assets/"]
    Stage1 --> S1_2["启发式语义大纲恢复 (= 至 ====)"]
    Stage1 --> S1_3["表格网格与跨行跨列 colspan/rowspan 规范化"]
    Stage1 --> S1_4["产出独立中间态 staging.typ"]
    Stage1 --> Decision{"归档模式判定"}
    
    Decision -->|"单向全新归档 (Archive)"| S2_Archive["封装为独立 Typst 项目并注入 @local 模板"]
    Decision -->|"双向会签合流 (Reconcile)"| Stage2["Stage 2: 差异对齐与合流 (Reconciliation)"]
    
    Stage2 --> S2_1["AST 差异对比: 定位变更章节 (Diff Engine)"]
    Stage2 --> S2_2["安全注入: 保护 main.typ 头部模板/自定义宏，仅更新正文"]
    Stage2 --> S2_3["资产移动: .staging/assets/ -> 项目 assets/"]
    Stage2 --> S2_4["Git 提交记录更新"]
    
    S2_Archive --> End["归档完成"]
    Stage2 --> End
```

---

# Execution Steps

## 步骤 1: 触发 Stage 1 独立逆向净化
调用 `word-to-typst-archiver` 执行四层清洗：
```bash
python -m word_to_typst_archiver --input <modified_docx> --output-dir .staging --mode stage1
```

## 步骤 2: 模式判定与 Stage 2 执行
- **情况 A：全新文档归档（Archive-Only）**
  直接将 staging 产物组装为独立工程，导入企业级模板，输出至 `docs/archive/`。
- **情况 B：双向会签回收（Reconcile）**
  指定目标主文档执行合流：
  ```bash
  python -m word_to_typst_archiver --input <modified_docx> --target-main <path_to_main_typ> --mode reconcile
  ```

## 步骤 3: 差异审查与安全校验
1. 检查生成的 Diff 摘要，核实新增/删除段落与表格变更。
2. 验证目标 `main.typ` 的头部 `#import`、`#show` 规则与自定义函数未被篡改。
3. 验证抽取图片已合流至 `assets/` 且无断链。

---

# Output Guidelines

完成归档或合流后，向用户汇报：
- **模式**：Reconcile（合流）或 Archive（独立归档）
- **变更摘要**：修改章节列表、新增图表统计
- **文件状态**：更新后的 `main.typ` 路径及生成的备份文件路径。
