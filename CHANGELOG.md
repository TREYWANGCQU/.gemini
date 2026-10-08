<!-- CHANGELOG.md -->
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v2.0.1] - 2026-10-08

### Added
- **Core Hub Antifragility Upgrades (`config/skills/`)**:
  - `analyzer`: Upward communication protocol optimization; structured multiple-choice decision options with defaults; mental bandwidth conservation; graceful degradation in non-UI environments.
  - `builder`: System jitter absorption mechanism; self-healing retry limit ($\le 3$ rounds); immediate penetration channel for fatal exogenous errors.
  - `verifier`: Local optima defense; transitioned from isolated unit checks to end-to-end topological data flow and cross-module contract verification.
  - `collector`: Context moat reinforcement; explicit extraction of unwritten business constraints and glue interfaces with task-adaptive token budgeting.
- **GitHub Wiki Staging & CI/CD Pipeline**:
  - `scripts/build-wiki-staging.ps1`: Automated PowerShell compiler and staging generator for GitHub Wiki with Windows path conversion to GitHub blob URLs.
  - `.github/workflows/wiki-sync.yml`: GitHub Actions automated workflow for CI/CD synchronization from `doc/wiki_staging/` to `TREYWANGCQU/.gemini.wiki.git`.
  - `doc/wiki_staging/`: Staged documentation set including 10 architectural proposals and specifications.
- **Cross-Platform Git Attributes (`.gitattributes`)**:
  - Normalized line endings across Windows and Linux (`* text=auto eol=lf`).
- **Release Documentation**:
  - `config/docs/20261008_release_notes_v2.0.1.md`: Standardized release notes for v2.0.1.

### Fixed
- **Link Normalization**: Fixed broken Windows local absolute `file:///` paths in staged markdown docs by converting them to GitHub blob URLs and Wiki page slugs.
- **Typst Publisher Path Handling**: Fixed execution path resolution in `typst-publisher` script.

---

## [v2.0.0] - 2026-09-29

### Added
- **Antigravity 2.0 Global Architecture Convergence**:
  - Formed the 6 Core Engineering Hubs: `/analyzer`, `/collector`, `/researcher`, `/builder`, `/verifier`, `/reviewer`.
  - Integrated 5 vertical domain plugins: `creative-writing`, `devops-curator`, `document-publishing`, `frontend-design`, `media-processor` (+ official `science` plugin).
  - Integrated native slash commands (`/plan`, `/goal`, `/grill-me`, `/learn`, `/schedule`).
  - Established unified architectural specification (`20260928_global_skills_asset_convergence_and_command_integration_architecture.md`).
- **Typography Scale Governance**:
  - Enforced physiological font size floor ($\ge 12\text{px}$) across CSS and SVG assets.
