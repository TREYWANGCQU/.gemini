# scripts/core/reader.py
"""
Unified Audio Metadata Reader
Extracts container format, acoustic parameters, universal tags, embedded lyrics, and artwork metadata.
"""

from dataclasses import dataclass, field, asdict
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional
import os

try:
    from PIL import Image
except ImportError:
    Image = None

import mutagen
from mutagen.flac import FLAC
from mutagen.id3 import ID3, APIC, USLT, SYLT, COMM, TXXX
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE


@dataclass
class ArtworkMetadata:
    exists: bool = False
    mime: Optional[str] = None
    type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    size_bytes: Optional[int] = None
    description: Optional[str] = None


@dataclass
class UniversalTags:
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    album_artist: Optional[str] = None
    composer: Optional[str] = None
    lyricist: Optional[str] = None
    track_number: Optional[str] = None
    disc_number: Optional[str] = None
    date: Optional[str] = None
    genre: Optional[str] = None
    isrc: Optional[str] = None
    comment: Optional[str] = None
    lyrics: Optional[str] = None
    custom: Dict[str, str] = field(default_factory=dict)


@dataclass
class UniversalAudioMetadata:
    file_path: str
    format: str
    duration_seconds: float = 0.0
    bitrate_kbps: Optional[int] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    tags: UniversalTags = field(default_factory=UniversalTags)
    artwork: ArtworkMetadata = field(default_factory=ArtworkMetadata)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _get_image_dimensions(image_data: bytes) -> tuple[Optional[int], Optional[int]]:
    if Image and image_data:
        try:
            with Image.open(BytesIO(image_data)) as img:
                return img.width, img.height
        except Exception:
            return None, None
    return None, None


def _parse_id3_tags(tags: ID3, meta: UniversalAudioMetadata) -> None:
    if "TIT2" in tags:
        meta.tags.title = str(tags["TIT2"].text[0])
    if "TPE1" in tags:
        meta.tags.artist = str(tags["TPE1"].text[0])
    if "TALB" in tags:
        meta.tags.album = str(tags["TALB"].text[0])
    if "TPE2" in tags:
        meta.tags.album_artist = str(tags["TPE2"].text[0])
    if "TCOM" in tags:
        meta.tags.composer = str(tags["TCOM"].text[0])
    if "TEXT" in tags:
        meta.tags.lyricist = str(tags["TEXT"].text[0])
    if "TRCK" in tags:
        meta.tags.track_number = str(tags["TRCK"].text[0])
    if "TPOS" in tags:
        meta.tags.disc_number = str(tags["TPOS"].text[0])
    if "TDRC" in tags:
        meta.tags.date = str(tags["TDRC"].text[0])
    elif "TYER" in tags:
        meta.tags.date = str(tags["TYER"].text[0])
    if "TCON" in tags:
        meta.tags.genre = str(tags["TCON"].text[0])
    if "TSRC" in tags:
        meta.tags.isrc = str(tags["TSRC"].text[0])

    for key, val in tags.items():
        if key.startswith("COMM") and meta.tags.comment is None:
            meta.tags.comment = str(val.text[0])
        elif (key.startswith("USLT") or key.startswith("SYLT")) and meta.tags.lyrics is None:
            meta.tags.lyrics = str(val.text if hasattr(val, "text") else val)
        elif key.startswith("TXXX:"):
            desc = getattr(val, "desc", "") or key[5:]
            text_val = str(val.text[0]) if val.text else ""
            meta.tags.custom[desc] = text_val
        elif key.startswith("APIC") and not meta.artwork.exists:
            img_data = val.data
            w, h = _get_image_dimensions(img_data)
            meta.artwork = ArtworkMetadata(
                exists=True,
                mime=val.mime,
                type=str(val.type),
                width=w,
                height=h,
                size_bytes=len(img_data),
                description=val.desc or "Cover (front)",
            )


def _read_mp3_metadata(audio_path: str, meta: UniversalAudioMetadata) -> UniversalAudioMetadata:
    audio = MP3(audio_path)
    meta.format = "MP3"
    meta.duration_seconds = round(audio.info.length, 2)
    meta.bitrate_kbps = int(audio.info.bitrate / 1000) if audio.info.bitrate else None
    meta.sample_rate = audio.info.sample_rate
    meta.channels = audio.info.channels

    if audio.tags:
        _parse_id3_tags(audio.tags, meta)

    return meta


