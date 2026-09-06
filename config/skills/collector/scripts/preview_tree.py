# scripts/preview_tree.py
# C:\Users\Reaticle\.gemini\config\skills\collector\scripts\preview_tree.py
"""
Lightweight Token-Efficient Directory Structure Preview & SSOT Asset Scanner.
Zero external dependencies (Python 3.8+ standard library only).
Engineered for /collector to enforce Preview-First context gathering and prevent LLM context pollution.
"""

import os
import sys
import argparse
import json
import fnmatch
from pathlib import Path

# High-noise directories and patterns to prune by default
DEFAULT_IGNORED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "env",
    "target",
    "dist",
    "build",
    "out",
    ".next",
    ".nuxt",
    ".turbo",
    ".gradle",
    "bin",
    "obj",
    ".idea",
    ".vscode",
    ".gemini",
    "vendor",
    "coverage",
    ".tox",
    ".cache",
}

DEFAULT_IGNORED_FILES = {
    ".DS_Store",
    "Thumbs.db",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.class",
    "*.exe",
    "*.dll",
    "*.so",
    "*.dylib",
    "*.swp",
    "*.swo",
}

# Key assets and single-source-of-truth (SSOT) configuration indicators
KEY_ASSET_PATTERNS = {
    "MANIFEST": [
        "package.json",
        "Cargo.toml",
        "pyproject.toml",
        "requirements.txt",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "Gemfile",
        "composer.json",
        "Pipfile",
        "setup.py",
        "setup.cfg",
    ],
    "CONFIG": [
        "tsconfig.json",
        "*config*.json",
        "settings.json",
        "docker-compose.yml",
        "docker-compose.yaml",
        "Dockerfile",
        "Makefile",
        ".env.example",
        "openapi.yaml",
        "openapi.json",
        "vite.config.*",
        "next.config.*",
        "webpack.config.*",
        "tailwind.config.*",
        "turbo.json",
        ".eslintrc*",
        "ruff.toml",
    ],
    "DOC_SPEC": [
        "README.md",
        "ARCHITECTURE.md",
        "SKILL.md",
        "GEMINI.md",
        "AGENTS.md",
        "ADR*.md",
    ],
}


