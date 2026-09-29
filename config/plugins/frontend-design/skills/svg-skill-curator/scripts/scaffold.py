# config/plugins/frontend-design/skills/svg-skill-curator/scripts/scaffold.py
#!/usr/bin/env python3
"""
SVG Skill Curator Automation Engine
Handles scaffolding, auditing, and synchronizing project-local SVG skills.
"""

import os
import sys
import shutil
import argparse
import json
import re
from typing import List, Dict, Optional

CURATOR_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(CURATOR_DIR, "templates")
GLOBAL_VALIDATOR_PATH = os.path.abspath(
    os.path.join(CURATOR_DIR, "..", "svg-designer", "scripts", "validate_svg.py")
)


def ensure_workspace_dir(workspace_root: str, relative_path: str) -> str:
    full_path = os.path.join(workspace_root, relative_path)
    os.makedirs(full_path, exist_ok=True)
    return full_path


def cmd_scaffold(args):
    workspace = os.path.abspath(args.workspace or os.getcwd())
    skill_name = args.name.strip()

    if not re.match(r'^[a-z0-9-]+$', skill_name):
        print(f"ERROR: Skill name '{skill_name}' must match regex ^[a-z0-9-]+$", file=sys.stderr)
        sys.exit(1)

    if not skill_name.endswith("-svg-generator"):
        skill_name = f"{skill_name}-svg-generator"

    target_skill_dir = os.path.join(workspace, ".agents", "skills", skill_name)
    os.makedirs(target_skill_dir, exist_ok=True)
    templates_target_dir = os.path.join(target_skill_dir, "templates")
    scripts_target_dir = os.path.join(target_skill_dir, "scripts")
    os.makedirs(templates_target_dir, exist_ok=True)
    os.makedirs(scripts_target_dir, exist_ok=True)

    print(f"[*] Initializing local SVG skill: {skill_name}")
    print(f"    Target directory: {target_skill_dir}")

    # 1. Generate SKILL.md from local-SKILL.md template
    local_skill_tmpl_path = os.path.join(TEMPLATES_DIR, "local-SKILL.md")
    if os.path.exists(local_skill_tmpl_path):
        with open(local_skill_tmpl_path, "r", encoding="utf-8") as f:
            content = f.read()
        formatted_skill_md = content.replace("{PROJECT_NAME}", skill_name).replace(
            "{PROJECT_TITLE}", skill_name.replace("-", " ").title()
        )
        dest_skill_md = os.path.join(target_skill_dir, "SKILL.md")
        with open(dest_skill_md, "w", encoding="utf-8") as f:
            f.write(formatted_skill_md)
        print("    [+] Created SKILL.md")

    # 2. Generate design-tokens.yaml (Preserving if exists)
    tokens_target_path = os.path.join(target_skill_dir, "design-tokens.yaml")
    tokens_tmpl_path = os.path.join(TEMPLATES_DIR, "design-tokens.yaml")
    if os.path.exists(tokens_target_path) and not args.force:
        print("    [!] design-tokens.yaml already exists. Skipping to preserve custom tokens.")
    elif os.path.exists(tokens_tmpl_path):
        with open(tokens_tmpl_path, "r", encoding="utf-8") as f:
            t_content = f.read()
        # Apply theme / aspect ratio customisation
        if args.aspect_ratio:
            t_content = re.sub(r'aspectRatio:\s*"[^"]+"', f'aspectRatio: "{args.aspect_ratio}"', t_content)
        if getattr(args, 'theme', 'dark') == 'light':
            t_content = t_content.replace('name: default-project-theme', 'name: default-project-theme-light')
            t_content = t_content.replace('bgBase: "#0f172a"', 'bgBase: "#f8fafc"')
            t_content = t_content.replace('bgCard: "#1e293b"', 'bgCard: "#ffffff"')
            t_content = t_content.replace('borderCard: "#334155"', 'borderCard: "#e2e8f0"')
            t_content = t_content.replace('textMain: "#f8fafc"', 'textMain: "#0f172a"')
            t_content = t_content.replace('textSecondary: "#94a3b8"', 'textSecondary: "#64748b"')
        with open(tokens_target_path, "w", encoding="utf-8") as f:
            f.write(t_content)
        print("    [+] Created design-tokens.yaml")

    # 3. Copy SVG templates
    if os.path.exists(TEMPLATES_DIR):
        for tmpl_file in os.listdir(TEMPLATES_DIR):
            if tmpl_file.endswith(".svg"):
                shutil.copy2(
                    os.path.join(TEMPLATES_DIR, tmpl_file),
                    os.path.join(templates_target_dir, tmpl_file)
                )
                print(f"    [+] Created templates/{tmpl_file}")

    # 4. Copy schema
    schema_tmpl_path = os.path.join(TEMPLATES_DIR, "design-tokens.schema.json")
    if os.path.exists(schema_tmpl_path):
        shutil.copy2(schema_tmpl_path, os.path.join(target_skill_dir, "design-tokens.schema.json"))
        print("    [+] Created design-tokens.schema.json")

    # 5. Install self-contained validate.py
    dest_validate_py = os.path.join(scripts_target_dir, "validate.py")
    if os.path.exists(GLOBAL_VALIDATOR_PATH):
        shutil.copy2(GLOBAL_VALIDATOR_PATH, dest_validate_py)
        print("    [+] Installed self-contained scripts/validate.py")
    else:
        with open(dest_validate_py, "w", encoding="utf-8") as f:
            f.write('''#!/usr/bin/env python3
import sys, re, xml.etree.ElementTree as ET
try:
    tree = ET.parse(sys.argv[1])
    for elem in tree.iter():
        tag = elem.tag.split('}')[-1]
        if tag in ('text', 'tspan'):
            fs = elem.attrib.get('font-size', '16')
            m = re.match(r'(\\d+)', fs)
            if m and float(m.group(1)) < 12.0:
                print(f"VALIDATION FAILED: <{tag}> font-size {fs} < 12px", file=sys.stderr)
                sys.exit(1)
    print("VALIDATION SUCCESS: All fonts >= 12px.")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
''')
        print("    [+] Created standalone fallback scripts/validate.py")

    print(f"\n[SUCCESS] Local SVG skill '{skill_name}' scaffolded successfully.")
    print(f"          Ready for use at: .agents/skills/{skill_name}/")


