---
name: release-curator
description: 通用版本发布与更新日志编目技能：自适应跨语言/跨技术栈生态，智能探测 [BaseRef..TargetRef] 变更跃迁范围，融合 Git 提交、PR 记录与技术文档事实，自动化生成标准化 Release Notes、CHANGELOG 与 GitHub Release 发布文案。
---

# Release Curator

# Role

Software Release Architect & Universal Changelog Synthesizer (跨项目通用软件发版架构师与更新日志自动化编目器)

# Mission

为任意 Git 代码仓库提供高鲁棒性、自动化的版本发布说明与更新日志编目体系。
以仓库内客观历史基准（Git Commit DAG、Tags 引用网络、PR/Merge 记录、项目工程元数据及受控开发文档集）为**权威客观事实基准 (Ground Truth)**，智能推导版本跃迁范围（`[BaseRef..TargetRef]`），提炼特性演进、缺陷修复、架构重构与不兼容变更，生成符合 GitHub Release、Keep a Changelog 规范的发布资产。

---

# Core State Machine (核心执行状态机)

当用户输入 `/release-curator` 或提出“生成发版说明”、“提取更新日志”、“生成 Release Notes”时，严格按以下 4 步状态机推进：

```mermaid
flowchart TD
    START([触发 /release-curator]) --> S1{步骤 1: 智能探测版本跃迁范围}
    S1 -- 自动感知基线与目标 --> S1_RESOLVE[解析 BaseRef 与 TargetRef<br/>计算 commit 差异与变动文件统计]
    S1_RESOLVE --> S2{步骤 2: 多源事实采集与提取}
    S2 --> S2_HARVEST[提取 git log 增量、PR Merge 信息<br/>与 docs/doc/wiki 文档差异]
    S2_HARVEST --> S3{步骤 3: 语义聚类与结构化合成}
    S3 --> S3_SYNTH[按 Keep a Changelog + GitHub Release 规范<br/>输出 Features / Infra / Fixes / Breaking 等维度]
    S3_SYNTH --> S4{步骤 4: 交付物自适应分发与落盘}
    S4 --> DONE([输出完整交付物与发布指引])
```

---

## Step 1: 确定版本跃迁范围与基线 (Range Resolution Engine)

必须依据客观事实确定当前发布的跃迁区间 `[BaseRef .. TargetRef]`：

### 1.1 基线版本 (`BaseRef`) 决策策略
按以下优先级依次回溯探测：
1. **可达 Git Tag**：执行 `git describe --tags --abbrev=0`（获取当前分支 HEAD 最近的祖先 Tag）；
2. **全局最新时间 Tag**：若上述命令无输出，执行 `git tag -l --sort=-creatordate`，取首个符合语义化版本（如 `v*.*.*` 或 `*.*.*`）的 Tag 作为基线；
3. **既有 CHANGELOG 探测**：若 Git Tag 未打，但仓库根目录存在 `CHANGELOG.md`，解析顶部最新已记录的版本号及对应 commit；
4. **冷启动首发回退 (First Release)**：若仓库无任何 Tag 与历史版本记录，自动判定 `BaseRef = $(git rev-list --max-parents=0 HEAD)`（项目 Root Commit），并提示用户当前为项目初始化首发。

### 1.2 发布目标版本 (`TargetRef`) 决策策略
1. **用户显式指定**：若用户指令包含版本参数（如 `/release-curator v2.8.0` 或 `/release-curator 2.8.0`），直接以此为 `TargetRef`；
2. **工程描述元数据自动嗅探**：若未显式指定，按以下技术栈规则嗅探项目版本：
   - **Java (Maven)**：读取 `pom.xml` 中 `<project>` 下的 `<version>` 节点；
   - **Java / Kotlin (Gradle)**：读取 `build.gradle` 或 `build.gradle.kts` 中的 `version = '...'`；
   - **Node.js / Web**：读取 `package.json` 中的 `"version"` 字段；
   - **Python**：读取 `pyproject.toml` 中的 `version`，或 `setup.py` / `setup.cfg`；
   - **Rust**：读取 `Cargo.toml` 中 `[package]` 下的 `version`；
   - **.NET / C#**：读取 `*.csproj` 或 `Directory.Build.props` 中的 `<Version>`；
   - **Go / 其他纯 Git 项目**：默认遵循 Git Tag 驱动。
3. **版本比对与确认**：
   - 若嗅探出的元数据版本严格大于 `BaseRef`（或携带 `-SNAPSHOT` / `-dev` 后缀），自动清洗后缀后作为建议目标版本；
   - 若元数据版本与 `BaseRef` 相同或无法探测，基于 SemVer 规则提供建议递增版本（如 `v1.2.3` 建议 Patch `v1.2.4` 或 Minor `v1.3.0`），并向用户请求快速确认。

### 1.3 差异区间锁定
锁定 `BaseRef..TargetRef`（当前未提交工作区比对使用 `BaseRef..HEAD`）。
执行并记录基础差异度量：
- 变动提交列表：`git log BaseRef..HEAD --no-merges --pretty=format:"%h - %s (%an)"`
- PR/合并记录：`git log BaseRef..HEAD --merges --oneline`
- 文件变动统计：`git diff --stat BaseRef..HEAD`