def load_gitignore_rules(root_dir):
    """Load ignore patterns from root .gitignore if available."""
    patterns = []
    gitignore_path = os.path.join(root_dir, ".gitignore")
    if os.path.isfile(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Normalize trailing slash
                        if line.endswith("/"):
                            line = line[:-1]
                        patterns.append(line)
        except OSError:
            pass
    return patterns


def is_ignored(name, is_dir, custom_patterns=None, no_ignore=False, include_hidden=False):
    """Determine if a file or directory should be ignored."""
    if no_ignore:
        return False

    # Skip hidden files/dirs unless include_hidden is set
    if not include_hidden and name.startswith(".") and name not in {".", ".."}:
        # Keep basic essential dotfiles like .env.example, .gitignore
        if not (name == ".gitignore" or name.startswith(".env")):
            return True

    if is_dir and name in DEFAULT_IGNORED_DIRS:
        return True

    for pattern in DEFAULT_IGNORED_FILES:
        if fnmatch.fnmatch(name, pattern):
            return True

    if custom_patterns:
        for pat in custom_patterns:
            if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(f"/{name}", pat):
                return True

    return False


def classify_key_asset(name):
    """Classify if file is a key manifest, config, or spec."""
    for category, patterns in KEY_ASSET_PATTERNS.items():
        for pat in patterns:
            if fnmatch.fnmatch(name, pat):
                return category
    return None


def scan_tree(root_dir, max_depth=3, max_files_per_dir=20, max_total_entries=150,
              include_hidden=False, no_ignore=False):
    """Scan directory hierarchy and collect structured nodes and stats."""
    root_path = os.path.abspath(root_dir)
    gitignore_patterns = load_gitignore_rules(root_path) if not no_ignore else []

    stats = {
        "root_path": root_path.replace("\\", "/"),
        "total_dirs_scanned": 0,
        "total_files_scanned": 0,
        "pruned_dirs_count": 0,
        "key_assets": [],
        "budget_exceeded": False,
        "total_nodes_generated": 0,
    }

    def walk_dir(current_dir, current_depth):
        if current_depth > max_depth:
            return []

        try:
            entries = os.scandir(current_dir)
        except (PermissionError, OSError):
            return []

        dirs = []
        files = []

        with entries:
            for entry in entries:
                name = entry.name
                try:
                    is_directory = entry.is_dir(follow_symlinks=False)
                except OSError:
                    continue

                if is_ignored(name, is_directory, gitignore_patterns, no_ignore, include_hidden):
                    if is_directory:
                        stats["pruned_dirs_count"] += 1
                    continue

                if is_directory:
                    dirs.append(entry)
                else:
                    files.append(entry)

        # Sort alphabetically
        dirs.sort(key=lambda e: e.name.lower())
        files.sort(key=lambda e: e.name.lower())

        stats["total_dirs_scanned"] += len(dirs)
        stats["total_files_scanned"] += len(files)

        dir_nodes = []

        # Process directories
        for d in dirs:
            if stats["total_nodes_generated"] >= max_total_entries:
                stats["budget_exceeded"] = True
                break

            stats["total_nodes_generated"] += 1
            children = walk_dir(d.path, current_depth + 1)
            dir_nodes.append({
                "name": d.name,
                "type": "directory",
                "rel_path": os.path.relpath(d.path, root_path).replace("\\", "/"),
                "children": children,
            })

        # Process files
        file_nodes = []
        truncated_files = 0
        if len(files) > max_files_per_dir:
            truncated_files = len(files) - max_files_per_dir
            displayed_files = files[:max_files_per_dir]
        else:
            displayed_files = files

        for f in displayed_files:
            if stats["total_nodes_generated"] >= max_total_entries:
                stats["budget_exceeded"] = True
                break

            stats["total_nodes_generated"] += 1
            rel_file_path = os.path.relpath(f.path, root_path).replace("\\", "/")
            asset_type = classify_key_asset(f.name)
            if asset_type:
                stats["key_assets"].append({
                    "name": f.name,
                    "rel_path": rel_file_path,
                    "type": asset_type,
                })

            try:
                size_bytes = f.stat().st_size
            except OSError:
                size_bytes = 0

            file_nodes.append({
                "name": f.name,
                "type": "file",
                "rel_path": rel_file_path,
                "size_bytes": size_bytes,
                "asset_tag": asset_type,
            })

        if truncated_files > 0:
            file_nodes.append({
                "name": f"... (+{truncated_files} more files)",
                "type": "truncated_notice",
                "rel_path": "",
            })

        return dir_nodes + file_nodes

    root_name = os.path.basename(root_path) or root_path
    tree_data = {
        "name": root_name,
        "type": "directory",
        "rel_path": ".",
        "children": walk_dir(root_path, 1),
    }

    return tree_data, stats


def format_text_tree(tree_data, stats, use_ascii=False):
    """Format tree nodes into visual text output with tree glyphs."""
    lines = []
    lines.append(f"📁 {tree_data['name']}/")

    branch = "|-- " if use_ascii else "├── "
    last_branch = "\\-- " if use_ascii else "└── "
    vertical = "|   " if use_ascii else "│   "
    space = "    "

    def render_children(children, prefix=""):
        count = len(children)
        for i, node in enumerate(children):
            is_last = (i == count - 1)
            current_prefix = prefix + (last_branch if is_last else branch)
            next_prefix = prefix + (space if is_last else vertical)

            node_type = node.get("type")
            name = node.get("name")

            if node_type == "directory":
                lines.append(f"{current_prefix}📁 {name}/")
                if "children" in node and node["children"]:
                    render_children(node["children"], next_prefix)
            elif node_type == "truncated_notice":
                lines.append(f"{current_prefix}⚠️  {name}")
            else:
                tag = f" [{node['asset_tag']}]" if node.get("asset_tag") else ""
                lines.append(f"{current_prefix}📄 {name}{tag}")

    if tree_data.get("children"):
        render_children(tree_data["children"])

    if stats.get("budget_exceeded"):
        lines.append("")
        lines.append("⚠️  [TOKEN_BUDGET_EXCEEDED]: Directory tree truncated to preserve token efficiency.")

    # Summary section
    lines.append("")
    lines.append("=" * 60)
    lines.append("📊 DIRECTORY SCAN SUMMARY (/collector SSOT BASELINE)")
    lines.append("=" * 60)
    lines.append(f"- Root Path: {stats['root_path']}")
    lines.append(f"- Dirs Scanned: {stats['total_dirs_scanned']} | Files Scanned: {stats['total_files_scanned']}")
    lines.append(f"- Pruned Dirs (Noise/Ignored): {stats['pruned_dirs_count']}")
    lines.append(f"- Key Assets / SSOT Baselines Discovered: {len(stats['key_assets'])}")

    if stats["key_assets"]:
        lines.append("")
        lines.append("🔑 Key Assets Found:")
        for asset in stats["key_assets"]:
            lines.append(f"  - [{asset['type']}] {asset['rel_path']}")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Preview-First Lightweight Directory Tree & SSOT Scanner for /collector"
    )
    parser.add_argument("path", nargs="?", default=".", help="Target directory to scan (default: current directory)")
    parser.add_argument("-d", "--max-depth", type=int, default=3, help="Maximum traversal depth (default: 3)")
    parser.add_argument("-m", "--max-files", type=int, default=20, help="Max files displayed per directory before truncation (default: 20)")
    parser.add_argument("-t", "--max-total", type=int, default=150, help="Max total tree entries before token-budget cutoff (default: 150)")
    parser.add_argument("--all", action="store_true", help="Include hidden dotfiles/dirs")
    parser.add_argument("--no-ignore", action="store_true", help="Do not prune standard ignored directories like .git or node_modules")
    parser.add_argument("--ascii", action="store_true", help="Use ASCII characters instead of UTF-8 box characters")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--summary-only", action="store_true", help="Only output statistics and key assets without tree")

    args = parser.parse_args()

    target_dir = os.path.abspath(args.path)
    if not os.path.isdir(target_dir):
        sys.stderr.write(f"Error: Target directory does not exist: {target_dir}\n")
        sys.exit(1)

    tree_data, stats = scan_tree(
        root_dir=target_dir,
        max_depth=args.max_depth,
        max_files_per_dir=args.max_files,
        max_total_entries=args.max_total,
        include_hidden=args.all,
        no_ignore=args.no_ignore,
    )

    if args.json:
        result = {
            "statistics": stats,
            "tree": tree_data if not args.summary_only else None,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.summary_only:
        print("=" * 60)
        print("📊 DIRECTORY SCAN SUMMARY (/collector SSOT BASELINE)")
        print("=" * 60)
        print(f"- Root Path: {stats['root_path']}")
        print(f"- Dirs Scanned: {stats['total_dirs_scanned']} | Files Scanned: {stats['total_files_scanned']}")
        print(f"- Pruned Dirs: {stats['pruned_dirs_count']}")
        print(f"- Key Assets Discovered: {len(stats['key_assets'])}")
        if stats["key_assets"]:
            print("")
            print("🔑 Key Assets Found:")
            for asset in stats["key_assets"]:
                print(f"  - [{asset['type']}] {asset['rel_path']}")
        print("=" * 60)
    else:
        output_text = format_text_tree(tree_data, stats, use_ascii=args.ascii)
        print(output_text)


if __name__ == "__main__":
    main()
