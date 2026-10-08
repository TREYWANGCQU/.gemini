<!-- 2026-09-07-Skills-Assets-Taxonomy-and-Scripts-Evaluation -->
# Skills 资产全景分布与脚本（scripts）准入判定评估报告

- **文档状态**：APPROVED / ARCHITECTURAL DECISION RECORD (ADR)
- **发布日期**：2026-09-07
- **评审人**：Quality Gate Reviewer (`/reviewer`)
- **评审结论**：PASS（准予基线归档）
- **关联基线**：
  - [20260907_global_workflows_deprecation_and_skills_migration.md](2026-09-07-Global-Workflows-Deprecation-and-Skills-Migration)
  - [20260903_global_workflows_upgrade_proposal.md](2026-09-03-Global-Workflows-Upgrade-Proposal)

---

## 1. 质量门禁评审意见 (Reviewer Quality Gate Audit)

针对前期 `/analyzer` 输出的“config\skills 资产全景分布及 `/verifier`、`/researcher` 脚本补充必要性分析方案”，质量门禁组依照 `/reviewer` 规范进行多维审计，审计结论如下：

### 1.1 评审维度核验
1. **需求对齐性 (Requirement Alignment)**：
   - 全面覆盖了 `config/skills` 现有 21 项技能资产的分布分析；
   - 深入针对 `/verifier`、`/researcher`、`/collector`、`/builder` 针对性回答了“是否有必要补充 scripts”的核心诉求，逻辑推导闭环，无漏项。
2. **变更范围合规 (Scope Compliance)**：
   - 聚焦全局技能体系的治理与脚本准入规约，未引入无关配置变更或越界重构。
3. **架构契约与版本合规 (Architecture Compliance)**：
   - 严格遵循 Antigravity Customization System 官方规范，与已发布的《全局工作流废弃与技能架构演进更新报告》中“渐进式披露”及“自包含能力封装”机制完全同构；
   - 严防向通用认知技能中硬编码项目特定工具的架构污染。
4. **质量与 AI 痕迹审计 (Quality & AI Artifacts)**：
   - 全文采用硬核工程语言，论证具备严密的推论边界与事实分离，杜绝“全能”、“绝对”、“最佳实践”等虚浮用词。

### 1.2 评审裁定
- **FINAL_STATUS**: `PASS`
- **REQUIRED_ACTIONS**: 将分析结论整理收敛为架构决策记录（ADR），固化至 `config/docs/` 统一归集。
- **MERGE_DECISION**: `APPROVED`，立即归档执行。

---

## 2. 变更事实与问题陈述 (Context & Problem Statement)

在完成了原 `global_workflows` 向 `config/skills/` 的标准化迁移后，系统形成了包含 21 项独立技能的自包含资产池。其中 6 项技能自带 `scripts/` 辅助可执行脚本，而其余 15 项技能仅包含 `SKILL.md` 契约文档。

随着研发工作流的深入，引发了核心工程疑问：
> **像 `/verifier`、`/researcher` 等通用型研发元认知技能，是否有必要像 `office-parser`、`ai-lyrics-aligner` 一样为其编写并补充配套的 `scripts/` 脚本？**

本报告基于确定性计算与多态性成本博弈，对全量资产进行象限切分，并正式确立脚本准入机制。

---

## 3. 技能资产全景四层拓扑分布 (Skills Taxonomy & Topology)

根据**计算确定性（Algorithmic Determinism）**与**认知抽象层级（Cognitive Abstraction）**，全局 21 项技能划分为四大象限层级：

