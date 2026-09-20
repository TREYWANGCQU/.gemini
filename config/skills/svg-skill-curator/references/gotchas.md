<!-- config/skills/svg-skill-curator/references/gotchas.md -->
# SVG Skill Curator Gotchas & Troubleshooting

本文档汇编使用 `svg-skill-curator` 进行局部矢量技能脚手架构建、跨项目模板治理及版本同步时的高频踩坑案例、硬性限制与反模式。

---

## Common Errors

### 1. Accidental Overwrite of Customized `design-tokens.yaml`

**Cause:** 在对已有项目重复执行脚手架（Scaffold）或版本同步（Sync）时，未检测本地是否已有业务配置文件，直接使用脚手架默认模板强制覆盖，导致用户辛辛苦苦调优的品牌配色、边距与豁免白名单全部丢失。

**Solution:** 脚手架在写入 `design-tokens.yaml` 前必须进行存在性检测；若文件已存在，默认只升级 `scripts/validate.py` 与通用 Schema，保留原有的 `design-tokens.yaml`，或生成 `.new` 临时文件以供比对。

```python
# ❌ BAD — 盲目覆盖用户现有设计变量
with open("design-tokens.yaml", "w") as f:
    f.write(default_template)

# ✅ GOOD — 检查存在性，保护用户定制资产
if os.path.exists("design-tokens.yaml"):
    print("design-tokens.yaml already exists; skipping overwrite to preserve custom tokens.")
else:
    with open("design-tokens.yaml", "w") as f:
        f.write(default_template)
```

---

### 2. Scaffold Template Hardcoding Sub-12px Defaults

**Cause:** 脚手架模板作者在编写 `templates/arch-card.svg` 或 `design-tokens.yaml` 时，误将辅助字阶默认值写成 `10px` 或 `9px`，导致所有基于该脚手架新建的项目从一开始就植入了违规小字号，通不过全局 DOM 质检。

**Solution:** 脚手架模板库必须严格自举审查，所有预置的卡片模板、变量默认值均必须遵守 $\text{font-size} \ge 12\text{px}$ 的生理底线。

```yaml
# ❌ BAD — 预置违规小字阶
scale:
  caption: 10px
  body: 12px

# ✅ GOOD — 严格保底
scale:
  floor: 12px
  sm: 14px
  base: 16px
  lg: 18px
```

---

### 3. Hardcoding Absolute Developer Machine Paths in Local Scripts

**Cause:** 脚手架在生成 `.agents/skills/<project>-svg-generator/scripts/validate.py` 时，将当前开发者的绝对物理路径（例如 `C:\Users\Reaticle\.gemini\...`）硬编码写入脚本内部作为全局验证器的软链或查找路径。当工程推送到团队仓库或在 CI 环境（如 Ubuntu 容器）执行时，脚本因绝对路径不存在直接崩溃报错。

**Solution:** 本地装配自包含的静态质检脚本，或者通过相对路径与环境变量动态解析基准路径，杜绝任何硬编码的机器物理路径。

```python
# ❌ BAD — 硬编码特定开发者的机器绝对路径
GLOBAL_VALIDATOR = r"C:\Users\Reaticle\.gemini\config\skills\svg-designer\scripts\validate_svg.py"

# ✅ GOOD — 自包含独立验证引擎，或基于工作区根目录相对寻找
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 自包含执行或基于相对层级调用
```

---

### 4. Generating Project Skill in Global Root Instead of Workspace Root

