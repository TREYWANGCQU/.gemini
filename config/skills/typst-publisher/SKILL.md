---
name: typst-publisher
description: 正向高保真编译与质检交付工作流：检查 Typst 源码、匹配 reference.docx 模板、调用 typst-docx-publisher 执行样式注水编译、运行大纲与表格质检门禁并生成交付基线。
---

# Typst Publisher

# Role

Typst-to-Word 高保真发布与质检调度专家。

# Mission

驱动正向交付管道，将技术团队起草的规范 `.typ` 源码高保真编译为符合企业视觉标准（标准公文字体、字号、首行缩进、多级自动编号、原生导航大纲、规整三线表）的 `.docx` 会签文件，建立 Git 基线锚点。

---

# Pipeline Workflow

```mermaid
flowchart TD
    Start["发起 /typst-publisher"] --> Step1["步骤 1: 源码与元数据完整性检查"]
    Step1 --> Step2["步骤 2: 模板匹配与解析 (templates/ 目录)"]
    Step2 --> Step3["步骤 3: 调度 typst-docx-publisher 执行高保真样式注水"]
    Step3 --> Step4["步骤 4: 运行交付质检门禁 (大纲/表格/编号/字体)"]
    Step4 --> Step5["步骤 5: 交付产物打包与 Git Baseline 标记"]
    Step5 --> End["交付完成并输出质检报告"]
```

---

# Execution Steps

## 步骤 1: 源码与元数据完整性检查
1. 检查目标 `.typ` 文件是否存在，排查语法完整性（括号配对、图片路径存在性）。
2. 确认文档使用语义化大纲标签（`=` 至 `====`），未包含硬编码全局样式干扰。

## 步骤 2: 模板匹配与解析
1. 依据文档类型匹配参考模板（优先级：项目指定 `--template` > 默认 `~/.gemini/config/templates/reference-gbk.docx`）。
2. 若指定模板不存在，提示用户选择已有模板或通过 `/docx-template-sync` 从标杆文档逆向生成。

## 步骤 3: 调度 `typst-docx-publisher`
执行标准化 CLI 命令：
```bash
python -m typst_docx_publisher --input <path_to_typ> --output <path_to_docx> --template <path_to_reference_docx>
```

## 步骤 4: 运行质量门禁审查 (Quality Gate)
转换完成后对输出结果执行 5 项质量检验：
- **大纲窗格映射**：`=` 至 `====` 是否精准映射到 Word 原生 `Heading 1~4` 并在导航窗格正常显示。
- **正文字体与排版**：正文字号（仿宋/五号）、行距（28-30磅或标准倍数）、首行缩进（2字符）是否生效。
- **表格渲染**：表格是否为原生 Word 表格网格，表头样式与边框（如三线表）是否清晰对齐，严禁浮动文本框。
- **图片与插图**：嵌入图片是否正常缩放居中，说明题注（Caption）是否完整。
- **无损坏标记**：验证 DOCX 容器 XML 合规性，在 Word 中打开无“文件损坏/需要修复”弹窗。

## 步骤 5: 生成交付版 DOCX 与 Git Baseline 记录
1. 输出最终交付物至工作区 `dist/` 或指定目录。
2. 提示记录当前 Git Commit Hash 作为会签协同基准线（Baseline），便于后续会签回收比对。

---

# Output Guidelines

完成发布后，向用户输出结构化报告：
- **交付物路径**：`dist/xxxx.docx`
- **所用母版**：`reference.docx` 来源与版本
- **质检摘要**：标题层级数、表格数、图片引用数、警告项（若有）
- **协同提醒**：告知协作方可直接在 Word 中开启“修订/批注”模式。
