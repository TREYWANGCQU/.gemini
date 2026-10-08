# scripts/build-wiki-staging.ps1
<#
.SYNOPSIS
    Builds and stages GitHub Wiki documentation from config/docs.
.DESCRIPTION
    Scans source architecture and specification documents in config/docs,
    normalizes links and formatting, generates Home.md, _Sidebar.md, and _Footer.md,
    and stages output files into doc/wiki_staging/ for automated GitHub Actions deployment.
#>

[CmdletBinding()]
param(
    [string]$DocsRoot,
    [string]$StagingDir
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $DocsRoot) {
    $DocsRoot = Join-Path $RepoRoot "config/docs"
}
if (-not $StagingDir) {
    $StagingDir = Join-Path $RepoRoot "doc/wiki_staging"
}

Write-Host "=== Wiki Curator: Staging Builder ===" -ForegroundColor Cyan
Write-Host "Source Docs Root: $DocsRoot"
Write-Host "Staging Target : $StagingDir"

if (-not (Test-Path $DocsRoot)) {
    throw "DocsRoot does not exist: $DocsRoot"
}

if (-not (Test-Path $StagingDir)) {
    New-Item -ItemType Directory -Path $StagingDir -Force | Out-Null
} else {
    # Clean up existing staging markdown files
    Get-ChildItem -Path $StagingDir -Filter "*.md" -File | Remove-Item -Force
}

$GitHubBlobBase = "https://github.com/TREYWANGCQU/.gemini/blob/main"

# Mapping table from source filename to Wiki page title & slug
$DocMap = [ordered]@{
    "20260903_global_workflows_upgrade_proposal.md" = @{
        PageName = "2026-09-03-Global-Workflows-Upgrade-Proposal"
        Title = "全局工作流架构增强方案：版本锚定、分层防御与熔断协议"
        Category = "工作流与治理演进"
        Date = "2026-09-03"
    }
    "20260907_global_workflows_deprecation_and_skills_migration.md" = @{
        PageName = "2026-09-07-Global-Workflows-Deprecation-and-Skills-Migration"
        Title = "全局工作流废弃与技能架构演进更新报告"
        Category = "工作流与治理演进"
        Date = "2026-09-07"
    }
    "20260907_skills_assets_taxonomy_and_scripts_evaluation.md" = @{
        PageName = "2026-09-07-Skills-Assets-Taxonomy-and-Scripts-Evaluation"
        Title = "Skills 资产全景分布与脚本准入判定评估报告"
        Category = "技能架构与分类"
        Date = "2026-09-07"
    }
    "20260917_skills_boundary_reconciliation_and_evolution_proposal.md" = @{
        PageName = "2026-09-17-Skills-Boundary-Reconciliation-and-Evolution-Proposal"
        Title = "全局技能边界调和与架构演进方案"
        Category = "技能架构与分类"
        Date = "2026-09-17"
    }
    "20260918_gemini_directory_storage_audit_and_safe_cleanup_guide.md" = @{
        PageName = "2026-09-18-Gemini-Directory-Storage-Audit-and-Safe-Cleanup-Guide"
        Title = ".gemini 目录存储深度审计与安全清理专项调研报告"
        Category = "环境治理与存储安全"
        Date = "2026-09-18"
    }
    "20260920_css_typography_control_and_theme_scaffolding_architecture.md" = @{
        PageName = "2026-09-20-CSS-Typography-Control-and-Theme-Scaffolding-Architecture"
        Title = "前端字阶控制与主题脚手架技能架构方案"
        Category = "字阶与排版治理"
        Date = "2026-09-20"
    }
    "20260920_typography_scale_control_and_skills_boundary_specification.md" = @{
        PageName = "2026-09-20-Typography-Scale-Control-and-Skills-Boundary-Specification"
        Title = "字体大小控制与矢量排版技能边界架构规范"
        Category = "字阶与排版治理"
        Date = "2026-09-20"
    }
    "20260924_global_skills_plan_mechanism_integration_architecture.md" = @{
        PageName = "2026-09-24-Global-Skills-Plan-Mechanism-Integration-Architecture"
        Title = "全局技能集成 /plan 交互门禁机制架构方案"
        Category = "交互协议与中枢赋能"
        Date = "2026-09-24"
    }
    "20260928_global_skills_asset_convergence_and_command_integration_architecture.md" = @{
        PageName = "2026-09-28-Global-Skills-Asset-Convergence-and-Command-Integration-Architecture"
        Title = "全局技能资产打包收敛与原生指令融合架构方案"
        Category = "技能架构与分类"
        Date = "2026-09-28"
    }
    "20261008_global_skills_antifragility_and_protocol_optimization_architecture.md" = @{
        PageName = "2026-10-08-Global-Skills-Antifragility-and-Protocol-Optimization-Architecture"
        Title = "全局技能抗脆弱性与通信协议优化演进架构方案"
        Category = "交互协议与中枢赋能"
        Date = "2026-10-08"
    }
}

