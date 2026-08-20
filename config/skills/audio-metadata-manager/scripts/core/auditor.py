# scripts/core/auditor.py
"""
CI Rule Auditor & Quality Gate Engine
Inspects audio files against metadata requirements, cover art constraints, and synced lyrics rules.
"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

from .reader import read_metadata, UniversalAudioMetadata
from .lyrics import is_synced_lyrics

ISRC_PATTERN = re.compile(r"^[A-Z]{2}-?[A-Z0-9]{3}-?\d{2}-?\d{5}$", re.IGNORECASE)


@dataclass
class AuditViolation:
    rule: str
    field: str
    message: str
    severity: str = "ERROR"  # ERROR or WARNING


@dataclass
class AuditReport:
    file_path: str
    format: str
    passed: bool
    violations: List[AuditViolation] = field(default_factory=list)
    metadata_summary: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "format": self.format,
            "passed": self.passed,
            "violations": [asdict(v) for v in self.violations],
            "metadata_summary": self.metadata_summary,
        }


def audit_metadata(
    audio_path: str,
    required_fields: Optional[List[str]] = None,
    min_cover_res: Optional[str] = None,
    max_cover_size_bytes: int = 10 * 1024 * 1024,  # 10MB
    require_synced_lyrics: bool = False,
    validate_isrc_format: bool = False,
    custom_rules: Optional[Dict[str, Any]] = None,
) -> AuditReport:
    """
    Audits an audio file against a set of compliance rules.
    """
    path = Path(audio_path).resolve()
    if not path.is_file():
        return AuditReport(
            file_path=str(path),
            format="UNKNOWN",
            passed=False,
            violations=[AuditViolation(rule="file_exists", field="file_path", message=f"File not found: {audio_path}")],
        )

    meta = read_metadata(str(path))
    violations: List[AuditViolation] = []

    req_fields = set(f.strip().lower() for f in (required_fields or []))

    # 1. Check basic text tag requirements
    tags_dict = meta.tags.__dict__
    for req in req_fields:
        if req == "artwork":
            if not meta.artwork.exists:
                violations.append(
                    AuditViolation(
                        rule="required_field",
                        field="artwork",
                        message="Missing embedded cover artwork.",
                    )
                )
        elif req == "lyrics":
            if not meta.tags.lyrics or not meta.tags.lyrics.strip():
                violations.append(
                    AuditViolation(
                        rule="required_field",
                        field="lyrics",
                        message="Missing embedded lyrics.",
                    )
                )
        else:
            val = tags_dict.get(req)
            if val is None or (isinstance(val, str) and not val.strip()):
                violations.append(
                    AuditViolation(
                        rule="required_field",
                        field=req,
                        message=f"Required metadata tag '{req}' is missing or empty.",
                    )
                )

    # 2. Check Cover Artwork Constraints
    if meta.artwork.exists:
        if min_cover_res:
            try:
                min_w, min_h = map(int, min_cover_res.lower().split("x"))
                w = meta.artwork.width or 0
                h = meta.artwork.height or 0
                if w < min_w or h < min_h:
                    violations.append(
                        AuditViolation(
                            rule="min_cover_res",
                            field="artwork.resolution",
                            message=f"Cover resolution {w}x{h} is lower than required {min_w}x{min_h}.",
                        )
                    )
            except Exception:
                pass

        if meta.artwork.size_bytes and meta.artwork.size_bytes > max_cover_size_bytes:
            violations.append(
                AuditViolation(
                    rule="max_cover_size",
                    field="artwork.size_bytes",
                    message=f"Cover artwork size ({meta.artwork.size_bytes} bytes) exceeds limit ({max_cover_size_bytes} bytes).",
                )
            )

    # 3. Check Synced Lyrics Constraints
    if require_synced_lyrics:
        lyrics_text = meta.tags.lyrics or ""
        if not lyrics_text.strip():
            violations.append(
                AuditViolation(
                    rule="require_synced_lyrics",
                    field="lyrics",
                    message="Lyrics are required but missing.",
                )
            )
        elif not is_synced_lyrics(lyrics_text):
            violations.append(
                AuditViolation(
                    rule="require_synced_lyrics",
                    field="lyrics",
                    message="Embedded lyrics do not contain standard LRC timestamps [mm:ss.xx].",
                )
            )

    # 4. Check ISRC format if present or requested
    if (validate_isrc_format or "isrc" in req_fields) and meta.tags.isrc:
        isrc_clean = meta.tags.isrc.strip().replace("-", "")
        if len(isrc_clean) != 12:
            violations.append(
                AuditViolation(
                    rule="isrc_format",
                    field="isrc",
                    message=f"ISRC '{meta.tags.isrc}' is not a valid 12-character ISRC string.",
                )
            )

    # Summarize
    passed = len(violations) == 0
    summary = {
        "title": meta.tags.title,
        "artist": meta.tags.artist,
        "album": meta.tags.album,
        "has_artwork": meta.artwork.exists,
        "has_lyrics": bool(meta.tags.lyrics),
        "duration_seconds": meta.duration_seconds,
    }

    return AuditReport(
        file_path=str(path),
        format=meta.format,
        passed=passed,
        violations=violations,
        metadata_summary=summary,
    )
