<!-- config/plugins/frontend-design/skills/svg-designer/references/gotchas.md -->
# SVG Designer Gotchas & Troubleshooting

本文档汇编 SVG 矢量排版、字体字阶控制及几何计算中的高频陷阱、边界限制与反模式。模型在设计、生成或排查 SVG 架构图时必须对照检查。

---

## Common Errors

### 1. Font Scaled Down Below 12px to Prevent Overflow

**Cause:** 当文本长度超出预设卡片宽度时，模型触发“空间代偿本能”，通过将 `font-size` 缩小至 `8px~10px` 来避免文字溢出卡片边界，造成图表在大屏或印刷时可读性完全坍塌。

**Solution:** 坚决捍卫 $12\text{px}$ 物理底线。通过文本精炼、`<tspan>` 折行以及容器矩形外延来解决空间容纳问题。

```xml
<!-- ❌ BAD — 缩减字号代偿容器宽度不足 -->
<rect x="20" y="20" width="160" height="40" rx="4" fill="#1e293b" />
<text x="30" y="44" font-size="9" fill="#94a3b8">
  分布式海量物联网设备接入与协议解包引擎
</text>

<!-- ✅ GOOD — 保持 12px 保底，拆分 tspan 并外扩容器高度 -->
<rect x="20" y="20" width="160" height="64" rx="4" fill="#1e293b" />
<text x="30" y="42" font-size="12" fill="#94a3b8">
  <tspan x="30">分布式海量物联网设备</tspan>
  <tspan x="30" dy="1.35em">接入与协议解包引擎</tspan>
</text>
```

---

### 2. Multi-line `<tspan>` Missing `x` Attribute

**Cause:** 在使用 `<tspan>` 实现多行文本时，省略了后续行的 `x` 属性。在 SVG 渲染规范中，省略 `x` 的 `<tspan>` 会紧接着前一个字符的横向终止点排版，导致第二行文字直接飘到右侧空白区域或与其他元素重叠。

**Solution:** 每一个新行 `<tspan>` 必须显式声明与第一行一致的绝对 `x` 坐标（保持左对齐或指定对齐基线）。

```xml
<!-- ❌ BAD — 第二行缺失 x 属性，横向跑偏 -->
<text x="40" y="50" font-size="14" fill="#ffffff">
  <tspan>第一行核心业务流程</tspan>
  <tspan dy="1.4em">第二行配套数据落盘</tspan>
</text>

<!-- ✅ GOOD — 每行均显式指定 x="40" 维持对齐锚点 -->
<text x="40" y="50" font-size="14" fill="#ffffff">
  <tspan x="40">第一行核心业务流程</tspan>
  <tspan x="40" dy="1.4em">第二行配套数据落盘</tspan>
</text>
```

---

### 3. Hardcoded Pixel `dy` Instead of Relative Unit (`em`)

**Cause:** 在 `<tspan>` 中使用固定的像素行高（例如 `dy="18px"` 或 `dy="18"`）。当后续调整 `font-size`（如从 12px 升级到 16px）时，固定像素行距会导致文字行与行之间发生严重重叠碰撞或过宽断裂。

**Solution:** 行距增量统一使用相对字阶单位 `dy="1.35em"`（正文）或 `dy="1.25em"`（大标题），实现行距与字号的自动几何联动。

```xml
<!-- ❌ BAD — 硬编码固定像素数值，字号放大后将重叠 -->
<text x="30" y="60" font-size="16" fill="#f8fafc">
  <tspan x="30">云原生可观测性底座</tspan>
  <tspan x="30" dy="14">多租户指标采集流水线</tspan>
</text>

<!-- ✅ GOOD — 使用相对单位 1.35em 自适应联动 -->
<text x="30" y="60" font-size="16" fill="#f8fafc">
  <tspan x="30">云原生可观测性底座</tspan>
  <tspan x="30" dy="1.35em">多租户指标采集流水线</tspan>
</text>
```

---

### 4. Container Box Geometry Not Cascaded on Multi-line Wrapping

**Cause:** 文本成功通过 `<tspan>` 换行，但包围盒容器（`<rect>`）的高度依然保持单行文本时的固定高度，导致第二行、第三行文本从容器底部穿透刺出，覆盖下游图元。

