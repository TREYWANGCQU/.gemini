<!-- config/docs/20261127-mailgun-gmail-antigravity-plan.md -->
# 个人域名邮件 (`reaticle.com`) 与 Antigravity IDE 接入架构方案

> **文档路径**：[20261127-mailgun-gmail-antigravity-plan.md](file:///c:/Users/Reaticle/.gemini/config/docs/20261127-mailgun-gmail-antigravity-plan.md)

## Goal Description
- **Objectives**: 针对 Gmail 于 2027 年 1 月停用第三方域名“Send mail as”别名后无法在 Gmail 内以 `@reaticle.com` 身份回复邮件的痛点，在本地 Antigravity IDE 中同时接入 **Mailgun MCP** 与 **Gmail MCP/插件**，构建“Cloudflare 转传入 Gmail -> IDE 通过 Gmail 读取入站邮件 -> 通过 Mailgun MCP 以 `@reaticle.com` 身份回复”的完整收发闭环。
- **Constraints & Hard Boundaries**:
  - **Gmail 2027-01 政策边界**: 个人 Gmail 永久移除第三方/自定义域名 **Send mail as**、Web **POP3** 拉取及 **Gmailify**；但 **Cloudflare Email Routing 入站自动转发至 Gmail 仍继续有效**。
  - **DNS 隔离边界**: 根域名 `reaticle.com` 的 `MX` 记录必须保留给 Cloudflare Email Routing；Mailgun 仅配置 `SPF`/`DKIM`/`DMARC` `TXT` 记录（或使用子域名如 `mg.reaticle.com`）。
  - **Mailgun 免费版边界**: 1 个自定义域名、100 封/天、约 300 封/小时、1 天日志保留。
  - **本地运行环境**: Node.js `v24.15.0` / npx `11.12.1` 已就绪，MCP 配置位于 [mcp_config.json](file:///c:/Users/Reaticle/.gemini/config/mcp_config.json)。

## Fact Grounding & Prerequisites
- **本地已核验**:
  - [mcp_config.json](file:///c:/Users/Reaticle/.gemini/config/mcp_config.json) 已存在并运行 `npx` 模式的 `stdio` MCP Server。
  - 本地无已连接的 Gmail 插件账号。
- **外部已核验**:
  - Mailgun 官方提供 `@mailgun/mcp-server`（`github.com/mailgun/mailgun-mcp-server`），通过 `MAILGUN_API_KEY` + `MAILGUN_API_REGION` (`us`/`eu`) 即可运行。
  - Antigravity Marketplace 提供官方 `Gmail` 插件（`antigravity-plugins-official/plugin/gmail`）。
- **人工已确认就绪项**:
  - `reaticle.com` 域名 DNS 配置正常（Cloudflare Email Routing `MX` 记录及 Mailgun `SPF`/`DKIM`/`DMARC` 记录已就绪且互不冲突）。
- **待用户侧提供/操作前置项**:
  - Mailgun 账号区域（`us` 或 `eu`）及 API Key（建议 Sending Key 或 Private API Key）。
  - 在 Antigravity Marketplace 安装官方 `Gmail` 插件并完成 OAuth 登录授权。

## Proposed Changes & Decisions
1. **Antigravity IDE 接入 Mailgun MCP**：在 [mcp_config.json](file:///c:/Users/Reaticle/.gemini/config/mcp_config.json) 中增量配置官方 `@mailgun/mcp-server`（`npx -y @mailgun/mcp-server`），提供以 `@reaticle.com` 发信、域名校验、日志/退信查询与模板管理能力。
2. **Antigravity IDE 接入 Gmail 插件/MCP（必选）**：安装官方 `Gmail` 插件（`antigravity-plugins-official/plugin/gmail`）并完成授权，用于检索经 Cloudflare Email Routing 转发至 Gmail 的 `@reaticle.com` 邮件，再由 Mailgun MCP 携带邮件线程头（`In-Reply-To` / `References`）以 `@reaticle.com` 身份发出回复，直接弥补 2027-01 后 Gmail 无法使用自定义别名回复的痛点。
3. **非 IDE 日常客户端兜底（可选）**：若需在手机或桌面独立邮件客户端回复 `@reaticle.com`，可在 Thunderbird / Apple Mail / FairEmail 中配置 Gmail IMAP 收信 + Mailgun SMTP 发信。
4. **Execution Topology**: `Single`（单会话串行推进，按 WBS 依次落地）。

## Work Breakdown Structure (WBS)

| WBS 编号 | 任务名称 | 执行主体 | 具体操作与交付内容 | 前置依赖 | 完成标志 (DoD) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1.1** | 域名 DNS 基线确认 | **【人工操作】（已完成）** | 确认 `reaticle.com` 在 Cloudflare 的 `MX` 转发记录与 Mailgun `SPF`/`DKIM`/`DMARC` 解析正常。 | — | DNS 基线已由人工确认正常 |
| **1.2** | 获取 Mailgun API 凭证 | **【人工操作】** | 登录 Mailgun 控制台确认账号 Region（`us` 或 `eu`），获取用于发信的 `MAILGUN_API_KEY`（建议 Sending/Private Key）。 | 1.1 | 获得可用的 `MAILGUN_API_KEY` 与 `MAILGUN_API_REGION` |
| **1.3** | 安装与授权 Gmail 插件 | **【人工操作】** | 在 Antigravity Marketplace 搜索并安装官方 `Gmail` 插件（`antigravity-plugins-official/plugin/gmail`），完成 Google 账号 OAuth 登录授权。 | — | IDE 内 Gmail 插件状态显示已连接且可读取邮件 |
| **2.1** | 配置 Mailgun MCP Server | **【Agent 执行】** / **【人工填入密钥】** | 在 [mcp_config.json](file:///c:/Users/Reaticle/.gemini/config/mcp_config.json) 中增量写入 `mailgun` 服务配置（`npx -y @mailgun/mcp-server`）；若不在对话中传递明文密钥，由人工在本地填入 `MAILGUN_API_KEY`。 | 1.2 | `mcp_config.json` 语法正确且包含 `mailgun` 配置节点 |
| **2.2** | 校验 Mailgun MCP 启动 | **【Agent 执行】** | 重载 MCP 服务并验证 `@mailgun/mcp-server` 工具列表可正常调用（如域名查询、发信接口）。 | 2.1 | Mailgun MCP 工具在 IDE 中可用且无启动报错 |
| **3.1** | Mailgun 发信与认证头校验 | **【Agent 执行】** + **【人工检查】** | Agent 通过 Mailgun MCP 查询 `reaticle.com` 域名状态并发送测试邮件；人工查收测试邮件，确认邮件头 `SPF`/`DKIM`/`DMARC` 均为 `PASS`。 | 1.1, 2.2 | 测试邮件成功送达且认证头全 `PASS` |
| **3.2** | 入站转发链路验证 | **【人工操作】** | 使用外部邮箱向 `xxx@reaticle.com` 发送一封测试邮件，确认经 Cloudflare Email Routing 正常到达 Gmail 收件箱。 | 1.1 | Gmail 收件箱可收到发往 `@reaticle.com` 的测试邮件 |
| **3.3** | Gmail + Mailgun 回复闭环联调 | **【Agent 执行】** + **【人工确认】** | Agent 通过 Gmail 插件读取 3.2 的测试邮件（提取发件人、主题、`Message-ID`），生成回复内容并经**人工确认发送**后，调用 Mailgun MCP 以 `@reaticle.com` 回复（附带 `In-Reply-To`/`References`）。 | 1.3, 2.2, 3.2 | 外部测试邮箱收到来自 `@reaticle.com` 的回复且会话线程关联正确 |
| **4.1** | 固化回复操作规范（可选） | **【Agent 执行】** | 按需在本地配置中沉淀“读 Gmail -> 拟定回复 -> 人工二次确认 -> Mailgun 发信”的安全交互规则，防止误发邮件。 | 3.3 | 本地规则/Skill 落盘 |
| **4.2** | 桌面/移动端客户端兜底（可选） | **【人工操作】** | 在 Thunderbird / Apple Mail / FairEmail 中配置 Gmail IMAP 收信 + Mailgun SMTP 发信，覆盖非 IDE 场景。 | 1.1, 1.2 | 独立客户端可收发 `@reaticle.com` 邮件 |

## Verification Plan
- **DNS 基线**: 已由人工确认 `reaticle.com` DNS（Cloudflare `MX` + Mailgun `SPF`/`DKIM`/`DMARC`）配置正常。
- **Mailgun MCP 校验**: 通过 `@mailgun/mcp-server` 查询域名状态并发送测试邮件，验证邮件头 `SPF`/`DKIM`/`DMARC` 均为 `PASS`。
- **收发闭环校验**: 验证“外部发信至 `@reaticle.com` -> Cloudflare 转发至 Gmail -> IDE Gmail 插件检索邮件 -> 人工确认 -> Mailgun MCP 以 `@reaticle.com` 回复并保持邮件线程”全链路通畅。

<!-- config/docs/20261127-mailgun-gmail-antigravity-plan.md -->
## 实际使用说明 (Operational Usage Guide)

日常在 Antigravity IDE 中以 `@reaticle.com` 收发邮件遵循“**发起指令 -> 检索/拟稿 -> 选择签名 -> 人工确认 -> 调用发信**”五步闭环：

1. **发起指令**
   - **回复入站邮件**：在对话中指示 Agent 检索 Gmail 收件箱（例如：“查一下来自 `xxx` 关于 `yyy` 的邮件，用 `@reaticle.com` 起草回复，要点是……”）。Agent 将通过 Gmail 插件读取目标邮件，提取发件人、主题（`Subject`）及线程标识（`Message-ID` / `References`）。
   - **主动发起新邮件**：直接提供收件人、主题与正文意图（例如：“用 `y.wang@reaticle.com` 给 `someone@example.com` 发一封邮件，主题为……，内容包括……”）。
2. **选择签名**
   - **显式指定**：在指令中直接指定签名代号（如“使用 `CQCRED` 签名”或“使用 `CQU` 签名”）。
   - **场景推断与确认**：若未显式指定，Agent 应根据邮件语境（商务/重庆征信事务对应 `CQCRED`；学术/重庆大学事务对应 `CQU`）推荐签名，或在草稿阶段询问人工确认使用哪套签名（或不使用签名）。
3. **人工确认（强制门禁）**
   - 在调用任何发信接口前，Agent **必须**在对话中输出完整待发预览，包含：
     - `From`（默认 `y.wang@reaticle.com`）
     - `To`（及 `Cc`/`Bcc`，如有）
     - `Subject`（回复邮件保留 `Re: ...`）
     - 线程头信息（回复时需确认 `In-Reply-To` 与 `References`）
     - 完整正文 + 选定的签名内容
   - 仅在收到用户明确的“确认发送 / 发送 / OK”等放行指令后，才允许进入下一步；未经确认严禁自动发信。
4. **最后发出与回执核验**
   - 用户确认后，Agent 调用 Mailgun MCP 的发信工具（`post-v3-domain-messages`），指定 `domain: "reaticle.com"` 及已确认的发信参数执行投递。
   - 若邮件内容同时包含纯文本与富文本，纯文本载荷（`text`）中的邮箱保持 `y.wang@reaticle.com`，HTML 载荷（`html`）中可渲染为 `<a href="mailto:y.wang@reaticle.com">y.wang@reaticle.com</a>`。
   - 发送完成后，Agent 返回 Mailgun 响应结果（含 `id` 与 `message` 状态）供留存核验。

## 个人签名库与维护规范 (Signature Registry & Maintenance)

### 当前已登记签名

#### 1. `CQCRED`（商务 / 重庆征信场景）
```text
---------
敬祝 安好
敬候 回谕
汪杨
重庆征信有限责任公司
重庆市渝中区化龙桥街道华盛路1号29层, 400010
Should you have any questions or require further information, please do not hesitate to contact me.
YOURS SINCERELY,
Dr. YANG WANG, PhD.
Chongqing Credit Co., Ltd.
29/F, No.1 Huasheng Road, Hualongqiao Street, Yuzhong District, Chongqing, China, 400010
[y.wang@reaticle.com](mailto:y.wang@reaticle.com)
```

#### 2. `CQU`（学术 / 重庆大学场景）
```text
---------
发送自 汪杨 重庆大学
SINCERELY YOURS,
PhD. YANG WANG
SCHOOL OF CIVIL ENGINEERING
CHONGQING UNIVERSITY,CHINA
[y.wang@reaticle.com](mailto:y.wang@reaticle.com)
```

> **发送格式说明**：上述代码块中保留了 `[y.wang@reaticle.com](mailto:y.wang@reaticle.com)` 标记；实际通过 Mailgun 发送时，纯文本（`text`）字段应剥离 Markdown 链接语法仅保留 `y.wang@reaticle.com`，HTML（`html`）字段则转换为标准超链接 `<a href="mailto:y.wang@reaticle.com">y.wang@reaticle.com</a>`。

### 维护、更新与新增规范

1. **单一事实源管理**
   - 本文档的“当前已登记签名”小节作为签名基线；若后续需要将签名与发信守则持久化为全局指令，可同步沉淀至 `c:\Users\Reaticle\.gemini\config\rules\` 下的独立规则文件（如 `email-workflow.md`），并在变更时保持两处一致。
   - 若需在 Mailgun 侧托管模板，亦可通过 Mailgun MCP 的模板接口（`post-v3-domain-templates` / `post-v3-domain-templates-template-versions`）将签名固化为服务端模板变量。
2. **更新现有签名**
   - 直接修改对应代号（如 `CQCRED`、`CQU`）下的代码块内容（如职称、地址、邮编或联系电话变更）。
   - 修改后建议向自有备用邮箱发送一封测试邮件，核验纯文本与 HTML 客户端下的换行及链接渲染是否正常。
3. **新增签名标准格式**
   - 按以下结构在“当前已登记签名”末尾追加新条目，确保 Agent 可按代号精确索引：
     - **标题**：`#### N. <SIGNATURE_ID>（<适用场景说明>）`（`SIGNATURE_ID` 建议使用全大写英文短代号，如 `PERSONAL`、`LAB`）。
     - **内容块**：使用 `text` 代码块包裹完整签名正文（含顶部分隔线 `---------`、中英文落款与联系邮箱）。
   - 新增后在对话中直接引用新代号（例如“使用 `<SIGNATURE_ID>` 签名发信”）即可生效。