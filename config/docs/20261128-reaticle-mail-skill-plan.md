<!-- config/docs/20261128-reaticle-mail-skill-plan.md -->
# `reaticle-mail` 全局固化 Skill 架构与实施方案

> **目标归档路径**：[20261128-reaticle-mail-skill-plan.md](file:///c:/Users/Reaticle/.gemini/config/docs/20261128-reaticle-mail-skill-plan.md)（受 `config/` 系统写保护边界限制，本方案先行输出至会话 Artifact 目录，供审阅后手动落盘至 `config/docs/`）
> **前置基线文档**：[20261127-mailgun-gmail-antigravity-plan.md](file:///c:/Users/Reaticle/.gemini/config/docs/20261127-mailgun-gmail-antigravity-plan.md)

## Goal Description
- **Objectives**: 将“收信检查 Gmail、发信默认选择 Mailgun（`@reaticle.com`，除非人工明确指定 Gmail）、个人签名选择（`CQCRED` / `CQU`）及发信前强制人工确认”固化为 Antigravity 全局 Skill（`C:\Users\Reaticle\.gemini\config\skills\reaticle-mail\SKILL.md`），解决 `config/docs/` 无法被跨会话自动发现的问题，同时利用 Skill 的渐进式披露（Progressive Disclosure）机制避免对非邮件任务造成上下文 Token 膨胀。
- **Constraints & Hard Boundaries**:
  - **Antigravity Skill 发现与格式边界**：必须放置于 `C:\Users\Reaticle\.gemini\config\skills\reaticle-mail\SKILL.md`，YAML Frontmatter 须包含小写连字符 `name: reaticle-mail` 及第三人称触发导向的 `description`。
  - **系统写保护边界**：`C:\Users\Reaticle\.gemini\config\` 目录受宿主系统写保护规则限制（`write_file` / `edit_file` 会被拒绝），因此由 `/builder` 生成最终 `SKILL.md` 内容后，需由人工（或外部拷贝）落盘至目标路径。
  - **通道路由硬边界**：
    - **收信**：统一通过 `gmail` 插件检索/读取经 Cloudflare Email Routing 转发的邮件及线程头（`Message-ID` / `References`）。
    - **发信（默认）**：默认通过 `mailgun` MCP（`post-v3-domain-messages`）以 `y.wang@reaticle.com` 身份发送；回复邮件须携带 `In-Reply-To` 与 `References`。
    - **发信（例外）**：仅当用户在指令中**显式指定使用 Gmail 发送**时，才切换至 `gmail` 插件发信。
  - **强制人工确认门禁（HITL）**：任何发信工具调用前，必须先输出包含通道、收发件人、主题、线程头及含签名的完整正文预览，未经用户明确确认严禁调用发信接口。
  - **单一事实源边界**：Skill 落地后，`reaticle-mail/SKILL.md` 作为签名库与发信流程的唯一运行时权威源；原方案文档中的签名章节应标注以 Skill 为准，避免双处漂移。

## Fact Grounding & Prerequisites (事实锚定与前置验证)
- **本地已核验事实**：
  - `C:\Users\Reaticle\.gemini\config\skills\` 当前包含 `analyzer`、`builder`、`collector`、`orchestrator`、`researcher`、`reviewer`、`verifier`，无 `reaticle-mail` 命名冲突。
  - [skills.md](file:///C:/Users/Reaticle/.gemini/antigravity/builtin/skills/agy-customizations/docs/skills.md) 规范了 `skills/<skill_name>/SKILL.md` 目录结构、Frontmatter 契约及渐进式披露最佳实践。
  - [20261127-mailgun-gmail-antigravity-plan.md](file:///c:/Users/Reaticle/.gemini/config/docs/20261127-mailgun-gmail-antigravity-plan.md#L54-L122) 已明确五步操作闭环及 `CQCRED`、`CQU` 完整签名文本。
  - 当前会话已加载 `mailgun` MCP（含 `post-v3-domain-messages`、`post-v3-domain-templates`）与 `gmail` 插件 Skill。
- **[Requires /collector] (本地事实基准)**：
  - `/builder` 编制 `SKILL.md` 中的 Mailgun 发信参数示例前，应先读取 `<appDataDir>\mcp\mailgun\post-v3-domain-messages.json`，核验其精确入参字段名（如 `h:In-Reply-To` / `h:References` 或 `headers` 结构），严禁凭记忆编造参数契约。
- **Unverified Assumptions (未验证假设清零)**：
  - `post-v3-domain-messages` 对自定义邮件头（`In-Reply-To` / `References`）及 `text`/`html` 字段的具体 Schema 名称尚待读取上述 JSON Schema 文件后确认。

## Proposed Changes

### 1. Architecture & System Decomposition
- **Skill 目录结构**：采用单文件轻量化结构（2 套签名合计不足 40 行，直接内联于 `SKILL.md` 可避免额外 `read_file` 往返，符合渐进式披露最优粒度；后续若签名扩充至 $>5$ 套，再拆分为 `references/signatures.md`）：
  ```text
  C:\Users\Reaticle\.gemini\config\skills\reaticle-mail\
  └── SKILL.md
  ```
- **核心章节设计（`SKILL.md` 逻辑分层）**：
  1. **YAML Frontmatter**：`name: reaticle-mail`，`description` 覆盖触发词（读取/检索 Gmail 邮件、以 `@reaticle.com` 或 Mailgun 回复/发送邮件、选择个人签名 `CQCRED`/`CQU`）。
  2. **Channel Routing Policy（通道路由契约）**：明确“收信 -> Gmail；发信 -> 默认 Mailgun (`reaticle.com`)；人工显式要求 -> Gmail”的决策矩阵。
  3. **Execution Workflow（五步状态机）**：
     - Step 1：收信/上下文采集（`gmail` 插件读取邮件与线程标识）。
     - Step 2：拟稿与签名匹配（显式代号优先，否则按商务/学术语境推荐或询问 `CQCRED` / `CQU` / 无签名）。
     - Step 3：载荷格式化（纯文本 `text` 剥离 Markdown 链接仅留 `y.wang@reaticle.com`；`html` 转为 `<a href="mailto:y.wang@reaticle.com">...</a>`）。
     - Step 4：强制预览与人工确认门禁（展示通道、`From`、`To`、`Subject`、线程头、完整正文与签名，阻塞等待放行）。
     - Step 5：投递与回执（调用 `post-v3-domain-messages` 或按需 `gmail` 发信，返回 Message ID）。
  4. **Signature Registry & Maintenance（签名库与维护入口）**：内联 `CQCRED`、`CQU` 标准块及新增/更新格式约定。

### 2. Work Breakdown Structure (WBS)

| WBS 编号 | 任务名称 | 执行主体 | 具体操作与交付内容 | 前置依赖 | 完成标志 (DoD) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1.1** | 核验 Mailgun 发信 Schema | **【Agent 执行】** | 读取 `mcp/mailgun/post-v3-domain-messages.json`，确认 `from`/`to`/`subject`/`text`/`html` 及线程头参数契约。 | — | 参数字段契约完全核实 |
| **1.2** | 编制 `SKILL.md` 内容 | **【Agent 执行】** (`/builder`) | 依据本方案与 1.1 核验结果生成完整 `SKILL.md`（输出至 Artifact 或对话代码块）。 | 1.1 | `SKILL.md` 符合规范且无占位符 |
| **2.1** | 全局 Skill 落盘 | **【人工操作】** | 因 `config/` 受写保护，由人工将生成的 `SKILL.md` 保存至 `C:\Users\Reaticle\.gemini\config\skills\reaticle-mail\SKILL.md`。 | 1.2 | 目标文件存在且编码为 UTF-8 |
| **2.2** | 方案文档同步归档（可选） | **【人工操作】** | 将本方案归档至 `config/docs/20261128-reaticle-mail-skill-plan.md`，并在原方案中注明签名以 Skill 为准。 | 2.1 | 文档索引与单一事实源一致 |
| **3.1** | 跨会话触发与门禁验收 | **【人工 + Agent 联调】** | 新开对话测试“查看最新邮件并拟定回复”，验证 Skill 自动激活、默认路由 Mailgun、签名匹配及确认门禁生效。 | 2.1 | 新会话无需 `@` 文档即可完整走通流程 |

- **Execution Topology**: `Single`（单会话串行推进：核验 Schema -> 生成内容 -> 人工落盘 -> 联调验收；不满足并行门槛）。

## Verification Plan
- **L0 规范与结构校验**：`SKILL.md` 位于 `C:\Users\Reaticle\.gemini\config\skills\reaticle-mail\SKILL.md`，Frontmatter 包含合法 `name` 与第三人称 `description`。
- **L1 跨会话发现校验**：开启全新会话，在系统提示词可用技能列表中可见 `reaticle-mail`；输入非邮件指令时不加载全文，输入邮件指令时自动激活。
- **L2 路由与线程校验**：
  - 常规回复场景：自动通过 Gmail 读取入站邮件并提取 `Message-ID`，默认生成 Mailgun（`y.wang@reaticle.com`）待发预览。
  - 例外覆盖场景：明确要求“用 Gmail 回复”时，预览通道切换为 Gmail。
- **L3 门禁与签名校验**：
  - 未得到“确认发送”前，严禁触发 `post-v3-domain-messages` 或 Gmail 发信。
  - `CQCRED` 与 `CQU` 签名文本逐字准确，纯文本与 HTML 邮箱链接格式正确。
