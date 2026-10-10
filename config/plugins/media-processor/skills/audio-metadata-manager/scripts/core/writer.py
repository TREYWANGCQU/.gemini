# scripts/core/writer.py
"""
Unified Audio Metadata Writer
Performs lossless, idempotent tag mutations across MP3, FLAC, WAV, M4A, and OGG formats.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

from mutagen.flac import FLAC
from mutagen.id3 import (
    ID3,
    TIT2,
    TPE1,
    TALB,
    TPE2,
    TCOM,
    TEXT,
    TRCK,
    TPOS,
    TDRC,
    TCON,
    TSRC,
    COMM,
    TXXX,
)
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE

from .artwork import set_artwork, remove_artwork
from .lyrics import set_lyrics, remove_lyrics


def _write_mp3_tags(audio_path: str, tags: Dict[str, Any]) -> None:
    audio = MP3(audio_path)
    if audio.tags is None:
        audio.add_tags()
    id3 = audio.tags

    if "title" in tags and tags["title"] is not None:
        id3["TIT2"] = TIT2(encoding=3, text=[str(tags["title"])])
    if "artist" in tags and tags["artist"] is not None:
        id3["TPE1"] = TPE1(encoding=3, text=[str(tags["artist"])])
    if "album" in tags and tags["album"] is not None:
        id3["TALB"] = TALB(encoding=3, text=[str(tags["album"])])
    if "album_artist" in tags and tags["album_artist"] is not None:
        id3["TPE2"] = TPE2(encoding=3, text=[str(tags["album_artist"])])
    if "composer" in tags and tags["composer"] is not None:
        id3["TCOM"] = TCOM(encoding=3, text=[str(tags["composer"])])
    if "lyricist" in tags and tags["lyricist"] is not None:
        id3["TEXT"] = TEXT(encoding=3, text=[str(tags["lyricist"])])
    if "track_number" in tags and tags["track_number"] is not None:
        id3["TRCK"] = TRCK(encoding=3, text=[str(tags["track_number"])])
    if "disc_number" in tags and tags["disc_number"] is not None:
        id3["TPOS"] = TPOS(encoding=3, text=[str(tags["disc_number"])])
    if "date" in tags and tags["date"] is not None:
        id3["TDRC"] = TDRC(encoding=3, text=[str(tags["date"])])
    if "genre" in tags and tags["genre"] is not None:
        id3["TCON"] = TCON(encoding=3, text=[str(tags["genre"])])
    if "isrc" in tags and tags["isrc"] is not None:
        id3["TSRC"] = TSRC(encoding=3, text=[str(tags["isrc"])])
    if "comment" in tags and tags["comment"] is not None:
        id3["COMM::eng"] = COMM(encoding=3, lang="eng", desc="", text=[str(tags["comment"])])

    if "custom" in tags and isinstance(tags["custom"], dict):
        for k, v in tags["custom"].items():
            if v is not None:
                id3[f"TXXX:{k}"] = TXXX(encoding=3, desc=k, text=[str(v)])

    audio.save(v2_version=3)


def _write_flac_tags(audio_path: str, tags: Dict[str, Any]) -> None:
    audio = FLAC(audio_path)
    if audio.tags is None:
        audio.add_tags()

    mapping = {
        "title": "TITLE",
        "artist": "ARTIST",
        "album": "ALBUM",
        "album_artist": "ALBUMARTIST",
        "composer": "COMPOSER",
        "lyricist": "LYRICIST",
        "track_number": "TRACKNUMBER",
        "disc_number": "DISCNUMBER",
        "date": "DATE",
        "genre": "GENRE",
        "isrc": "ISRC",
        "comment": "COMMENT",
    }

    for standard_key, vorbis_key in mapping.items():
        if standard_key in tags and tags[standard_key] is not None:
            audio.tags[vorbis_key] = [str(tags[standard_key])]

    if "custom" in tags and isinstance(tags["custom"], dict):
        for k, v in tags["custom"].items():
            if v is not None:
                audio.tags[k] = [str(v)]

    audio.save()


def _write_wav_tags(audio_path: str, tags: Dict[str, Any]) -> None:
    audio = WAVE(audio_path)
    if audio.tags is None:
        audio.add_tags()
    id3 = audio.tags

    if "title" in tags and tags["title"] is not None:
        id3["TIT2"] = TIT2(encoding=3, text=[str(tags["title"])])
    if "artist" in tags and tags["artist"] is not None:
        id3["TPE1"] = TPE1(encoding=3, text=[str(tags["artist"])])
    if "album" in tags and tags["album"] is not None:
        id3["TALB"] = TALB(encoding=3, text=[str(tags["album"])])
    if "album_artist" in tags and tags["album_artist"] is not None:
        id3["TPE2"] = TPE2(encoding=3, text=[str(tags["album_artist"])])
    if "composer" in tags and tags["composer"] is not None:
        id3["TCOM"] = TCOM(encoding=3, text=[str(tags["composer"])])
    if "lyricist" in tags and tags["lyricist"] is not None:
        id3["TEXT"] = TEXT(encoding=3, text=[str(tags["lyricist"])])
    if "track_number" in tags and tags["track_number"] is not None:
        id3["TRCK"] = TRCK(encoding=3, text=[str(tags["track_number"])])
    if "disc_number" in tags and tags["disc_number"] is not None:
        id3["TPOS"] = TPOS(encoding=3, text=[str(tags["disc_number"])])
    if "date" in tags and tags["date"] is not None:
        id3["TDRC"] = TDRC(encoding=3, text=[str(tags["date"])])
    if "genre" in tags and tags["genre"] is not None:
        id3["TCON"] = TCON(encoding=3, text=[str(tags["genre"])])
    if "isrc" in tags and tags["isrc"] is not None:
        id3["TSRC"] = TSRC(encoding=3, text=[str(tags["isrc"])])
    if "comment" in tags and tags["comment"] is not None:
        id3["COMM::eng"] = COMM(encoding=3, lang="eng", desc="", text=[str(tags["comment"])])

    if "custom" in tags and isinstance(tags["custom"], dict):
        for k, v in tags["custom"].items():
            if v is not None:
                id3[f"TXXX:{k}"] = TXXX(encoding=3, desc=k, text=[str(v)])

    audio.save()


def _write_mp4_tags(audio_path: str, tags: Dict[str, Any]) -> None:
    audio = MP4(audio_path)
    if audio.tags is None:
        audio.add_tags()
    mp4_tags = audio.tags

    if "title" in tags and tags["title"] is not None:
        mp4_tags["\xa9nam"] = [str(tags["title"])]
    if "artist" in tags and tags["artist"] is not None:
        mp4_tags["\xa9ART"] = [str(tags["artist"])]
    if "album" in tags and tags["album"] is not None:
        mp4_tags["\xa9alb"] = [str(tags["album"])]
    if "album_artist" in tags and tags["album_artist"] is not None:
        mp4_tags["aART"] = [str(tags["album_artist"])]
    if "composer" in tags and tags["composer"] is not None:
        mp4_tags["\xa9wrt"] = [str(tags["composer"])]
    if "date" in tags and tags["date"] is not None:
        mp4_tags["\xa9day"] = [str(tags["date"])]
    if "genre" in tags and tags["genre"] is not None:
        mp4_tags["\xa9gen"] = [str(tags["genre"])]
    if "comment" in tags and tags["comment"] is not None:
        mp4_tags["\xa9cmt"] = [str(tags["comment"])]
    if "isrc" in tags and tags["isrc"] is not None:
        mp4_tags["----:com.apple.iTunes:ISRC"] = [str(tags["isrc"]).encode("utf-8")]

    if "track_number" in tags and tags["track_number"] is not None:
        val = str(tags["track_number"])
        if "/" in val:
            parts = val.split("/")
            mp4_tags["trkn"] = [(int(parts[0]), int(parts[1]))]
        else:
            mp4_tags["trkn"] = [(int(val), 0)]

    if "disc_number" in tags and tags["disc_number"] is not None:
        val = str(tags["disc_number"])
        if "/" in val:
            parts = val.split("/")
            mp4_tags["disk"] = [(int(parts[0]), int(parts[1]))]
        else:
            mp4_tags["disk"] = [(int(val), 0)]

    audio.save()


def _write_ogg_tags(audio_path: str, tags: Dict[str, Any]) -> None:
    audio = OggVorbis(audio_path)
    if audio.tags is None:
        audio.add_tags()

    mapping = {
        "title": "TITLE",
        "artist": "ARTIST",
        "album": "ALBUM",
        "album_artist": "ALBUMARTIST",
        "composer": "COMPOSER",
        "track_number": "TRACKNUMBER",
        "date": "DATE",
        "genre": "GENRE",
        "isrc": "ISRC",
        "comment": "COMMENT",
    }
    for standard_key, vorbis_key in mapping.items():
        if standard_key in tags and tags[standard_key] is not None:
            audio.tags[vorbis_key] = [str(tags[standard_key])]

    audio.save()


def write_metadata(
    audio_path: str,
    tags: Optional[Dict[str, Any]] = None,
    cover_image: Optional[Union[str, bytes]] = None,
    remove_cover_flag: bool = False,
    lyrics_content_or_path: Optional[str] = None,
    remove_lyrics_flag: bool = False,
) -> bool:
    """
    Unified metadata write entry point.
    Mutates tags, cover artwork, and lyrics safely in a single transaction.
    """
    path = Path(audio_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    ext = path.suffix.lower()

    # Automatically delegate lyrics if provided inside tags dict and not overridden
    if lyrics_content_or_path is None and not remove_lyrics_flag and tags and "lyrics" in tags and tags["lyrics"]:
        lyrics_content_or_path = tags["lyrics"]

    # 1. Update text tags
    if tags:
        if ext == ".mp3":
            _write_mp3_tags(str(path), tags)
        elif ext == ".flac":
            _write_flac_tags(str(path), tags)
        elif ext == ".wav":
            _write_wav_tags(str(path), tags)
        elif ext in (".m4a", ".mp4", ".aac"):
            _write_mp4_tags(str(path), tags)
        elif ext == ".ogg":
            _write_ogg_tags(str(path), tags)
        else:
            raise ValueError(f"Unsupported format for metadata write: {ext}")

    # 2. Update cover artwork
    if remove_cover_flag:
        remove_artwork(str(path))
    elif cover_image is not None:
        set_artwork(str(path), cover_image)

    # 3. Update lyrics
    if remove_lyrics_flag:
        remove_lyrics(str(path))
    elif lyrics_content_or_path is not None:
        set_lyrics(str(path), lyrics_content_or_path)

    return True