```mermaid
flowchart TD
    subgraph Tier1 [Tier 1: 确定性引擎技能 (必须配置 scripts/)]
        T1_1[ai-lyrics-aligner<br/>人声分离与逐字对齐]
        T1_2[audio-metadata-manager<br/>多媒体 Tag/封面无损嵌入]
        T1_3[docx-reference-builder<br/>Word XML 解包与样式指纹提取]
        T1_4[office-parser<br/>办公文档与PDF切片提取]
        T1_5[typst-docx-publisher<br/>Pandoc AST 转换与样式注水]
        T1_6[word-to-typst-archiver<br/>DOCX 逆向清洗与 Typst 序列化]
    end

    subgraph Tier2 [Tier 2: 编译与流程编排技能 (纯流程 / 脚本薄包装)]
        T2_1[docx-template-sync<br/>同步并驱动 reference builder]
        T2_2[typst-publisher<br/>调度 publisher 并执行大纲质检]
        T2_3[typst-archiver<br/>两阶段差异清洗与安全合流]
        T2_4[typst<br/>语义排版规则与本地模板]
    end

    subgraph Tier3 [Tier 3: 通用研发元认知技能 (认知契约 / 脚本非必须)]
        T3_1[collector<br/>上下文盘点与风险分流]
        T3_2[analyzer<br/>系统分析与需求解构]
        T3_3[builder<br/>高标准交付物生成]
        T3_4[verifier<br/>L0-L3分层核验与双轮熔断]
        T3_5[reviewer<br/>质量门禁与AI痕迹审查]
        T3_6[researcher<br/>多级证据与事实查证]
    end

    subgraph Tier4 [Tier 4: 领域语义与专业写作技能 (纯思维范式 / 严禁脚本)]
        T4_1[chinese-insight-writer]
        T4_2[chinese-reflective-writer]
        T4_3[english-reflective-writer]
        T4_4[industry-report-writer]
        T4_5[research-paper-writer]
    end
```

### 全量资产属性清单

| 序号 | 技能标识 | 所属层级 | 脚本资产现状 | 核心定位与技术底座 |
| :---: | :--- | :---: | :---: | :--- |
| 1 | `ai-lyrics-aligner` | Tier 1 | 包含 (3 个 Python 脚本) | 音频 stem 对齐、LRC 格式化、文本正则清洗 |
| 2 | `audio-metadata-manager` | Tier 1 | 包含 (CLI + 5 个 core 模块) | Mutagen 标签读写、ID3/FLAC 嵌入、CI 审计 |
| 3 | `docx-reference-builder` | Tier 1 | 包含 (1 个 Python 脚本) | Word XML 逆向解包、段落属性聚类合成 |
| 4 | `office-parser` | Tier 1 | 包含 (1 个 Python 脚本) | OpenPyXL/python-docx/PyPDF 结构提取 |
| 5 | `typst-docx-publisher` | Tier 1 | 包含 (1 个 Python 脚本) | Pandoc 管道、XML AST 预处理、样式重注入 |
| 6 | `word-to-typst-archiver` | Tier 1 | 包含 (1 个 Python 脚本) | XML 网格解构、Typst 语法序列化、四层清洗 |
| 7 | `docx-template-sync` | Tier 2 | 无 | 标杆模板逆向提取与同步工作流编排 |
| 8 | `typst-publisher` | Tier 2 | 无 | Typst 正向编译质检与版本基线交付工作流 |
| 9 | `typst-archiver` | Tier 2 | 无 | 逆向差异比对与 Reconcile 合流工作流 |
| 10 | `typst` | Tier 2 | 无 | Typst 语义排版与本地模板语法规范 |
| 11 | `collector` | Tier 3 | 包含 (1 个轻量脚本) | 上下文事实收集、SSOT 基准挂载、未知分流（配置 `preview_tree.py`） |
| 12 | `analyzer` | Tier 3 | 无 | 系统架构解构、边界矩阵、WBS 与验收标准 |
| 13 | `builder` | Tier 3 | 无 | 最终交付物生成、最小差异补丁生成 |
| 14 | `verifier` | Tier 3 | 无 | L0-L3 自底向上验证、2-Fail 熔断、假设矩阵 |
| 15 | `reviewer` | Tier 3 | 无 | 需求对齐、范围审查、AI 模板化表达审计 |
| 16 | `researcher` | Tier 3 | 无 | 证据分级 (Level A/B/C)、官方标准/文档调研 |
| 17 | `chinese-insight-writer` | Tier 4 | 无 | 中文深度行业评论、技术复盘写作范式 |
| 18 | `chinese-reflective-writer`| Tier 4 | 无 | 中文个人博客、读书随想、心智漂流范式 |
| 19 | `english-reflective-writer`| Tier 4 | 无 | 英文随笔、评论与心智探索写作范式 |
| 20 | `industry-report-writer` | Tier 4 | 无 | 基础设施与公共数字化宏观行业研报范式 |
| 21 | `research-paper-writer` | Tier 4 | 无 | 学术论文结构化写作与同行评审视角把控 |