**Cause:** 误将针对某客户/某具体项目的特化技能（如 `soe-ppt-svg-generator`）直接脚手架生成在全局目录 `C:\Users\Reaticle\.gemini\config\skills\` 中，造成全局技能列表急速膨胀，污染其他完全无关的项目上下文。

**Solution:** 牢记边界契约矩阵：全局技能（Tier 1）仅限 `svg-designer` 与 `svg-skill-curator`；所有具体的业务项目特化技能（Tier 2）必须生成在项目工作区根目录的 `.agents/skills/<project>-svg-generator/` 下。

---

### 5. Mixing Dynamic Logic / Shell Code in `design-tokens.yaml`

**Cause:** 试图在声明式的 `design-tokens.yaml` 中编写条件判断、动态函数或可执行代码，破坏了“纯数据配置”的 Tier 3 契约。

**Solution:** `design-tokens.yaml` 必须保持为纯静态的 YAML/JSON 数据结构，仅表达色值、尺寸、字阶与豁免规则，由静态引擎进行读取和派生。

---

### 6. Drifted Local Validator Allowing Sub-12px in Production

**Cause:** 项目本地早期初始化的 `scripts/validate.py` 存在老旧漏洞（例如当时只检查了属性没检查内联 style），随着全局 `svg-designer` 升级后，该项目长期未执行 `sync`，导致违规小字号在项目内部被漏放并合并进主干。

**Solution:** 定期调用 `/svg-skill-curator audit`，扫描当前工作区所有局部技能的健康度与引擎版本；发现版本漂移后一键执行 `sync` 平滑拉齐。

---

## Limits

| Limit (约束项) | Hard Limit (硬性阈值) | Standard Pattern (标准规范) | Notes |
| :--- | :--- | :--- | :--- |
| **局部技能命名模式** | `^[a-z0-9-]+-svg-generator$` | `<project>-svg-generator` | 必须具备明确的业务域前缀与后缀标识 |
| **局部技能安装路径** | `.agents/skills/<name>/` | 基于项目根目录相对路径 | 纳入项目 Git 版本控制 |
| **设计变量物理格式** | 纯静态 YAML / JSON | `design-tokens.yaml` | 严禁包含内嵌脚本或执行代码 |
| **默认最小字阶常量** | $\ge 12\text{px}$ | `floor: "12px"` | 模板中严禁提供 `< 12px` 的默认参数 |
| **支持画布比例预设** | `16:9`, `4:3`, `1:1`, `21:9` | 默认推荐 `16:9` (1200x675 或 1920x1080) | 满足大屏与汇报投影标准 |

---

## Anti-Patterns

### Anti-Pattern 1: Blind Scaffold Overwrite

```bash
# ❌ BAD — 重新生成脚手架时强行 rm -rf 原有目录，抹杀业务配置
rm -rf .agents/skills/my-svg-generator/ && scaffold ...

# ✅ GOOD — 增量探测，已有 tokens 则仅提示并备份
scaffold --name my-svg-generator --preserve-tokens
```

### Anti-Pattern 2: Monolithic Global SVG Skill Bloating

```text
❌ BAD: 在全局 config/skills/ 目录下堆叠几十个项目专属技能
C:\Users\Reaticle\.gemini\config\skills\
  ├── project-a-svg-generator\
  ├── project-b-svg-generator\
  ├── project-c-svg-generator\
  └── ... (全局上下文被严重污染)

✅ GOOD: 双全局架构，项目私有归位到本地工作区
全局 (config/skills/):
  ├── svg-designer
  └── svg-skill-curator
本地工作区 (.agents/skills/):
  └── project-a-svg-generator
```

### Anti-Pattern 3: Skipping Quality Gate in Local Workflows

在生成的局部技能 `SKILL.md` 中省略“运行验证脚本”步骤，导致开发者或 LLM 在画完图后直接宣称完成，绕过确定性质检门禁。每个局部技能必须将 `validate.py` 设为不可逾越的交付前置条件。

---

## Synchronization & Drift Behavior

当全局规则与本地技能发生演进时，遵循如下三方同步机制：

```
[全局 svg-designer 升级]
   │
   ├─ 更新 scripts/validate_svg.py 核心算法
   └─ 优化空间代偿几何模型
   │
   ▼
[运行 /svg-skill-curator audit]
   │
   ├─ 探测到本地 .agents/skills/*/scripts/validate.py 存在哈希差异
   └─ 标记为 DRIFT_DETECTED (建议同步)
   │
   ▼
[执行 /svg-skill-curator sync]
   │
   ├─ 【更新】覆盖本地 scripts/validate.py
   ├─ 【更新】向 SKILL.md 注入最新的边界提示词
   └─ 【锁定】完整保留项目私有 design-tokens.yaml (业务参数完全隔离)
```
