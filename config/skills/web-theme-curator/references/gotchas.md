<!-- config/skills/web-theme-curator/references/gotchas.md -->
# Web Theme & Typography Gotchas & Anti-Patterns

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
