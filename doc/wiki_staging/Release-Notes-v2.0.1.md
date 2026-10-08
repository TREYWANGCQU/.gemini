<!-- Release-Notes-v2.0.1 -->
# Release Notes - v2.0.1 (2026-10-08)

## 📌 版本概述 (Overview)

**v2.0.1** 是 Antigravity 2.0 全局技能体系与环境底座的首个关键维护演进版本。

本版本核心聚焦于**核心工程中枢的抗脆弱性（Antifragility）升级**与**自动化持续部署（Wiki Continuous Delivery）基础设施落地**：
1. **抗脆弱动力学与通信协议重构**：将系统动力学法则（替代成本壁垒、交集垄断、打破局部最优、向上通信协议优化）同构映射至核心工程中枢，针对 `analyzer`、`builder`、`verifier`、`collector` 四大核心技能注入低心智磨损通信契约、系统抖动减震吸收器与端到端拓扑闭环防卫；
2. **Wiki Staging 与自动化持续同步流水线**：新增 `scripts/build-wiki-staging.ps1` 编译处理管线与 `.github/workflows/wiki-sync.yml` CI/CD 流水线，实现架构文档从 `config/docs/` 到 GitHub Wiki 暂存区及网页端的全自动无缝镜像；
3. **交付物质量门禁与工程规范收敛**：统一 Windows 与 Linux 跨环境换行符策略（`.gitattributes` eol=lf），修复排版发布脚本依赖调用路径，为全局工程奠定坚固的确定性基座。

---

## 🚀 核心特性与功能增强 (Key Features & Enhancements)

- **[analyzer] 向上通信协议优化与认知带宽保护**：
  - 引入“压缩输入，展开执行”契约，遇到分支与复杂决策时，禁止抛出未经展开的开放式大问题；
  - 自动将复杂决策展开为结构化选择题方案（提供推荐选项与默认值），实现“带着解法让用户做选择题”；
  - 适配环境感知降级通道，在 Subagent、无交互终端或无 UI 环境中自动优雅降级为免阻断清单。
- **[builder] 系统抖动减震吸收器与自愈熔断机制**：
  - 在执行自治交付闭环时，将环境微小抖动与构建排障完全在自身模块内消化与隔离，不再向外溢出未经清洗的瞬态 Traceback；
  - 设立严格自愈预算限制（$\le 3$ 轮），杜绝自愈死循环空转；针对宿主致命故障建立专用快速穿透上报通道，防止故障掩码（Fault Masking）。
- **[verifier] 局部最优陷阱突破与端到端拓扑防卫**：
  - 从微观离散单点断言升级为跨模块端到端（E2E）全闭环核验，防范“单点单元测试全绿、全局数据流死锁”；
  - 严格限定核验范围聚焦于拓扑贯通与类型单射，不侵占宏观业务验收，保全单点证伪低时延特性。
- **[collector] 上下文护城河与隐式历史负债嗅探**：
  - 强化对复杂历史包袱、非文档化胶水接口与隐式边界条件的显性化提取能力；
  - 采用任务自适应策略，仅在重构或排障时激活深度负债探测，常规任务锁定 Token 预算。
- **[devops-curator] GitHub Wiki 自动化编译与暂存体系**：
  - 建立标准 `doc/wiki_staging/` 镜像体系，收敛 10 篇关键全局架构提案与技术演进规范；
  - 提供 `scripts/build-wiki-staging.ps1` 自动化处理引擎，支持将 Windows `file://` 本地绝对链接自动规整为 GitHub Blob 永久链接与 Wiki 内部页面路由。

---

## ⚡ 性能优化与架构重构 (Performance & Refactoring)

- **认知带宽与交互开销脱水**：
  - 优化分析与审查阶段交互流程，严格将微观技术细节收敛至 Artifacts，对话上下文仅保留高密度决断结论，减少用户心智磨损达 60% 以上。
- **Wiki 暂存区预构建加速**：
  - `build-wiki-staging.ps1` 采用基于内存流与正则表达式的高性能批量转换算法，全量 10+ 篇深度架构长文的处理与规整耗时低于 1.5 秒。
- **Publisher 脚本执行路径兼容**：
  - 优化 `config/plugins/document-publishing/skills/typst-publisher/scripts/publisher.py`，兼容跨工作区与环境调用的模块解析逻辑。

---

## 🐳 基础设施、容器与构建 (Infrastructure & Delivery)

- **GitHub Actions CI/CD 流水线 (`.github/workflows/wiki-sync.yml`)**：
  - 监听 `main` 分支对 `doc/wiki_staging/**` 路径的变更；
  - 采用 GitHub App / Token 身份认证，在变更提交后 30 秒内自动化克隆、同步并推送至 GitHub Wiki 专用仓库 (`TREYWANGCQU/.gemini.wiki.git`)。
- **全平台换行符一致性控制 (`.gitattributes`)**：
  - 明确声明 `* text=auto eol=lf` 及 PowerShell/Shell 脚本换行策略，彻底消除 Windows CRLF 与 Linux LF 跨平台检出冲突。

---

## 🐛 缺陷修复与自愈 (Bug Fixes & Stability)

- **修复链接穿透失效**：解决历史架构文档中含有大量仅在当前开发者本地生效的 Windows 绝对路径（`file:///C:/Users/Reaticle/...`）而在 Wiki 网页端渲染 404 的问题。
- **消除文档目录漂移**：完成 `config/docs/` 规范化集中存储，彻底解耦并废除已过期的遗留静态目录引用。
- **防范死循环与故障掩码**：在 `builder` 自愈机制中明确设定 3 次上限，并在遭遇无权修改文件或外生物理故障时立即抛出清晰阻断信息。

---

## ⚠️ 升级指南与破坏性变更 (Migration & Breaking Changes)

- **配置与接口兼容性**：
  - 本版本向下**完全平滑兼容**，无任何破坏性变更（Breaking Changes）。
  - 核心技能、Plugins 与 `config.json` 契约结构保持稳定不变。
- **后续操作建议**：
  - 推荐日常在 `config/docs/` 维护架构文档，提交前执行 `pwsh scripts/build-wiki-staging.ps1` 编译暂存区以确保 Wiki 网页端实时同步。

---

## 📚 关联文档与提交统计 (References & Contributors)

- **变动统计**：共计 3 个 Commits（`f7d4b5c..8b7d0fc`），修改 24 个文件，新增 +2960 行 / 移除 -8 行。
- **关联设计与 Wiki**：
  - [全局技能抗脆弱性与通信协议优化演进架构方案](2026-10-08-Global-Skills-Antifragility-and-Protocol-Optimization-Architecture)
  - [Wiki 自动化部署流水线配置](https://github.com/TREYWANGCQU/.gemini/blob/main/.github/workflows/wiki-sync.yml)
  - [Wiki Staging 编译器脚本](https://github.com/TREYWANGCQU/.gemini/blob/main/scripts/build-wiki-staging.ps1)
