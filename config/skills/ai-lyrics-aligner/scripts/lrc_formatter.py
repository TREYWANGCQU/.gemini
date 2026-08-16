# scripts/lrc_formatter.py
"""
Lyrics Formatter & Serializer
Formats aligned timecodes into Standard LRC, Enhanced LRC, SRT, and DAW Marker CSV.
"""

from typing import Any, Dict, List


def format_timestamp_lrc(seconds: float) -> str:
    """Format seconds into [mm:ss.xx] standard LRC timestamp."""
    if seconds < 0:
        seconds = 0.0
    minutes = int(seconds // 60)
    remaining_secs = seconds % 60
    return f"[{minutes:02d}:{remaining_secs:05.2f}]"


def format_timestamp_srt(seconds: float) -> str:
    """Format seconds into 00:00:00,000 SRT timestamp."""
    if seconds < 0:
        seconds = 0.0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        millis = 999
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_standard_lrc(aligned_data: Dict[str, Any], metadata: Dict[str, str] = None) -> str:
    """Generate standard line-level LRC file content."""
    lines = []
    if metadata:
        for k, v in metadata.items():
            lines.append(f"[{k}:{v}]")
    
    sections = aligned_data.get("sections", [])
    for section in sections:
        tag = section.get("tag", "")
        # Add section marker if start_time available
        sec_start = section.get("start_time")
        if sec_start is not None and tag:
            lines.append(f"{format_timestamp_lrc(sec_start)} //{tag}//")

        for line_item in section.get("lines", []):
            start = line_item.get("start_time", 0.0)
            text = line_item.get("text", "")
            lines.append(f"{format_timestamp_lrc(start)}{text}")

    return "\n".join(lines)


def generate_srt(aligned_data: Dict[str, Any]) -> str:
    """Generate SubRip (.srt) subtitle content."""
    entries = []
    counter = 1
    sections = aligned_data.get("sections", [])
    
    for section in sections:
        for line_item in section.get("lines", []):
            start = line_item.get("start_time", 0.0)
            end = line_item.get("end_time", start + 3.0)
            text = line_item.get("text", "")
            if not text:
                continue
            
            entries.append(f"{counter}\n{format_timestamp_srt(start)} --> {format_timestamp_srt(end)}\n{text}\n")
            counter += 1

    return "\n".join(entries)


def generate_daw_marker_csv(aligned_data: Dict[str, Any]) -> str:
    """Generate DAW Marker CSV (compatible with Reaper, Pro Tools, Studio One)."""
    lines = ["Name,Start,Length,Color"]
    sections = aligned_data.get("sections", [])
    
    for section in sections:
        tag = section.get("tag", "Section").replace('"', '""')
        start = section.get("start_time", 0.0)
        end = section.get("end_time", start + 5.0)
        length = max(0.1, end - start)
        # Format as seconds or MM:SS:MS
        lines.append(f'"{tag}",{start:.3f},{length:.3f},#4A90E2')

        for i, line_item in enumerate(section.get("lines", [])):
            l_start = line_item.get("start_time", 0.0)
            l_end = line_item.get("end_time", l_start + 2.0)
            l_len = max(0.1, l_end - l_start)
            l_text = line_item.get("text", f"Line {i+1}").replace('"', '""')
            lines.append(f'"{l_text}",{l_start:.3f},{l_len:.3f},#7ED321')

    return "\n".join(lines)
