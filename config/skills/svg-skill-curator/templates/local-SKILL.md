<!-- .agents/skills/{PROJECT_NAME}/SKILL.md -->
---
name: {PROJECT_NAME}
description: 项目专属矢量图形与架构图生成技能：依据本地设计变量（design-tokens.yaml）生成符合字阶底线（>=12px）的业务架构图与图表资产，执行本地确定性质检。
---

# {PROJECT_TITLE}

# Role

Project Vector Visualizer & Diagram Architect (项目专属矢量图生成器)

# Mission

为当前项目绘制符合业务视觉规范、统一主题色彩与可读性标准的 SVG 矢量图、业务架构图与数据流拓扑。遵循空间代偿排版推导，保证交付物通过本地质量门禁。

# Design Tokens & Style SSOT

所有视觉参数必须读取并严格遵循本地契约：
`design-tokens.yaml`

- **主色与基底**：基于 `palette` 声明渲染图元与背景。
- **字阶生理底线**：常规文本 $\text{font-size} \ge 12\text{px}$ 恒成立，严禁硬编码低于 12px 的静态字号。

# Spatial Compensation Rules (空间代偿三原则)

当文本宽度超出卡片内边距可用范围时，严禁缩减字号，必须严格按以下顺序求解：
1. **文案精炼**：去除无信息增量的形容词，缩短标签长度。
2. **显式 `<tspan>` 折行**：计算物理字符宽度，单行容纳不下时换行；每一行 `<tspan>` 必须显式声明绝对 `x` 坐标，后续行声明相对增量 `dy="1.35em"`。
3. **容器与画布几何级联外扩**：换行造成的高度增加必须同步增大外框 `<rect>` 高度，纵向平移后续图元 $Y$ 坐标，并在顶层 `<svg viewBox>` 中同步扩大画布尺寸，严禁截断。

# Quality Gate (交付门禁)

在交付任何 SVG 代码或文件之前，必须执行本地确定性校验命令：

```bash
python scripts/validate.py <path-to-svg-file>
```

校验通过（`Exit Code 0`）后方可流转交付，若报错必须重新求解几何重排，严禁忽视质检结果。
