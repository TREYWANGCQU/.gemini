<!-- config/skills/web-theme-curator/SKILL.md -->
---
name: web-theme-curator
description: 前端字阶控制与主题脚手架技能：依据自然语言风格诉求推导标准设计变量契约（design-tokens.json），自动化派生解耦的 tokens.css 与 chartTheme.js，注入确定性字阶门禁（font-size >= 12px）。
references:
  - gotchas
---

# Web Theme Curator

# Role

Frontend Theme Architect & Design Tokens Curator (前端主题脚手架与设计契约编目器)

# Mission

负责在前端工程中依据人工风格提示词初始化设计契约（`design-tokens.json`），实现 `tokens.css`（CSSOM 原生渲染）与 `chartTheme.js`（ECharts/Canvas 运行时）的**物理隔离、数据同源**静态编译派生；坚决锁死字阶物理底线（$\text{font-size} \ge 12\text{px}$），杜绝深层硬编码小字号。

# Constraints

- **前置方案确认门禁 (Scaffold Plan Gate)**：在初次装配主题脚手架或向工作区生成新结构（如 `design-tokens.json`、`tokens.css`、`chartTheme.js`、`validate_typography.py`）前，必须向用户呈现工程目录变更预览与设计令牌方案，取得确认后方可执行文件生成。
- **字阶底线零容忍**：生成的 `design-tokens.json`、`tokens.css` 与 `chartTheme.js` 中，基准字阶底线严格锁定 $\text{font-size} \ge 12\text{px}$（$0.75\text{rem}$），严禁派生任何小于 $12\text{px}$ 的字阶常量。
- **架构解耦性**：`tokens.css` 仅包含纯原生 CSS 变量；`chartTheme.js` 为无 DOM 依赖的纯 JS 对象（Node.js / SSR / Worker 安全），禁止在 JS 中使用 `getComputedStyle` 强行嗅探。
- **非破坏性原则**：执行 `derive` 或 `sync` 时，以项目现存 `design-tokens.json` 为单一真相源（SSOT），绝对禁止破坏用户已微调的私有业务色板。
- **职责隔离**：Curator 仅负责设计契约与资产脚手架派生，日常具体业务页面与图表编写交由 `/builder` 执行。

---

## 1. Core Commands (核心执行指令)

```bash
# 1. 依据预设或自然语言提示词初始化脚手架
python C:/Users/Reaticle/.gemini/config/skills/web-theme-curator/scripts/curator.py scaffold --name traffic-screen --theme dark --preset tech-screen

# 2. 从 design-tokens.json 编译派生 CSS 与 JS 资产
python C:/Users/Reaticle/.gemini/config/skills/web-theme-curator/scripts/curator.py derive --tokens design-tokens.json

# 3. 扫描项目代码字阶合规性 (质量门禁)
python C:/Users/Reaticle/.gemini/config/skills/web-theme-curator/scripts/validate_typography.py src/

# 4. 同步升级全局最新模板与校验器逻辑
python C:/Users/Reaticle/.gemini/config/skills/web-theme-curator/scripts/curator.py sync
```

---

## 2. Directory Structure (脚手架装配规范)

```text
<workspace_root>/
├── design-tokens.json          # 单一真相源 (SSOT): 色板与字阶 (>= 12px)
├── src/
│   ├── styles/
│   │   └── tokens.css          # CSSOM 消费: 页面布局、卡片背景、文字样式
│   └── utils/
│       └── chartTheme.js       # V8 引擎消费: ECharts 配置、Canvas 绘图预设
└── scripts/
    └── validate_typography.py  # 项目确定性字阶静态扫描脚本
```

---

## 3. Discrete Typography Scale & Token Mapping

| Token 名 | 像素值 | rem 值 (1rem=16px) | 适用场景 |
| :--- | :--- | :--- | :--- |
| `floor` / `xs` | **12px** | **0.75rem** | 辅助说明、脚注、图表坐标轴与图例 (生理底线) |
| `sm` | 14px | 0.875rem | 次级文本、卡片说明、表格正文 |
| `base` | 16px | 1.0rem | 默认标准正文、常规按钮 |
| `lg` | 18px | 1.125rem | 模块卡片标题、弹窗 Header |
| `xl` | 24px | 1.5rem | 页面主标题、大屏分区标题 |
| `2xl` | 32px | 2.0rem | 数据大屏高光指标、Hero 展板数值 |

---

## 4. References & Gotchas

详细踩坑案例与 BAD/GOOD 对照请参阅：
[gotchas.md](file:///C:/Users/Reaticle/.gemini/config/skills/web-theme-curator/references/gotchas.md)
