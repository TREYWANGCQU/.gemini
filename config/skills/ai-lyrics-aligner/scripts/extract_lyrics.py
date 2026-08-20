# scripts/extract_lyrics.py
"""
AI Music Prompt Specification Lyrics Extractor
Extracts structured sections and sanitized lyrics from prompt specification markdown.
"""

import argparse
import json
import os
import re
from typing import Any, Dict, List


def extract_lyrics_from_markdown(content: str) -> Dict[str, Any]:
    # Locate lyrics code blocks or lyrics section
    code_blocks = re.findall(r'```(?:text|lyrics)?\s*\n(.*?)\n```', content, re.DOTALL)
    lyrics_block = ""
    for block in code_blocks:
        if re.search(r'\[(Intro|Verse|Chorus|Pre-Chorus|Bridge|Outro)', block, re.IGNORECASE):
            lyrics_block = block
            break
            
    if not lyrics_block:
        # Fallback to whole content if no code block matches
        lyrics_block = content

    lines = lyrics_block.splitlines()
    sections: List[Dict[str, Any]] = []
    current_section = {
        "tag": "Uncategorized",
        "type": "General",
        "description": "",
        "lines": [],
        "cues": []
    }

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # Ignore meta header lines or spec structure title
        if line.startswith("#") or ":" in line and not line.startswith("[") and any(k in line.lower() for k in ["style", "vocal", "instrumentation"]):
            continue

        # Check section header: e.g. [Verse 1], [Bridge - Melodic Rap], [Chorus], [Bridge: Funky breakdown...]
        section_match = re.match(r'^\[([^\]]+)\]$', line)
        if section_match:
            tag = section_match.group(1).strip()
            if "structure" in tag.lower() or "allocation" in tag.lower():
                continue
            
            # Check if tag is purely an instrumental/arrangement cue (e.g. [Delicate fingerstyle...])
            is_instrumental_cue = any(k in tag.lower() for k in [
                "guitar", "flute", "piano", "ambience", "breeze", "fade", "fades out", 
                "drum", "synth", "strings", "solo", "instrumental", "beat"
            ]) and not any(k in tag.lower() for k in [
                "verse", "chorus", "bridge", "intro", "outro", "spoken", "whisper", 
                "recitation", "opera", "vocal", "rap", "hook", "pre-chorus", "climax", "end"
            ])

            if is_instrumental_cue:
                current_section["cues"].append(tag)
                continue

            if current_section["lines"] or current_section["cues"]:
                sections.append(current_section)
            sec_type = "Verse"
            if "chorus" in tag.lower():
                sec_type = "Chorus"
            elif "pre-chorus" in tag.lower():
                sec_type = "Pre-Chorus"
            elif "bridge" in tag.lower() or "rap" in tag.lower():
                sec_type = "Bridge"
            elif "intro" in tag.lower():
                sec_type = "Intro"
            elif "outro" in tag.lower() or "end" in tag.lower():
                sec_type = "Outro"

            current_section = {
                "tag": tag,
                "type": sec_type,
                "description": "",
                "lines": [],
                "cues": []
            }
            continue

        # Check performance cue or parenthetical instruction: e.g. (Smooth Fender Rhodes chords...)
        cue_match = re.match(r'^\((.*?)\)$', line)
        if cue_match:
            cue_text = cue_match.group(1).strip()
            # If cue contains sung text in quotes like: (Soft vocal ad-libs: "Mmm... let the night settle in... yeah")
            quoted_sung = re.findall(r'["“](.*?)["”]', cue_text)
            if quoted_sung:
                for s in quoted_sung:
                    current_section["lines"].append({
                        "text": s.strip(),
                        "is_adlib": True,
                        "raw": line
                    })
            else:
                current_section["cues"].append(cue_text)
            continue

        # Regular lyric line
        current_section["lines"].append({
            "text": line,
            "is_adlib": False,
            "raw": raw_line
        })

    if current_section["lines"] or current_section["cues"]:
        sections.append(current_section)

    # If structured sections exist, drop Uncategorized preamble
    structured_sections = [s for s in sections if s["tag"] != "Uncategorized"]
    if structured_sections:
        sections = structured_sections

    return {
        "total_sections": len(sections),
        "total_lyric_lines": sum(len(s["lines"]) for s in sections),
        "sections": sections
    }


def main():
    parser = argparse.ArgumentParser(description="Extract lyrics from AI prompt spec markdown.")
    parser.add_argument("--input", required=True, help="Path to prompt markdown file")
    parser.add_argument("--output", required=False, help="Path to output json file")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        raise FileNotFoundError(f"Input file not found: {args.input}")

    with open(args.input, "r", encoding="utf-8") as f:
        content = f.read()

    result = extract_lyrics_from_markdown(content)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Extracted {result['total_lyric_lines']} lines across {result['total_sections']} sections -> {args.output}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