---

## 4. 核心技能脚本必要性深度论证 (Scripts Necessity Evaluation)

### 4.1 `/verifier`：是否有必要补充 scripts？
- **结论**：**核心流程无必要；严禁将其绑定至具体项目的测试或构建工具链。**
- **论证理由**：
  1. **项目技术栈多态性冲突 (Polymorphism Dilemma)**：
     全局技能面向任意工作区（Workspace）。若在全局 `verifier` 中编写特定的验证脚本（如 `run_test.py` 或 `check_linter.sh`），势必硬编码调用某种语言的 Runner（如 pytest、cargo、vitest）。当用户在其他技术栈（如 Typst 排版、C++、Go 仓库）中使用 `/verifier` 时，全局脚本将直接沦为无用垃圾代码或报错炸弹。
  2. **原生能力重叠与执行路径冗余 (Redundancy)**：
     Agent 原生具备 `run_command` 工具，能够根据所处项目的实际环境（`package.json`、`Cargo.toml`、`Makefile`）动态自主调用宿主测试命令（如 `cargo check`、`pnpm test`）。在 Skill 内部增加一层脚本外壳，属于反模式封装。
  3. **定位错位风险 (Misalignment of Responsibilities)**：
     `/verifier` 的核心壁垒在于**“逻辑推演的独立性”**与**“对自身局部最优假设的自省机制”**（即 Bottom-up L0->L3 分层核验与双轮熔断）。这些属于高阶思维审查，根本无法被静态脚本替代。
- **唯一允许的可选扩展场景（容许但非必须）**：
  - 仅容许存在**完全语言无关**的静态文本守卫脚本（如 `scripts/verify_placeholders.py`），用于扫描输出中是否残留 `TODO`、`FIXME`、未替换宏定义等违背用户全局规则的硬伤。但此类检查当前直接由 Prompt 契约与 Reviewer 双重拦截已足够胜任。

---

### 4.2 `/researcher`：是否有必要补充 scripts？
- **结论**：**完全无必要 (Strictly No Necessity)。**
- **论证理由**：
  1. **功能重叠与工具覆盖 (Covered by Built-in & Plugin Ecosystem)**：
     - 通用 Web 搜索与网页静态抓取已有系统原生工具（`search_web`、`read_url_content`）；
     - 专业领域的结构化调研已有已安装的 `science` 插件（包含针对 ArXiv、EuropePMC、PubMed、OpenAlex、ChEMBL 等针对学术文献与生物数据的十余个成熟工具）。
  2. **高频维护腐化风险 (High Maintenance Rot)**：
     直接在 `researcher` 内编写爬虫或搜索脚本，极易遭遇第三方反爬虫策略更新、DOM 漂移、鉴权密钥失效等物理阻碍，在全局配置层造成极高维护成本。
  3. **能力核心定位**：
     `/researcher` 的核心资产是 **证据等级分类法（Level A: 官方标准与文档 / Level B: 论文与研报 / Level C: 社区讨论）** 与 **事实/未验证假说分离模型**，它是指导检索行为的“准则仪”，而不是执行抓取的底层爬虫。

---

### 4.3 其他元认知技能的衍生评估

1. **`/collector`**：
   - **评估结果**：**低到中度潜在增益（已作为轻量辅助交付落地）**。
   - **理由**：通过配置纯标准库实现的 `scripts/preview_tree.py`，以受限深度和 Token 预算快速生成目录拓扑并自动识别 `package.json`/`Cargo.toml` 等 SSOT 基准与配置，高效践行了“Preview-First（结构预览优先，杜绝全量吞吐文件）”的全局约束。