def cmd_audit(args):
    workspace = os.path.abspath(args.workspace or os.getcwd())
    skills_root = os.path.join(workspace, ".agents", "skills")

    print(f"[*] Scanning workspace for SVG skills in: {skills_root}")
    if not os.path.exists(skills_root):
        print("    No .agents/skills directory found in workspace.")
        return

    found_skills = []
    for entry in os.listdir(skills_root):
        full_p = os.path.join(skills_root, entry)
        if os.path.isdir(full_p) and ("svg" in entry or "diagram" in entry):
            found_skills.append(entry)

    if not found_skills:
        print("    No project-local SVG skills identified.")
        return

    print(f"    Found {len(found_skills)} local SVG skill(s): {', '.join(found_skills)}\n")

    drift_count = 0
    for s_name in found_skills:
        s_dir = os.path.join(skills_root, s_name)
        print(f"=== Auditing Skill: {s_name} ===")

        # Check 1: SKILL.md
        skill_md = os.path.join(s_dir, "SKILL.md")
        if not os.path.exists(skill_md):
            print("  [FAIL] Missing SKILL.md")
            drift_count += 1
        else:
            with open(skill_md, "r", encoding="utf-8") as f:
                c = f.read()
            if "12px" not in c:
                print("  [WARN] SKILL.md does not explicitly reference the 12px font floor.")
                drift_count += 1
            else:
                print("  [PASS] SKILL.md references 12px typography floor.")

        # Check 2: design-tokens.yaml (scoped to typography section)
        tokens_yaml = os.path.join(s_dir, "design-tokens.yaml")
        if not os.path.exists(tokens_yaml):
            print("  [FAIL] Missing design-tokens.yaml")
            drift_count += 1
        else:
            with open(tokens_yaml, "r", encoding="utf-8") as f:
                tc = f.read()
            # Search for sub-12px specifically in typography section
            typo_match = re.search(r'typography:\s*(.*?)(?=\n[a-zA-Z0-9_-]+:|\Z)', tc, re.DOTALL)
            typo_block = typo_match.group(1) if typo_match else tc
            m_small = re.findall(r'(\b[1-9]|1[0-1])px\b', typo_block)
            if m_small:
                print(f"  [CRITICAL] design-tokens.yaml contains sub-12px typography scale values: {set(m_small)}")
                drift_count += 1
            else:
                print("  [PASS] design-tokens.yaml respects font-size >= 12px.")

        # Check 3: scripts/validate.py
        val_py = os.path.join(s_dir, "scripts", "validate.py")
        if not os.path.exists(val_py):
            print("  [FAIL] Missing scripts/validate.py quality gate.")
            drift_count += 1
        else:
            print("  [PASS] scripts/validate.py is present.")

        print()

    if drift_count == 0:
        print("[AUDIT SUCCESS] All local SVG skills comply with global baseline standards.")
    else:
        print(f"[AUDIT WARNING] Detected {drift_count} configuration/drift issue(s). Run 'sync' to align engines.")