def _read_wav_metadata(audio_path: str, meta: UniversalAudioMetadata) -> UniversalAudioMetadata:
    meta.format = "WAV"
    audio = WAVE(audio_path)
    meta.duration_seconds = round(audio.info.length, 2)
    meta.bitrate_kbps = int(audio.info.bitrate / 1000) if getattr(audio.info, "bitrate", None) else None
    meta.sample_rate = audio.info.sample_rate
    meta.channels = audio.info.channels

    if audio.tags:
        _parse_id3_tags(audio.tags, meta)

    return meta



def _read_mp4_metadata(audio_path: str, meta: UniversalAudioMetadata) -> UniversalAudioMetadata:
    meta.format = "M4A"
    audio = MP4(audio_path)
    meta.duration_seconds = round(audio.info.length, 2)
    meta.bitrate_kbps = int(audio.info.bitrate / 1000) if getattr(audio.info, "bitrate", None) else None
    meta.sample_rate = getattr(audio.info, "sample_rate", None)
    meta.channels = getattr(audio.info, "channels", None)

    tags = audio.tags
    if tags:
        if "\xa9nam" in tags:
            meta.tags.title = str(tags["\xa9nam"][0])
        if "\xa9ART" in tags:
            meta.tags.artist = str(tags["\xa9ART"][0])
        if "\xa9alb" in tags:
            meta.tags.album = str(tags["\xa9alb"][0])
        if "aART" in tags:
            meta.tags.album_artist = str(tags["aART"][0])
        if "\xa9wrt" in tags:
            meta.tags.composer = str(tags["\xa9wrt"][0])
        if "trkn" in tags and tags["trkn"]:
            trk = tags["trkn"][0]
            meta.tags.track_number = f"{trk[0]}/{trk[1]}" if len(trk) > 1 and trk[1] else str(trk[0])
        if "disk" in tags and tags["disk"]:
            dsk = tags["disk"][0]
            meta.tags.disc_number = f"{dsk[0]}/{dsk[1]}" if len(dsk) > 1 and dsk[1] else str(dsk[0])
        if "\xa9day" in tags:
            meta.tags.date = str(tags["\xa9day"][0])
        if "\xa9gen" in tags:
            meta.tags.genre = str(tags["\xa9gen"][0])
        if "\xa9cmt" in tags:
            meta.tags.comment = str(tags["\xa9cmt"][0])
        if "\xa9lyr" in tags:
            meta.tags.lyrics = str(tags["\xa9lyr"][0])
        if "----:com.apple.iTunes:ISRC" in tags:
            meta.tags.isrc = tags["----:com.apple.iTunes:ISRC"][0].decode("utf-8", errors="ignore")

        # Artwork
        if "covr" in tags and tags["covr"]:
            cover_data = bytes(tags["covr"][0])
            fmt = tags["covr"][0].imageformat
            mime = "image/png" if fmt == MP4Cover.FORMAT_PNG else "image/jpeg"
            w, h = _get_image_dimensions(cover_data)
            meta.artwork = ArtworkMetadata(
                exists=True,
                mime=mime,
                type="Cover (front)",
                width=w,
                height=h,
                size_bytes=len(cover_data),
                description="Cover (front)",
            )

    return meta


def read_metadata(file_path: str) -> UniversalAudioMetadata:
    """
    Reads metadata from audio file across supported formats (.mp3, .flac, .wav, .m4a, .ogg)
    """
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    ext = path.suffix.lower()
    meta = UniversalAudioMetadata(file_path=str(path), format=ext.lstrip(".").upper())

    if ext == ".mp3":
        return _read_mp3_metadata(str(path), meta)
    elif ext == ".flac":
        return _read_flac_metadata(str(path), meta)
    elif ext == ".wav":
        return _read_wav_metadata(str(path), meta)
    elif ext in (".m4a", ".mp4", ".aac"):
        return _read_mp4_metadata(str(path), meta)
    elif ext == ".ogg":
        audio = OggVorbis(str(path))
        meta.format = "OGG"
        meta.duration_seconds = round(audio.info.length, 2)
        meta.sample_rate = audio.info.sample_rate
        meta.channels = audio.info.channels
        if audio.tags:
            for k, v in audio.tags.items():
                ku = k.upper()
                vs = v[0] if v else ""
                if ku == "TITLE": meta.tags.title = vs
                elif ku == "ARTIST": meta.tags.artist = vs
                elif ku == "ALBUM": meta.tags.album = vs
                elif ku in ("LYRICS", "UNSYNCEDLYRICS"): meta.tags.lyrics = vs
                else: meta.tags.custom[k] = vs
        return meta
    else:
        # Fallback mutagen File
        audio = mutagen.File(str(path))
        if audio is None:
            raise ValueError(f"Unsupported audio format: {file_path}")
        meta.duration_seconds = round(getattr(audio.info, "length", 0.0), 2)
        return meta
