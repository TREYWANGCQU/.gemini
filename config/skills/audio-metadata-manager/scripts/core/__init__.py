# scripts/core/__init__.py
"""
Audio Metadata Manager - Core Module
"""
from .reader import read_metadata, UniversalAudioMetadata
from .writer import write_metadata
from .artwork import extract_artwork, set_artwork, remove_artwork
from .lyrics import extract_lyrics, set_lyrics, remove_lyrics
from .auditor import audit_metadata, AuditReport, AuditViolation

__all__ = [
    "read_metadata",
    "UniversalAudioMetadata",
    "write_metadata",
    "extract_artwork",
    "set_artwork",
    "remove_artwork",
    "extract_lyrics",
    "set_lyrics",
    "remove_lyrics",
    "audit_metadata",
    "AuditReport",
    "AuditViolation",
]
