---
name: reaticle-mail
description: >-
  Manage personal domain email (`@reaticle.com`) and Gmail workflows: read and
  search inbound messages via the `gmail` skill, draft replies or new emails
  with `CQCRED`/`CQU` signatures, enforce mandatory human confirmation before
  dispatch, and send by default via Mailgun MCP (`y.wang@reaticle.com`) unless
  the user explicitly specifies Gmail.
---

# `reaticle-mail` Email Workflow Skill

## 1. Channel Routing Policy

- **Inbound (Read / Search / Thread Inspection)**: Always use the `gmail` skill (`gmail readonly search`, `gmail readonly read`, etc.) to inspect incoming emails—including messages sent to `@reaticle.com` and forwarded via Cloudflare Email Routing.
- **Outbound (Default = Mailgun)**: Unless the user explicitly requests sending via Gmail, always send via the `mailgun` MCP tool `post-v3-domain-messages`:
  - `domain_name`: `"reaticle.com"`
  - `from`: `"y.wang@reaticle.com"` (default; replace prefix only if the user explicitly specifies another `@reaticle.com` address)
  - `to`: array of recipient email strings (and optional `cc` / `bcc` arrays)
  - `subject`: string (preserve `Re: ...` for replies)
  - `text` / `html`: formatted body with selected signature
  - Threading headers for replies: pass `In-Reply-To` and `References` (per `post-v3-domain-messages` schema header parameter `h_X-My-Header`, e.g., `h:In-Reply-To=<msg-id>`).
- **Outbound (Explicit Override = Gmail)**: Only when the user explicitly states to send via Gmail (e.g., "用 Gmail 发"), use the `gmail` skill (`mutate send` / `mutate reply`).

## 2. Execution Workflow

1. **Read & Extract Context (Inbound / Reply)**:
   - Use `gmail` skill to locate the target email/thread.
   - Extract sender, recipients, `Subject`, `Message-ID`, and `References`.
2. **Draft & Select Signature**:
   - If the user specified a signature ID (`CQCRED` or `CQU`), apply it.
   - Otherwise, infer from context (`CQCRED` for business/Chongqing Credit; `CQU` for academic/Chongqing University) and propose it, or ask the user which signature (or none) to use.
   - Format email address links by payload type:
     - **`text` (plain text)**: strip Markdown link syntax and use plain `y.wang@reaticle.com`.
     - **`html` (HTML)**: render as `<a href="mailto:y.wang@reaticle.com">y.wang@reaticle.com</a>`.
3. **Mandatory Human Confirmation Gate (HITL)**:
   - Before calling any outbound send tool (`post-v3-domain-messages` or `gmail mutate send`/`reply`), output a complete preview in chat:
     - **Channel**: `Mailgun (reaticle.com)` or `Gmail`
     - **From**: `y.wang@reaticle.com` (or specified prefix/Gmail account)
     - **To / Cc / Bcc**
     - **Subject**
     - **Threading Headers** (`In-Reply-To` / `References`, if replying)
     - **Full Body + Selected Signature**
   - Wait for explicit user approval (e.g., "确认发送", "发送", "OK"). Never send without confirmation.
4. **Dispatch & Report**:
   - Execute the confirmed send call and report the returned message ID and delivery status.

## 3. Signature Registry (Single Source of Truth)

### 1. `CQCRED` (商务 / 重庆征信场景)
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

### 2. `CQU` (学术 / 重庆大学场景)
```text
---------
发送自 汪杨 重庆大学
SINCERELY YOURS,
PhD. YANG WANG
SCHOOL OF CIVIL ENGINEERING
CHONGQING UNIVERSITY,CHINA
[y.wang@reaticle.com](mailto:y.wang@reaticle.com)
```

### Signature Maintenance
- **Update**: Edit the corresponding code block above and send a test email to a secondary address to verify line breaks and link rendering.
- **Add**: Append `### N. <SIGNATURE_ID> (<适用场景>)` using an uppercase ID and a `text` code block with `---------` header, sign-off, and contact email.