# Process each document
$ProcessedCount = 0
foreach ($sourceFile in (Get-ChildItem -Path $DocsRoot -Filter "*.md")) {
    $meta = $DocMap[$sourceFile.Name]
    if (-not $meta) {
        # Fallback automatic slugging
        $baseStem = [System.IO.Path]::GetFileNameWithoutExtension($sourceFile.Name)
        $meta = @{
            PageName = ($baseStem -replace "_", "-")
            Title = $baseStem
            Category = "文档归档"
            Date = (Get-Date -Format "yyyy-MM-dd")
        }
    }

    $rawContent = [System.IO.File]::ReadAllText($sourceFile.FullName, [System.Text.Encoding]::UTF8)

    # Convert Windows file:// links
    # 1. Links to config/docs/*.md -> Wiki Page
    foreach ($entry in $DocMap.GetEnumerator()) {
        $sourceName = $entry.Key
        $targetPage = $entry.Value.PageName
        
        # Match file:///.../config/docs/<sourceName>
        $patternDocs = "file:///[a-zA-Z]:/[^)\s\""]*/config/docs/$sourceName"
        $rawContent = [System.Text.RegularExpressions.Regex]::Replace($rawContent, $patternDocs, $targetPage)
        
        # Match relative config/docs/<sourceName>
        $patternRel = "(?<=[\(\s])(?:\./)?config/docs/$sourceName(?=[\)\s])"
        $rawContent = [System.Text.RegularExpressions.Regex]::Replace($rawContent, $patternRel, $targetPage)
    }

    # 2. Links to other local repo files -> GitHub Blob URLs
    # Pattern: file:///C:/Users/Reaticle/.gemini/(.*?)
    $patternRepoFile = "file:///[a-zA-Z]:/[^)\s\""]*/\.gemini/(.*?)(?=[\)\""])?"
    $evaluator = [System.Text.RegularExpressions.MatchEvaluator]{
        param($match)
        $subPath = $match.Groups[1].Value.TrimEnd(')', '"')
        $subPathClean = $subPath.Replace("\", "/")
        return "$GitHubBlobBase/$subPathClean"
    }
    $rawContent = [System.Text.RegularExpressions.Regex]::Replace($rawContent, "file:///[a-zA-Z]:/[^)\s\""]*/\.gemini/([^\)\s\""]+)", $evaluator)

    # Ensure LF line endings
    $rawContent = $rawContent.Replace("`r`n", "`n")

    $destPath = Join-Path $StagingDir "$($meta.PageName).md"
    [System.IO.File]::WriteAllText($destPath, $rawContent, [System.Text.UTF8Encoding]::new($false))
    $ProcessedCount++
    Write-Host " [Staged] $($sourceFile.Name) -> $($meta.PageName).md" -ForegroundColor Green
}

# --- Generate Home.md ---
$HomeContent = @'
# 知识库主页 (Antigravity Global Architecture Knowledge Base)

欢迎访问 **.gemini** 全局架构、技能体系与环境治理的官方技术知识库。

本项目作为个人高阶 AI 辅助工程与多智能体系统（MAS）的全局基础设施，沉淀了从全局工作流演进、技能拓扑收敛、工程中枢防御到通信协议抗脆弱性优化的全量架构方案。

---

## 架构拓扑全景 (Architecture Panorama)

