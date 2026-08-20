# scripts/audio_metadata_cli.py
"""
Audio Metadata Manager - Command Line Interface
Unified CLI for audio metadata inspection, modification, artwork/lyrics management, and CI quality gating.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Enable relative imports if executed directly
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.reader import read_metadata
from core.writer import write_metadata
from core.artwork import extract_artwork, set_artwork, remove_artwork
from core.lyrics import extract_lyrics, set_lyrics, remove_lyrics
from core.auditor import audit_metadata, AuditReport


def cmd_inspect(args: argparse.Namespace) -> int:
    try:
        meta = read_metadata(args.file)
        data = meta.to_dict()

        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print("=" * 60)
            print(f"File:     {meta.file_path}")
            print(f"Format:   {meta.format} | Duration: {meta.duration_seconds}s | Sample Rate: {meta.sample_rate}Hz | Channels: {meta.channels}")
            print("-" * 60)
            print("Tags:")
            for k, v in data["tags"].items():
                if k == "custom" and v:
                    print("  custom:")
                    for ck, cv in v.items():
                        print(f"    {ck}: {cv}")
                elif k == "lyrics" and v:
                    lines = v.split("\n")
                    preview = lines[0] if lines else ""
                    print(f"  lyrics: [{len(lines)} lines] {preview[:50]}...")
                elif v is not None:
                    print(f"  {k:15}: {v}")
            print("-" * 60)
            print("Artwork:")
            for k, v in data["artwork"].items():
                print(f"  {k:15}: {v}")
            print("=" * 60)
        return 0
    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, ensure_ascii=False, indent=2), file=sys.stderr)
        else:
            print(f"Error inspecting file: {e}", file=sys.stderr)
        return 2


def cmd_mutate(args: argparse.Namespace) -> int:
    try:
        tags: Dict[str, Any] = {}

        # Load config file if provided
        if args.config:
            cfg_path = Path(args.config).resolve()
            if not cfg_path.is_file():
                raise FileNotFoundError(f"Config file not found: {args.config}")
            with open(cfg_path, "r", encoding="utf-8") as f:
                if cfg_path.suffix.lower() in (".yaml", ".yml"):
                    try:
                        import yaml
                        cfg_data = yaml.safe_load(f)
                    except ImportError:
                        raise ImportError("PyYAML is required to load YAML configuration files.")
                else:
                    cfg_data = json.load(f)
                if "tags" in cfg_data:
                    tags.update(cfg_data["tags"])
                else:
                    tags.update(cfg_data)

        # CLI overrides
        if args.title is not None: tags["title"] = args.title
        if args.artist is not None: tags["artist"] = args.artist
        if args.album is not None: tags["album"] = args.album
        if args.album_artist is not None: tags["album_artist"] = args.album_artist
        if args.composer is not None: tags["composer"] = args.composer
        if args.lyricist is not None: tags["lyricist"] = args.lyricist
        if args.track is not None: tags["track_number"] = args.track
        if args.disc is not None: tags["disc_number"] = args.disc
        if args.date is not None: tags["date"] = args.date
        if args.genre is not None: tags["genre"] = args.genre
        if args.isrc is not None: tags["isrc"] = args.isrc
        if args.comment is not None: tags["comment"] = args.comment

        if args.custom:
            if "custom" not in tags:
                tags["custom"] = {}
            for item in args.custom:
                if "=" in item:
                    k, v = item.split("=", 1)
                    tags["custom"][k.strip()] = v.strip()

        # Execute write
        write_metadata(
            audio_path=args.file,
            tags=tags if tags else None,
            cover_image=args.set_cover,
            remove_cover_flag=args.remove_cover,
            lyrics_content_or_path=args.set_lyrics,
            remove_lyrics_flag=args.remove_lyrics,
        )

        if args.json:
            updated_meta = read_metadata(args.file)
            print(json.dumps({"success": True, "file": args.file, "metadata": updated_meta.to_dict()}, ensure_ascii=False, indent=2))
        else:
            print(f"Successfully updated metadata for: {args.file}")
        return 0
    except Exception as e:
        if args.json:
            print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False, indent=2), file=sys.stderr)
        else:
            print(f"Error mutating metadata: {e}", file=sys.stderr)
        return 2


def cmd_extract_cover(args: argparse.Namespace) -> int:
    try:
        data = extract_artwork(args.file, args.output)
        if data is None:
            if args.json:
                print(json.dumps({"success": False, "message": "No embedded cover artwork found"}, ensure_ascii=False))
            else:
                print("No embedded cover artwork found.", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps({"success": True, "output": args.output, "size_bytes": len(data)}, ensure_ascii=False))
        else:
            print(f"Extracted cover artwork to: {args.output} ({len(data)} bytes)")
        return 0
    except Exception as e:
        if args.json:
            print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False), file=sys.stderr)
        else:
            print(f"Error extracting cover: {e}", file=sys.stderr)
        return 2


def cmd_extract_lyrics(args: argparse.Namespace) -> int:
    try:
        text = extract_lyrics(args.file, args.output)
        if text is None:
            if args.json:
                print(json.dumps({"success": False, "message": "No embedded lyrics found"}, ensure_ascii=False))
            else:
                print("No embedded lyrics found.", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps({"success": True, "output": args.output, "lines": len(text.splitlines())}, ensure_ascii=False))
        else:
            print(f"Extracted lyrics to: {args.output}")
        return 0
    except Exception as e:
        if args.json:
            print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False), file=sys.stderr)
        else:
            print(f"Error extracting lyrics: {e}", file=sys.stderr)
        return 2


def cmd_audit(args: argparse.Namespace) -> int:
    req_fields: List[str] = []
    min_res = args.min_cover_res
    req_synced = args.require_synced_lyrics
    val_isrc = args.validate_isrc

    if args.schema:
        schema_file = Path(args.schema).resolve()
        if schema_file.is_file():
            with open(schema_file, "r", encoding="utf-8") as f:
                schema_data = json.load(f)
                if "require" in schema_data:
                    req_fields.extend(schema_data["require"])
                if "min_cover_res" in schema_data:
                    min_res = schema_data["min_cover_res"]
                if "require_synced_lyrics" in schema_data:
                    req_synced = schema_data["require_synced_lyrics"]
                if "validate_isrc" in schema_data:
                    val_isrc = schema_data["validate_isrc"]

    if args.require:
        req_fields.extend([f.strip() for f in args.require.split(",") if f.strip()])

    target = Path(args.target).resolve()
    audio_files: List[Path] = []
    supported_exts = {".flac", ".mp3", ".wav", ".m4a", ".aac", ".ogg"}

    if target.is_file():
        audio_files.append(target)
    elif target.is_dir():
        glob_fn = target.rglob if args.recursive else target.glob
        for p in glob_fn("*"):
            if p.suffix.lower() in supported_exts:
                audio_files.append(p)
    else:
        print(f"Target path not found: {args.target}", file=sys.stderr)
        return 2

    reports: List[AuditReport] = []
    overall_passed = True

    for af in audio_files:
        rep = audit_metadata(
            audio_path=str(af),
            required_fields=req_fields,
            min_cover_res=min_res,
            require_synced_lyrics=req_synced,
            validate_isrc_format=val_isrc,
        )
        if not rep.passed:
            overall_passed = False
        reports.append(rep)

    if args.json:
        out_dict = {
            "overall_passed": overall_passed,
            "total_files": len(reports),
            "passed_files": sum(1 for r in reports if r.passed),
            "failed_files": sum(1 for r in reports if not r.passed),
            "reports": [r.to_dict() for r in reports],
        }
        print(json.dumps(out_dict, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print(f"Audit Results ({len(reports)} files checked):")
        print("=" * 60)
        for r in reports:
            status = "[PASS]" if r.passed else "[FAIL]"
            print(f"{status} {r.file_path} ({r.format})")
            if not r.passed:
                for v in r.violations:
                    print(f"    - [{v.rule}] {v.field}: {v.message}")
        print("-" * 60)
        print(f"Summary: {sum(1 for r in reports if r.passed)}/{len(reports)} passed.")

    return 0 if overall_passed else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audio Metadata Manager CLI - Universal audio tag, artwork, lyrics editor and CI auditor"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Inspect
    p_inspect = subparsers.add_parser("inspect", help="Inspect audio metadata, artwork, and acoustic info")
    p_inspect.add_argument("file", help="Path to audio file (.mp3, .flac, .wav, .m4a, .ogg)")
    p_inspect.add_argument("--json", action="store_true", help="Output standard JSON format")
    p_inspect.set_defaults(func=cmd_inspect)

    # 2. Mutate
    p_mutate = subparsers.add_parser("mutate", help="Mutate tags, inject cover art, or embed lyrics")
    p_mutate.add_argument("file", help="Path to audio file")
    p_mutate.add_argument("--title", help="Song title")
    p_mutate.add_argument("--artist", help="Artist name")
    p_mutate.add_argument("--album", help="Album name")
    p_mutate.add_argument("--album-artist", help="Album artist / Band")
    p_mutate.add_argument("--composer", help="Composer name")
    p_mutate.add_argument("--lyricist", help="Lyricist name")
    p_mutate.add_argument("--track", help="Track number (e.g. 1 or 1/10)")
    p_mutate.add_argument("--disc", help="Disc number (e.g. 1/1)")
    p_mutate.add_argument("--date", help="Release date / Year")
    p_mutate.add_argument("--genre", help="Music genre")
    p_mutate.add_argument("--isrc", help="ISRC code")
    p_mutate.add_argument("--comment", help="Comment / Prompt spec metadata")
    p_mutate.add_argument("--custom", nargs="*", help="Custom tags in KEY=VALUE format")
    p_mutate.add_argument("--set-cover", help="Path to image file to embed as cover")
    p_mutate.add_argument("--remove-cover", action="store_true", help="Remove embedded cover art")
    p_mutate.add_argument("--set-lyrics", help="Path to .lrc/.txt file or raw lyrics string to embed")
    p_mutate.add_argument("--remove-lyrics", action="store_true", help="Remove embedded lyrics")
    p_mutate.add_argument("--config", help="Path to JSON or YAML metadata config file")
    p_mutate.add_argument("--json", action="store_true", help="Output JSON result")
    p_mutate.set_defaults(func=cmd_mutate)

    # 3. Extract Cover
    p_cover = subparsers.add_parser("extract-cover", help="Extract embedded cover artwork")
    p_cover.add_argument("file", help="Path to audio file")
    p_cover.add_argument("output", help="Output image file path (e.g. cover.jpg)")
    p_cover.add_argument("--json", action="store_true", help="Output JSON result")
    p_cover.set_defaults(func=cmd_extract_cover)

    # 4. Extract Lyrics
    p_lyrics = subparsers.add_parser("extract-lyrics", help="Extract embedded lyrics")
    p_lyrics.add_argument("file", help="Path to audio file")
    p_lyrics.add_argument("output", help="Output lyrics file path (e.g. song.lrc)")
    p_lyrics.add_argument("--json", action="store_true", help="Output JSON result")
    p_lyrics.set_defaults(func=cmd_extract_lyrics)

    # 5. Audit
    p_audit = subparsers.add_parser("audit", help="Audit metadata compliance for CI/CD gates")
    p_audit.add_argument("target", help="Audio file or directory path to audit")
    p_audit.add_argument("--require", help="Comma-separated required fields (e.g. 'title,artist,artwork,lyrics')")
    p_audit.add_argument("--min-cover-res", help="Minimum cover resolution (e.g. 500x500)")
    p_audit.add_argument("--require-synced-lyrics", action="store_true", help="Require synced [mm:ss.xx] timestamps in lyrics")
    p_audit.add_argument("--validate-isrc", action="store_true", help="Validate ISRC string length & format")
    p_audit.add_argument("--schema", help="Path to JSON rules schema file")
    p_audit.add_argument("--recursive", "-r", action="store_true", help="Search directories recursively")
    p_audit.add_argument("--json", action="store_true", help="Output standard JSON report")
    p_audit.set_defaults(func=cmd_audit)

    args = parser.parse_args()
    code = args.func(args)
    sys.exit(code)


if __name__ == "__main__":
    main()
