<!-- 2026-09-07-Global-Workflows-Deprecation-and-Skills-Migration -->
# 全局工作流废弃与技能架构演进更新报告

- **文档状态**：RELEASED / OFFICIAL SPECIFICATION
- **发布日期**：2026-09-07
- **变更主体**：Antigravity 全局定制体系（Customization System）
- **影响范围**：`config/global_workflows/`（已废弃）、`config/skills/`（新基准）、`config/docs/`（文档归集）

---

## 1. 变更事实与背景 (Change Facts & Background)

### 1.1 官方废弃事件
随着 Antigravity 定制系统（Customization System）向模块化、按需加载与工具集成方向的深度演进，官方正式废弃了早期的 `global_workflows`（全局工作流）机制。原全局工作流机制将提示词文档集中平铺存放，在上下文管理、脚本执行扩展及多级项目继承方面存在架构局限性。新规范全面转向以 **Skills（技能）** 与 **Rules（规则）** 为核心的现代化定制架构。

### 1.2 物理迁移与资产归集事实
在本次架构升级中，系统已完成以下物理重构与资产清理：
1. **工作流全量解耦与备份**：原 `config/global_workflows/` 目录下的 14 个核心工作流平铺 Markdown 文件已全部归档重命名为 `*.md.bak`，并在根配置目录标记 `.migrated` 状态。
2. **技能标准化重构**：14 个工作流完整升级为符合官方规范的独立自包含技能，统一入驻 `config/skills/<skill_name>/SKILL.md`，注入标准 YAML Frontmatter 元数据。
3. **架构文档统一收敛归集**：原挂载于已废弃目录下的 `config/global_workflows/doc/` 整体迁移至配置中心标准文档根目录 `config/docs/`，历史提案文件路径同步更新为 `config/docs/20260903_global_workflows_upgrade_proposal.md`。

---

## 2. 架构对比与范式转变 (Architectural Paradigm Shift)

### 2.1 拓扑演进模型

```mermaid
flowchart TD
    subgraph Legacy [旧机制: Global Workflows (已废弃)]
        GW1[config/global_workflows/*.md]
        GW1 -->|平铺加载 / 静态上下文占用| LLM1[LLM 上下文窗口]
        GW1 -.->|无脚本封装能力 / 纯文本依赖| LLM1
    end

    subgraph Modern [新架构: Modular Skills & Customization Root]
        S_META[Skill YAML Frontmatter<br/>仅注入 name & description]
        S_BODY[SKILL.md 正文]
        S_SCRIPTS[scripts/ 独立可执行脚本]
        S_REFS[references/ & resources/ 基准源]

        S_META -->|轻量注册| CTX[LLM 动态上下文]
        CTX -->|模型决策匹配 / 显式 Slash Command| TRIGGER{按需激活}
        TRIGGER -->|Progressive Disclosure| S_BODY
        TRIGGER -->|CLI / Runtime 调用| S_SCRIPTS
        TRIGGER -->|查阅 SSOT| S_REFS
    end
```

### 2.2 核心维度对比矩阵

| 评估维度 | 旧机制：Global Workflows | 新架构：Skills Architecture | 架构收益 |
| :--- | :--- | :--- | :--- |
| **上下文管理** | 全量/大段注入或高底噪占用，消耗上下文预算 | **渐进式披露（Progressive Disclosure）**，默认仅注册名称与描述 | 极大释放模型上下文容量，降低注意力干扰 |
| **工程封装能力** | 仅支持单一 Markdown 纯文本指令 | 支持目录级封装：携带 `scripts/`、`examples/`、`resources/` | 提示词驱动升级为“代码/脚本 + 提示词”的确定性工程系统 |
| **触发与调度模式** | 隐式注入或易产生指令交叉混淆 | 显式 Slash Command (`/skill-name`) 与基于语义描述的按需激活 | 调度边界确定，消除不同流程之间的指令污染 |
| **发现与覆盖优先级** | 全局平铺，缺乏与项目仓库协同的清晰层次 | **五级严格优先级链条**（Workspace > Declared > Global > Built-in） | 支持仓库级 `.agents/` 覆盖全局配置，实现项目隔离 |
| **生态集成能力** | 孤立运行，无法挂载独立环境与依赖 | 支持与 Plugins、MCP Servers、Lifecycle Hooks 无缝编排 | 具备构建复杂自动化管道与领域专有工具链的能力 |