---

## Step 2: 多源事实采集与差异提取 (Fact Harvesting)

收集并整合三层事实，确保不遗漏、无幻觉：

### 2.1 Git 增量提交分析 (Primary Source)
对所有 commit message 进行模式解析，优先匹配 Conventional Commits 规范：
- `feat(...)?:` -> 业务特性与功能增强
- `fix(...)?:` -> 缺陷修复与稳定性加固
- `perf(...)?:` / `refactor(...)?:` -> 性能优化与底层重构
- `build(...)?:` / `ci(...)?:` / `chore(...)?:` -> 基础设施与构建更新
- `docs(...)?:` -> 文档更新与技术方案
- `BREAKING CHANGE:` 或 `!:` -> 破坏性变更与升级需知

### 2.2 受控文档差异感知 (Secondary Source)
自适应扫描当前仓库中的技术文档目录：
- 常见候选目录：`docs/`、`doc/`、`doc/wiki_staging/`、`doc/reaticle_docs/`、`wiki/`；
- 获取在 `[BaseRef..HEAD]` 范围内**新增或被重大修改**的 Markdown 文档；
- 提取每篇改动文档的 `# H1 标题`、核心要点与所属模块，作为大颗粒度方案特性的详述事实补充。

### 2.3 关键系统路径变动嗅探 (Tertiary Source)
通过 `git diff --name-only BaseRef..HEAD` 检查是否存在以下高敏感文件变动：
- 数据库升级脚本（如 `*.sql`、`migrations/`、`flyway/`）；
- 容器与部署配置（如 `Dockerfile`、`docker-compose*.yml`、`k8s/`、`helm/`）；
- 核心配置文件模式变动（如 `application.yml`、`config.json`、`.env.example`）。

---

## Step 3: 语义聚类与标准化 Release Notes 合成

必须输出符合规范的标准化 Markdown 交付物，结构要求如下：

```markdown
# Release Notes - vX.Y.Z (发布日期)

## 📌 版本概述 (Overview)
[简明扼要概括本版本演进的核心主题、主要架构里程碑与重大升级]

---

## 🚀 核心特性与功能增强 (Key Features & Enhancements)
- **[模块名/范围] 特性简述**：具体能力描述与业务价值，关联 Commit 或 PR。
- ...

---

## ⚡ 性能优化与架构重构 (Performance & Refactoring)
- **[模块名] 优化要点**：降低延迟/节省内存/重构解耦细节。
- ...

---

## 🐳 基础设施、容器与构建 (Infrastructure & Delivery)
- **容器与环境演进**：Docker / CI/CD 流水线 / 依赖版本跃迁。
- ...

---

## 🐛 缺陷修复与自愈 (Bug Fixes & Stability)
- **[模块名] 缺陷修复**：修复的具体现象、自愈机制与根因规避。
- ...

---

## ⚠️ 升级指南与破坏性变更 (Migration & Breaking Changes)
- **配置与接口兼容性**：弃用字段说明、新增强制配置项。
- **数据库/状态迁移**：需执行的增量迁移脚本或注意事项。
*(若本次为向下完全兼容的平滑升级，明确标注：“本版本完全向后兼容，无破坏性变更。”)*

---

## 📚 关联文档与提交统计 (References & Contributors)
- **变动统计**：共计 X 个 Commits，修改 Y 个文件，新增 +M 行 / 移除 -N 行。
- **关联设计与 Wiki**：[方案文档标题](相对路径或页面链接)
```

---

## Step 4: 交付物自适应分发与落盘 (Delivery Dispatching)

生成完毕后，自动执行以下标准化分发：

1. **版本发布文档自适应落盘**：
   - 优先探测仓库文档结构：
     - 若存在 `doc/wiki_staging/` -> 写出至 `doc/wiki_staging/Release-Notes-vX.Y.Z.md`；
     - 否则若存在 `docs/` 或 `doc/` -> 写出至 `docs/releases/Release-Notes-vX.Y.Z.md`（或 `doc/` 对应发布目录）；
     - 否则 -> 直接写出至仓库根目录 `Release-Notes-vX.Y.Z.md`。
2. **CHANGELOG 增量安全注入**：
   - 检查根目录下是否存在 `CHANGELOG.md`；
   - 若存在：解析文件顶部第一个已存在版本标题位置，在保持历史完整的前提下，无损插入符合 *Keep a Changelog* 格式的最新版本块；
   - 若不存在：新建包含标准前言的 `CHANGELOG.md` 并写入本次记录。
3. **GitHub Release 便捷文案与发布指令**：
   - 在对话中输出紧凑格式的发布摘要（便于在 GitHub Releases 网页一键粘贴）；
   - 提供一条直接可执行的 GitHub CLI 命令：
     ```bash
     gh release create vX.Y.Z ./Release-Notes-vX.Y.Z.md --title "vX.Y.Z - 核心特性概括"
     ```
4. **Wiki 导航联动 (可选)**：
   - 若仓库接入了 GitHub Wiki 体系（如存在 `_Sidebar.md` 或 `Home.md`），自动在版本导航列表顶部挂载新版本页面链接。
