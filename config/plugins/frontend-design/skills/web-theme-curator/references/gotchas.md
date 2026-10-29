<!-- config/plugins/frontend-design/skills/web-theme-curator/references/gotchas.md -->
# Web Theme, Typography & Palette Gotchas & Anti-Patterns

## 1. CSS font-size < 12px (The Micro-Font Antipattern)

- **BAD**:
  ```css
  .badge { font-size: 9px; }
  .footnote { font-size: 10px; }
  ```
- **WHY**: 在多数桌面显示器和标准移动设备上，低于 12px 会导致子像素栅格化模糊，视力可读性坍塌，违反 WCAG 与人机工程学基线。
- **GOOD**:
  ```css
  .badge { font-size: var(--text-xs, 0.75rem); padding: 2px 6px; }
  .footnote { font-size: var(--text-xs, 0.75rem); color: var(--color-text-secondary); }
  ```

---

## 2. CSS transform: scale() 假合规绕过

- **BAD**:
  ```css
  .tag { font-size: 12px; transform: scale(0.8); display: inline-block; }
  ```
- **WHY**: 使用 transform 缩小文字在盒模型中仍占据原始尺寸，导致边缘空白或点击热区错位，且模糊渲染问题依旧存在。
- **GOOD**:
  精简文本或重组卡片布局，保持 12px 物理字号。

---

## 3. ECharts 图表坐标轴拥挤时的错误代偿

- **BAD**:
  ```javascript
  xAxis: {
    axisLabel: { fontSize: 9 } // 试图缩小编号以塞下更多日期
  }
  ```
- **GOOD**:
  ```javascript
  xAxis: {
    axisLabel: {
      fontSize: CHART_TOKENS.fontSizeFloor, // 严格保持 12
      rotate: 30, // 旋转倾斜代偿
      interval: 'auto' // 或隔项隐藏
    }
  }
  ```

---

## 4. 强行在 JS 中通过 getComputedStyle 嗅探 CSS 变量

- **BAD**:
  ```javascript
  // chartTheme.js
  const primary = getComputedStyle(document.documentElement).getPropertyValue('--color-primary');
  ```
- **WHY**: 在 Node.js 服务端渲染（SSR）、Nuxt/Next 预渲染、Web Worker 或离线出图脚本中，不存在 DOM `window` 与 `document` 对象，会导致直接报错崩溃。
- **GOOD**:
  由 `design-tokens.json` 作为 SSOT 静态编译分别导出 `tokens.css` 和 `chartTheme.js`。

---

## 5. 屏幕色彩“圣诞树彩灯效应”（The Rainbow Dash Antipattern）

- **BAD**:
  ```json
  // design-tokens.json
  "chartPalette": ["#00f0ff", "#00e676", "#ffa726", "#ff5252", "#0084ff", "#b388ff"]
  ```
  页面同时混排青、绿、橙、红、宝蓝、电光紫等 6 种以上高饱和度有彩色，单张卡片内杂色四溅。
- **WHY**: 大屏是工业级生产监控与调度态势系统，杂色泛滥破坏庄重科技底调，分散视觉焦点，使用户无法在一秒内识别警讯紧急程度。
- **GOOD**:
  严格遵从 **“1 个主色 + $\le 3$ 个辅助色”** 契约：
  - **1 个主色 (Primary: #00f0ff)**：常态底座与全息感知，统揽全局；
  - **3 个辅助色**：`warning (#ffa726)` 预警自控、`danger (#ff5252)` 超限协同、`success (#00e676)` 达标治理；
  - **彻底清退无关色相**：图表调色板收敛至 4 色，坚决剔除紫色与多色杂蓝。

---

## 6. HTML 标签深层内联硬编码色值（The Inline Color Leak）

- **BAD**:
  ```html
  <span style="color: #00f0ff;">感知总数</span>
  <div style="background: rgba(255,167,38,0.25); border: 1px solid #ffa726;">
  ```
- **WHY**: 内联散落数十处私有 Hex/RGBA 色值导致主题不可维护，使 Design Tokens 沦为空壳，产生大面积色阶漂移。
- **GOOD**:
  全部抽取收敛至语义化 CSS 类名或原子变量：
  ```html
  <span class="text-primary">感知总数</span>
  <div class="alert-strip-warning">
  ```