```mermaid
graph TB
    subgraph CoreHub["核心工程中枢 (Core Engineering Hub)"]
        Analyzer["/analyzer<br/>系统分析与方案澄清"]
        Collector["/collector<br/>事实收集与代码盘点"]
        Researcher["/researcher<br/>外部证据与权威检索"]
        Builder["/builder<br/>终局交付与自主闭环"]
        Verifier["/verifier<br/>白盒证伪与边界防卫"]
        Reviewer["/reviewer<br/>质量门禁与反思沉淀"]
    end

    subgraph Plugins["垂直专业插件群 (Domain Plugins)"]
        CW["creative-writing<br/>深度写作与行业分析"]
        DC["devops-curator<br/>Wiki & 版本日志发布"]
        DP["document-publishing<br/>Typst & 标杆文档排版"]
        FD["frontend-design<br/>字阶控制 & SVG设计"]
        MP["media-processor<br/>音频元数据与歌词对齐"]
        SC["science<br/>生物信息与学术计算"]
    end

    subgraph Governance["底座治理体系 (Base Infrastructure & Governance)"]
        RuleGlobal["GEMINI.md / Global Rule<br/>生理字阶底线 (>=12px) & 事实分离"]
        Audit["存储审计与空间清理<br/>Brain / Logs / TempMedia"]
        WikiSync["wiki-sync.yml<br/>GitHub Wiki 自动化发布"]
    end

    CoreHub <--> Plugins
    CoreHub --> Governance
```

---

## 架构演进与技术规范专栏 (Architecture Roadmap)

### 1. 交互协议与工程中枢赋能 (Interaction Protocol & Engineering Hub)
| 制定日期 | 方案标题 | 核心突破 |
| :--- | :--- | :--- |
| 2026-10-08 | [全局技能抗脆弱性与通信协议优化演进架构方案](2026-10-08-Global-Skills-Antifragility-and-Protocol-Optimization-Architecture) | 引入“替代成本壁垒”、“交集垄断”、“主动打破局部最优”与“向上通信协议优化”，消除代理交互心智带宽磨损。 |
| 2026-09-24 | [全局技能集成 /plan 交互门禁机制架构方案](2026-09-24-Global-Skills-Plan-Mechanism-Integration-Architecture) | 确立高危操作交互式审批门禁，阻断非受控执行。 |

### 2. 技能架构与资产分类 (Skills Architecture & Convergence)
| 制定日期 | 方案标题 | 核心突破 |
| :--- | :--- | :--- |
| 2026-09-28 | [全局技能资产打包收敛与原生指令融合架构方案](2026-09-28-Global-Skills-Asset-Convergence-and-Command-Integration-Architecture) | 构建“6 大核心中枢 + 5 大垂直插件”拓扑，无缝融合 slash commands 原生指令体系。 |
| 2026-09-17 | [全局技能边界调和与架构演进方案](2026-09-17-Skills-Boundary-Reconciliation-and-Evolution-Proposal) | 解决技能重叠与职责冲突，规范能力边界划分。 |
| 2026-09-07 | [Skills 资产全景分布与脚本准入判定评估报告](2026-09-07-Skills-Assets-Taxonomy-and-Scripts-Evaluation) | 全量资产盘点，设立脚本引入硬性准入基线。 |

### 3. 工作流与治理演进 (Workflows & Lifecycle Evolution)
| 制定日期 | 方案标题 | 核心突破 |
| :--- | :--- | :--- |
| 2026-09-07 | [全局工作流废弃与技能架构演进更新报告](2026-09-07-Global-Workflows-Deprecation-and-Skills-Migration) | 全面废弃旧版静态 global_workflows，升级为动态声明式技能架构。 |
| 2026-09-03 | [全局工作流架构增强方案：版本锚定、分层防御与熔断协议](2026-09-03-Global-Workflows-Upgrade-Proposal) | 建立版本锚定防御与异常熔断机制。 |

### 4. 字阶控制与排版治理 (Typography & Frontend Governance)
| 制定日期 | 方案标题 | 核心突破 |
| :--- | :--- | :--- |
| 2026-09-20 | [字体大小控制与矢量排版技能边界架构规范](2026-09-20-Typography-Scale-Control-and-Skills-Boundary-Specification) | 确立绝对生理字阶底线（`font-size >= 12px`），禁止任何缩放或伪缩小绕过。 |
| 2026-09-20 | [前端字阶控制与主题脚手架技能架构方案](2026-09-20-CSS-Typography-Control-and-Theme-Scaffolding-Architecture) | 提供 CSS/JS 主题自动化衍生脚手架与质检钩子。 |