**Solution:** 文本每增加一行，容器高度必须严格执行几何递增：$H \leftarrow H + \Delta H$，同时该容器后续的图元纵向位移 $Y$ 也必须顺延平移。

```xml
<!-- ❌ BAD — 换行为 3 行后文本超出容器底部 -->
<rect x="50" y="50" width="200" height="50" fill="#1e293b" />
<text x="65" y="75" font-size="12" fill="#cbd5e1">
  <tspan x="65">平台级微服务分布式追踪</tspan>
  <tspan x="65" dy="1.35em">支持全链路拓扑探针注入</tspan>
  <tspan x="65" dy="1.35em">实时异常定位与告警联动</tspan>
</text>

<!-- ✅ GOOD — 容器高度外扩至 86px，内边距均匀平衡 -->
<rect x="50" y="50" width="200" height="86" fill="#1e293b" />
<text x="65" y="75" font-size="12" fill="#cbd5e1">
  <tspan x="65">平台级微服务分布式追踪</tspan>
  <tspan x="65" dy="1.35em">支持全链路拓扑探针注入</tspan>
  <tspan x="65" dy="1.35em">实时异常定位与告警联动</tspan>
</text>
```

---

### 5. Canvas Truncation Due to Fixed `viewBox` Height

**Cause:** 子卡片由于折行和内容扩充导致最下方元素坐标下移（如达到 $Y=840$），但顶层 `<svg>` 的 `viewBox` 仍停留在初始的 `"0 0 1200 800"`，导致图形底端被硬性截断。

**Solution:** 画布高度必须具备级联感知能力，设置为包含全部图元在内的外包围盒加上安全下边距：$H_{\text{canvas}} \ge \max(Y_i + H_i) + \text{Padding}_{\text{bottom}}$。

```xml
<!-- ❌ BAD — viewBox 仅 800 高，底部元素 (Y=820, H=60) 无法显示 -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800" width="100%" height="100%">
  <!-- ... 中间内容 ... -->
  <rect x="100" y="820" width="1000" height="60" fill="#334155" />
</svg>

<!-- ✅ GOOD — 同步扩展 viewBox 高度至 920，完整保留边距 -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 920" width="100%" height="100%">
  <!-- ... 中间内容 ... -->
  <rect x="100" y="820" width="1000" height="60" fill="#334155" />
</svg>
```

---

### 6. Inherited `<g font-size="...">` Leakage / Inline Style Escaping

**Cause:** 父分组 `<g>` 声明了 `font-size="10"`，或者文字节点带有 `style="font-size: 10px"`，导致正则扫描直接漏判，但在浏览器实际渲染时字体变小破坏可读性。

**Solution:** 依赖 XML DOM 继承计算树进行全量属性解析，根除继承样式中的小字号污染。

```xml
<!-- ❌ BAD — 隐式继承父组的小字号 -->
<g id="metrics-group" font-size="10" fill="#64748b">
  <text x="100" y="200">吞吐量指标监控</text>
</g>

<!-- ✅ GOOD — 根除小字号声明，显式设为 12px 或继承标准基线 -->
<g id="metrics-group" font-size="12" fill="#64748b">
  <text x="100" y="200">吞吐量指标监控</text>
</g>
```

---

### 7. Reviewer In-Place Coordinate Drift Remediation

**Cause:** `/reviewer` 发现某处文字溢出或字号偏小，直接在审查修复日志中强行修改文本字号与 `x`, `y` 坐标。由于文本尺寸发生质变，单点修复造成整体几何拓扑全面漂移和对齐崩溃。

**Solution:** 坚决执行 Reviewer 契约——判定为 `L2 几何拓扑缺陷`，签发 `FAIL` 阻断单并打回生成器，由生成器重新求解几何。

---


---

### 8. Western Font Precedence Triggering CJK Fallback to SimSun in Typst / resvg (西文字体置前导致 Typst 异常回退为宋体)

**Cause:** 在 SVG 中声明复合字体栈时，直接照搬 Web 惯用的 `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', sans-serif`。在 Typst / resvg 渲染引擎下，引擎找不到 Apple 字体后立即命中 `Segoe UI` 并将其选定为主字体。但 `Segoe UI` 是纯西文字体、不包含中文字形，引擎只能将中文字符回退至系统底层的宋体（SimSun），导致数字/西文为无衬线、中文突变为宋体，严重割裂。