---

## 3. 技术作用与运行机制 (Technical Mechanism & Function)

### 3.1 渐进式披露机制 (Progressive Disclosure)
- **原理**：在 Agent 会话初始化时，系统仅扫描并加载各 Skill 声明的 YAML Frontmatter（即 `name` 与 `description`），将其作为轻量级索引驻留于系统提示词中。
- **作用**：即使系统配置数十个复杂技能，初始化 Token 消耗始终稳定在常量级别（$O(1)$ 相对开销），彻底杜绝旧机制下多个数十KB工作流堆叠导致的上下文窗口拥塞。
- **动态加载**：仅当用户发起对应 Slash Command（如 `/builder`）或任务意图与技能描述匹配时，Agent 才会通过内部机制按需读取 `SKILL.md` 全文。

### 3.2 资产与能力自包含 (Self-Contained Capability Encapsulation)
- **原理**：每个 Skill 作为一个独立目录存在，其结构规范如下：
  ```
  config/skills/<skill_name>/
  ├── SKILL.md                 # 核心说明书与提示词契约（必须包含 YAML Frontmatter）
  ├── scripts/                 # 可执行 Python/Shell 辅助脚本（确定性算法/工具）
  ├── references/              # 官方规范切片、API Schema、SSOT 基准文档
  ├── resources/               # 模板文件、预制资产
  └── examples/                # 少样本样例（Few-shot prompts/outputs）
  ```
- **作用**：突破纯文本提示词的局限。复杂解析、AST 提取、几何拓扑计算等确定性任务直接交由 `scripts/` 下的本地代码执行（如 `docx-reference-builder`、`typst-docx-publisher`），大模型仅负责协调与生成，大幅提升交付准确率。

### 3.3 多级继承与覆盖控制 (Precedence & Overriding)
- **层级链条**：
  $$\text{Workspace Project (.agents/)} \succ \text{Declared (skills.json)} \succ \text{Global (config/skills/)} \succ \text{Built-in}$$
- **作用**：当特定项目需要定制化 `builder` 或 `verifier` 时，可在该项目根目录 `.agents/skills/` 下定义同名技能，自动覆盖全局默认行为，而无需篡改全局配置文件。

---

## 4. 系统意义与工程价值评估 (Engineering Significance & Value)

遵循严谨的工程事实分离原则（Fact, Judgment, Speculation）：

### 4.1 已验证事实 (Fact)
1. **工作流全面技能化**：系统现有 14 个全局工作流已成功完成向 `config/skills/` 的物理迁移，全部具备有效的前置元数据与标准化结构。
2. **目录职责彻底解耦**：`config/global_workflows/` 内部已无生效中的配置脚本；原设计方案统一收敛至 `config/docs/`，消除了全局配置根目录下的废弃悬空路径。
3. **IDE 与 CLI 无缝识别**：Antigravity IDE 与 CLI 运行时能原生索引 `config/skills/`，保留原 Slash Command（如 `/collector`、`/analyzer`、`/builder` 等）调用习惯。

### 4.2 工程判断 (Judgment)
1. **消除版本漂移与实现断层**：统一使用官方最新推荐的 Customization 规范，使自建工作流体系与平台底层升级保持同构，避免未来版本迭代导致的隐性失效。
2. **大幅降低模型认知负荷**：通过元数据过滤与按需加载，避免在简单任务中强行加载高复杂度的学术写作或基础设施发布规则，降低幻觉率与偏离概率。
3. **提升配置版本控制与可维护性**：`config/docs/` 的设立为后续架构提案、变更记录（ADR）提供了标准归宿，符合软件工程基线管理规范。

### 4.3 长远预期 (Speculation)
1. **向多 Agent 协同体系演进**：标准化的 Skill 单元可直接被后续规划的子代理（Subagents）或分布式工作流编排器无缝复用。
2. **支持跨团队技能分发**：自包含的目录结构便于未来直接打包为独立 Plugin 或 Git Submodule 进行跨环境共享与分发。

---

## 5. 迁移资产对照清单 (Asset Inventory & Migration Mapping)

### 5.1 核心工作流迁移映射表