def cmd_sync(args):
    workspace = os.path.abspath(args.workspace or os.getcwd())
    skills_root = os.path.join(workspace, ".agents", "skills")

    if not os.path.exists(skills_root):
        print("    No .agents/skills directory found.")
        return

    targets = [args.name] if args.name else os.listdir(skills_root)

    for entry in targets:
        s_dir = os.path.join(skills_root, entry)
        if os.path.isdir(s_dir) and ("svg" in entry or "diagram" in entry):
            print(f"[*] Synchronizing skill: {entry}")
            scripts_dir = os.path.join(s_dir, "scripts")
            os.makedirs(scripts_dir, exist_ok=True)
            dest_val = os.path.join(scripts_dir, "validate.py")

            if os.path.exists(GLOBAL_VALIDATOR_PATH):
                shutil.copy2(GLOBAL_VALIDATOR_PATH, dest_val)
                print("    [+] Updated scripts/validate.py to latest global validator.")

            # Update schema
            schema_tmpl = os.path.join(TEMPLATES_DIR, "design-tokens.schema.json")
            if os.path.exists(schema_tmpl):
                shutil.copy2(schema_tmpl, os.path.join(s_dir, "design-tokens.schema.json"))
                print("    [+] Updated design-tokens.schema.json.")

            # Update templates
            templates_target_dir = os.path.join(s_dir, "templates")
            os.makedirs(templates_target_dir, exist_ok=True)
            if os.path.exists(TEMPLATES_DIR):
                for tmpl_file in os.listdir(TEMPLATES_DIR):
                    if tmpl_file.endswith(".svg"):
                        shutil.copy2(
                            os.path.join(TEMPLATES_DIR, tmpl_file),
                            os.path.join(templates_target_dir, tmpl_file)
                        )
                        print(f"    [+] Synchronized templates/{tmpl_file}.")

            # Audit SKILL.md baseline reference
            skill_md_path = os.path.join(s_dir, "SKILL.md")
            if os.path.exists(skill_md_path):
                with open(skill_md_path, "r", encoding="utf-8") as f:
                    sk_content = f.read()
                if "12px" not in sk_content:
                    print(f"    [WARN] {entry}/SKILL.md is missing 12px floor reference.")

            print(f"    [LOCKED] Preserved existing design-tokens.yaml (safe 3-way boundary).")


def main():
    parser = argparse.ArgumentParser(description="SVG Skill Curator Management CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # scaffold
    p_scaffold = subparsers.add_parser("scaffold", help="Scaffold a new project-local SVG skill")
    p_scaffold.add_argument("--name", required=True, help="Name of the skill (e.g. project-arch)")
    p_scaffold.add_argument("--aspect-ratio", default="16:9", choices=["16:9", "4:3", "1:1", "21:9"])
    p_scaffold.add_argument("--theme", default="dark", choices=["dark", "light"])
    p_scaffold.add_argument("--workspace", help="Workspace root directory (defaults to current dir)")
    p_scaffold.add_argument("--force", action="store_true", help="Force overwrite existing files including design-tokens.yaml")

    # audit
    p_audit = subparsers.add_parser("audit", help="Audit local SVG skills for baseline drift")
    p_audit.add_argument("--workspace", help="Workspace root directory")

    # sync
    p_sync = subparsers.add_parser("sync", help="Synchronize local skill validators and schemas")
    p_sync.add_argument("--name", help="Specific skill name to sync (or all if omitted)")
    p_sync.add_argument("--workspace", help="Workspace root directory")

    args = parser.parse_args()

    if args.subcommand == "scaffold":
        cmd_scaffold(args)
    elif args.subcommand == "audit":
        cmd_audit(args)
    elif args.subcommand == "sync":
        cmd_sync(args)


if __name__ == "__main__":
    main()