### 5. 环境治理与存储安全 (Storage Audit & Safety)
| 制定日期 | 方案标题 | 核心突破 |
| :--- | :--- | :--- |
| 2026-09-18 | [.gemini 目录存储深度审计与安全清理专项调研报告](2026-09-18-Gemini-Directory-Storage-Audit-and-Safe-Cleanup-Guide) | 审计 Brain、Logs 与临时存储，制定零误删安全清理标准流程。 |

---

## 自动化持续部署 (Continuous Delivery)

本项目 Wiki 依托 **wiki-curator** 架构与 GitHub Actions 实现自动化部署：
1. **源文件编辑**：在主仓库 `config/docs/` 下编写或更新 Markdown 文档。
2. **本地受控编译**：运行 `pwsh scripts/build-wiki-staging.ps1`，自动完成链接规整与暂存区构建。
3. **极速发布**：推送到 `main` 分支后，GitHub Actions 工作流将在 30 秒内无缝镜像同步至 GitHub Wiki 网页端。
'@.Replace("`r`n", "`n")

[System.IO.File]::WriteAllText((Join-Path $StagingDir "Home.md"), $HomeContent, [System.Text.UTF8Encoding]::new($false))
Write-Host " [Staged] Home.md" -ForegroundColor Green

# --- Generate _Sidebar.md ---
$SidebarContent = @'
# 导航目录 (Navigation)

- **[知识库主页](Home)**

---

### 交互协议与工程中枢
- [全局技能抗脆弱性与通信协议优化](2026-10-08-Global-Skills-Antifragility-and-Protocol-Optimization-Architecture)
- [全局技能集成 /plan 交互门禁机制](2026-09-24-Global-Skills-Plan-Mechanism-Integration-Architecture)

### 技能架构与资产分类
- [全局技能资产打包收敛与指令融合](2026-09-28-Global-Skills-Asset-Convergence-and-Command-Integration-Architecture)
- [全局技能边界调和与架构演进方案](2026-09-17-Skills-Boundary-Reconciliation-and-Evolution-Proposal)
- [Skills 资产分布与脚本准入判定](2026-09-07-Skills-Assets-Taxonomy-and-Scripts-Evaluation)

### 工作流与治理演进
- [全局工作流废弃与技能架构演进](2026-09-07-Global-Workflows-Deprecation-and-Skills-Migration)
- [全局工作流架构增强方案](2026-09-03-Global-Workflows-Upgrade-Proposal)

### 字阶控制与排版治理
- [字体大小控制与矢量排版技能边界](2026-09-20-Typography-Scale-Control-and-Skills-Boundary-Specification)
- [前端字阶控制与主题脚手架技能](2026-09-20-CSS-Typography-Control-and-Theme-Scaffolding-Architecture)

### 环境治理与存储安全
- [.gemini 目录存储审计与安全清理](2026-09-18-Gemini-Directory-Storage-Audit-and-Safe-Cleanup-Guide)

---

### 项目代码链接
- [主仓库 GitHub](https://github.com/TREYWANGCQU/.gemini)
- [核心工程中枢 (Skills)](https://github.com/TREYWANGCQU/.gemini/blob/main/config/skills)
- [插件库 (Plugins)](https://github.com/TREYWANGCQU/.gemini/blob/main/config/plugins)
'@.Replace("`r`n", "`n")

[System.IO.File]::WriteAllText((Join-Path $StagingDir "_Sidebar.md"), $SidebarContent, [System.Text.UTF8Encoding]::new($false))
Write-Host " [Staged] _Sidebar.md" -ForegroundColor Green

# --- Generate _Footer.md ---
$FooterContent = @'
---
> 💡 *本 Wiki 页面由 [wiki-curator](https://github.com/TREYWANGCQU/.gemini/blob/main/config/plugins/devops-curator/skills/wiki-curator/SKILL.md) 自动化维护构建，通过 GitHub Actions 持续部署发布。*
> **Repository**: [TREYWANGCQU/.gemini](https://github.com/TREYWANGCQU/.gemini) | **Branch**: main
'@.Replace("`r`n", "`n")

[System.IO.File]::WriteAllText((Join-Path $StagingDir "_Footer.md"), $FooterContent, [System.Text.UTF8Encoding]::new($false))
Write-Host " [Staged] _Footer.md" -ForegroundColor Green

Write-Host "`nWiki Staging 构建完成！共处理 $ProcessedCount 篇源文档，生成 Home、_Sidebar、_Footer 及全量暂存文件。" -ForegroundColor Cyan