| 序号 | 技能名称 (`skill_name`) | 原工作流路径 (已备份为 `.bak`) | 新规范技能路径 | 核心定位与职责 |
| :---: | :--- | :--- | :--- | :--- |
| 1 | `collector` | `config/global_workflows/collector.md` | `config/skills/collector/SKILL.md` | 上下文事实收集与资产盘点 |
| 2 | `analyzer` | `config/global_workflows/analyzer.md` | `config/skills/analyzer/SKILL.md` | 系统分析与需求解构 |
| 3 | `builder` | `config/global_workflows/builder.md` | `config/skills/builder/SKILL.md` | 最终交付物生成（代码/配置/文档） |
| 4 | `verifier` | `config/global_workflows/verifier.md` | `config/skills/verifier/SKILL.md` | 独立核验、L0-L3分层排查与双轮熔断 |
| 5 | `reviewer` | `config/global_workflows/reviewer.md` | `config/skills/reviewer/SKILL.md` | 质量门禁评审、架构合规与漂移审查 |
| 6 | `researcher` | `config/global_workflows/researcher.md` | `config/skills/researcher/SKILL.md` | 证据检索与多源事实查证 |
| 7 | `chinese-insight-writer` | `config/global_workflows/chinese-insight-writer.md` | `config/skills/chinese-insight-writer/SKILL.md` | 结构化中文深度行业与技术洞察写作 |
| 8 | `chinese-reflective-writer`| `config/global_workflows/chinese-reflective-writer.md` | `config/skills/chinese-reflective-writer/SKILL.md` | 博客随笔与心智探讨写作 |
| 9 | `english-reflective-writer`| `config/global_workflows/english-reflective-writer.md` | `config/skills/english-reflective-writer/SKILL.md` | 英文随笔、评论与心智探索写作 |
| 10 | `industry-report-writer` | `config/global_workflows/industry-report-writer.md` | `config/skills/industry-report-writer/SKILL.md` | 基础设施与公共战略咨询报告撰写 |
| 11 | `research-paper-writer` | `config/global_workflows/research-paper-writer.md` | `config/skills/research-paper-writer/SKILL.md` | 学术论文结构化写作与审稿人视角把控 |
| 12 | `docx-template-sync` | `config/global_workflows/docx-template-sync.md` | `config/skills/docx-template-sync/SKILL.md` | Word 模板样式指纹逆向提取与同步 |
| 13 | `typst-archiver` | `config/global_workflows/typst-archiver.md` | `config/skills/typst-archiver/SKILL.md` | 历史 Word 逆向双阶段清洗与归档 |
| 14 | `typst-publisher` | `config/global_workflows/typst-publisher.md` | `config/skills/typst-publisher/SKILL.md` | Typst 高保真排版与样式注水编译交付 |

### 5.2 架构文档资产迁移表

| 原资产路径 | 现资产路径 | 文档性质 | 当前状态 |
| :--- | :--- | :--- | :--- |
| `config/global_workflows/doc/20260903_global_workflows_upgrade_proposal.md` | `config/docs/20260903_global_workflows_upgrade_proposal.md` | 架构升级提案（分层防御、双轮熔断） | BASELINE ARCHITECTURE / 已收敛 |
| *(新建)* | `config/docs/20260907_global_workflows_deprecation_and_skills_migration.md` | 架构重大演进与废弃更新报告 | RELEASED / 本文档 |

---

## 6. 维护准则与后续治理 (Governance & Maintenance SOP)

1. **废弃目录禁止写入**：`config/global_workflows/` 仅作为历史版本比对与回滚安全缓冲区（保留 `.bak`），严禁在其中新增任何工作流文件或文档。
2. **新技能开发契约**：
   - 必须通过独立目录 `config/skills/<name>/` 承载；
   - 必须包含 `SKILL.md`，并在首部定义准确的 YAML Frontmatter（`name` 与精确概括职责的 `description`）；
   - 如包含确定性脚本计算，统一存放于同级 `scripts/` 目录中，并通过标准化 CLI 接口调用。
3. **架构文档统一归档**：所有全局级别的系统分析、设计提案、架构决策记录（ADR）统一维护在 `config/docs/` 下，命名遵循 `YYYYMMDD_<topic>.md` 规范。