**Solution:** 严格执行**方案B（中文字体前置锁定）**，将兼具完整中西文字形的系统无衬线字体（思源黑体、微软雅黑）放在第一顺位，严禁西文字体排在中文字体之前：

```xml
<!-- ❌ BAD — 纯西文字体 Segoe UI 排在前列，触发 Typst 中文宋体回退 -->
<text font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', sans-serif">
  数智路桥维护管养平台
</text>

<!-- ✅ GOOD — 方案B：思源黑体与微软雅黑前置锁定，中西文无缝现代呈现 -->
<text font-family="Noto Sans SC, Microsoft YaHei, PingFang SC, sans-serif">
  数智路桥维护管养平台
</text>
```

## Limits

| Limit (约束项) | Hard Limit (硬性阈值) | Recommended Value (推荐基准) | Notes |
| :--- | :--- | :--- | :--- |
| **常规文本最小字号** | $\ge 12\text{px}$ | $14\text{px}$ (标准正文) | 低于 12px 无法通过 DOM 质检门禁 |
| **特殊豁免微小字号** | $\ge 10\text{px}$ | $10\text{px}$ | 必须声明 `data-allow-micro-font="true"`，仅限 Sparkline 刻度 |
| **多行折行行距** | `1.2em ~ 1.5em` | `1.35em` | 必须使用相对单位 `em`，严禁纯像素数字 |
| **CJK / 全角字宽估算系数** | $1.0 \times \text{FontSize}$ | $1.0 \times \text{FontSize}$ | 中文字符、全角标点 |
| **ASCII / 半角字宽估算系数** | $0.5 \sim 0.6 \times \text{FontSize}$ | $0.55 \times \text{FontSize}$ | 英文大小写、数字及半角符号 |
| **容器水平最小内边距** | $\ge 8\text{px}$ | $12\text{px} \sim 16\text{px}$ | 防止文字贴紧外边框 |
| **顶层 viewBox 纵横比** | — | `16:9` (大屏/PPT) 或 `4:3` | 优先保证通用屏幕完整展现 |

---

## Anti-Patterns

### Anti-Pattern 1: Downscaling Font Size to Fit Box

```xml
<!-- ❌ BAD — 削足适履：为了塞进小卡片，将字号缩至 9px -->
<rect width="120" height="30" fill="#1e293b" />
<text x="10" y="20" font-size="9" fill="#94a3b8">高可用负载均衡节点</text>

<!-- ✅ GOOD — 空间代偿：保持 12px，调整卡片尺寸或精炼文案 -->
<rect width="140" height="36" fill="#1e293b" />
<text x="12" y="23" font-size="12" fill="#94a3b8">负载均衡节点</text>
```

### Anti-Pattern 2: Single-Line Regex for SVG Font Validation

```python
# ❌ BAD — 极其粗糙的正则匹配，极易被内联 style、注释、继承漏判
re.findall(r'font-size="(\d+)px"', svg_content)

# ✅ GOOD — 使用 ElementTree 进行 DOM 树递归与计算样式求值
# 见 scripts/validate_svg.py
```

### Anti-Pattern 3: Floating Point Coordinate Jitter

在手动计算或拼接路径时产生过多无意义的高精度浮点数（如 `x="34.1983748293"`），不仅急剧膨胀文件体积，还容易在渲染引擎上产生半像素锯齿模糊。坐标与尺寸统一四舍五入保留到整数或最多 1 位小数。

---

## Cascading & Propagation Behavior

SVG 矢量排版的几何变动具有强烈的**向上传播（Upward Propagation）**与**向下级联（Downward Cascading）**特征：

```
[文本内容增加 / 折行]
   │
   ▼
1. 字符宽度累加超过容器可用宽 -> 触发显式 <tspan> 折行
   │
   ▼
2. 文本总高增加 (ΔH) -> 容器 <rect> 高度同步扩大 (H += ΔH)
   │
   ▼
3. 下游兄弟图元纵向位移 -> Sibling Nodes Y 坐标平移 (Y += ΔH)
   │
   ▼
4. 画布整体边界溢出 -> 顶层 <svg viewBox> 级联扩增
```

**核心法则**：严禁局部孤立修改单个文本，任何尺寸变动必须引发包围盒的系统性重求解。