2. **`/reviewer`**：
   - **评估结果**：**无需配置独立脚本**。
   - **理由**：审查范围遵循 `git status` 与 `git diff --stat`，直接依托系统原生 CLI 即可无缝运行。
3. **`/builder`**：
   - **评估结果**：**严禁配置任何脚本**。
   - **理由**：生成交付物是根据已验证事实与架构进行的代码/文档综合产出过程，强行加入生成模板脚本会束缚大模型的代码表达能力。

---

## 5. 脚本准入准则与“三不原则” (Inclusion Policy & Governance)

为规范未来新技能的孵化与既有技能的演化，特确立以下**脚本准入判定模型与三不原则**：

### 5.1 准入数学判定模型
$$\text{AllowScript} \iff \frac{\mathcal{D}_{\text{algo}} \times \mathcal{C}_{\text{AST/Binary}}}{\mathcal{P}_{\text{poly}} + \mathcal{M}_{\text{env}} + \mathcal{O}_{\text{native}}} \ge 1.0$$

- $\mathcal{D}_{\text{algo}}$：任务算法的确定性（如特定解包算法、多媒体 tag 格式化为 1.0，思维审查为 0.1）；
- $\mathcal{C}_{\text{AST/Binary}}$：非文本/二进制/树状 AST 处理的复杂度；
- $\mathcal{P}_{\text{poly}}$：跨语言、跨项目多态性成本（通用技能极高）；
- $\mathcal{M}_{\text{env}}$：本地环境依赖与环境腐烂维护成本；
- $\mathcal{O}_{\text{native}}$：与 Agent 原生内建工具的重叠程度。

### 5.2 脚本引入“三不原则”
1. **不写死项目专用技术栈**：全局 `config/skills/` 严禁引入绑定特定语言包管理器、特定单一单元测试框架的运行脚本。项目私有脚本应沉淀在工作区 `.agents/skills/`。
2. **不重复包装运行时原生工具**：严禁为了调用系统的 `git`、`curl`、`cat`、`grep` 或内置 `search_web` 而单独套壳 Python 包装层。
3. **不替代高阶推理决策**：脚本仅负责**数据清洗、二进制读写、复杂拓扑计算**；一切关于“逻辑是否严密”、“架构是否偏离”、“假设是否清零”的审查判定必须由 LLM 推理层与用户把关。

---

## 6. 事实、判断与推论分离清单 (Fact, Judgment & Speculation Separation)

### 6.1 已验证事实 (Fact)
1. 全局配置 `config/skills/` 目前涵盖 21 项技能，现存 6 项自带复杂脚本技能属“底层多媒体或文档逆向引擎”（Tier 1），1 项技能（`/collector`）配置纯标准库零依赖轻量辅助脚本 `preview_tree.py`。
2. `/verifier`、`/researcher`、`/collector`、`/analyzer`、`/builder`、`/reviewer` 自设计之初均为跨语言、跨领域通用的元认知决策规范，此前平铺在工作流中亦从未依赖独立脚本。
3. Agent 运行环境内建具备网络搜索、网页解析、正则文本检索与本地 Shell CLI 调度全量接口。

### 6.2 工程判断 (Judgment)
1. 为 `/verifier` 与 `/researcher` 补充通用脚本不仅不能提升效率，反而会因项目技术栈冲突与环境腐烂带来负向维护负担。
2. 保持通用技能的“纯认知与契约规范”属性，有助于保障其在各类 heterogeneous（异构）项目环境中的最大化移植性与通用覆盖率。

### 6.3 演进预期 (Speculation)
1. `/collector` 的轻量 `preview_tree` 辅助脚本已完成落地验证，完全基于 Python 标准库，支持递归深度限制、文件截断与 SSOT 基准文件自动分类；后续可推荐用户在特定项目的 `.agents/skills/` 中注入特定语言的测试辅助外挂。
