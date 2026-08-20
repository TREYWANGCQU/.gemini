# scripts/core/lyrics.py
"""
Lyrics Manager
Handles extracting, embedding, verifying, and removing lyrics (Plain & Synced LRC) across MP3, FLAC, WAV, M4A, and OGG formats.
"""

from pathlib import Path
from typing import Optional, Union
import re

from mutagen.flac import FLAC
from mutagen.id3 import ID3, USLT, SYLT, ID3NoHeaderError
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE

LRC_TIMESTAMP_REGEX = re.compile(r"\[\d{2}:\d{2}\.\d{2,3}\]")


def is_synced_lyrics(text: str) -> bool:
    """
    Returns True if the lyrics contain standard LRC timestamp tags [mm:ss.xx].
    """
    if not text:
        return False
    return bool(LRC_TIMESTAMP_REGEX.search(text))


def extract_lyrics(audio_path: str, output_path: Optional[str] = None) -> Optional[str]:
    """
    Extracts embedded lyrics from audio file.
    If output_path is provided, writes lyrics to a .lrc or .txt file.
    """
    path = Path(audio_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    ext = path.suffix.lower()
    lyrics_text: Optional[str] = None

    if ext == ".mp3":
        try:
            tags = ID3(str(path))
            for k, v in tags.items():
                if k.startswith("USLT"):
                    lyrics_text = str(v.text)
                    break
                elif k.startswith("SYLT"):
                    lyrics_text = str(v)
                    break
        except ID3NoHeaderError:
            lyrics_text = None

    elif ext == ".wav":
        audio = WAVE(str(path))
        if audio.tags:
            for k, v in audio.tags.items():
                if k.startswith("USLT"):
                    lyrics_text = str(v.text)
                    break
                elif k.startswith("SYLT"):
                    lyrics_text = str(v)
                    break


    elif ext == ".flac":
        audio = FLAC(str(path))
        if audio.tags:
            for k, v in audio.tags.items():
                if k.upper() in ("LYRICS", "UNSYNCEDLYRICS") and v:
                    lyrics_text = v[0]
                    break

    elif ext in (".m4a", ".mp4", ".aac"):
        audio = MP4(str(path))
        if audio.tags and "\xa9lyr" in audio.tags and audio.tags["\xa9lyr"]:
            lyrics_text = str(audio.tags["\xa9lyr"][0])

    elif ext == ".ogg":
        audio = OggVorbis(str(path))
        if audio.tags:
            for k, v in audio.tags.items():
                if k.upper() in ("LYRICS", "UNSYNCEDLYRICS") and v:
                    lyrics_text = v[0]
                    break

    if not lyrics_text:
        return None

    if output_path:
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(lyrics_text)

    return lyrics_text


def set_lyrics(
    audio_path: str,
    lyrics_input: Union[str, Path],
    language: str = "eng",
    description: str = "",
) -> bool:
    """
    Injects or replaces lyrics in the specified audio file.
    lyrics_input can be raw lyrics text or a path to a .lrc / .txt file.
    """
    path = Path(audio_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    lyrics_text = ""
    # Check if lyrics_input is a valid file path
    if isinstance(lyrics_input, (str, Path)):
        p = Path(lyrics_input)
        if p.is_file():
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                lyrics_text = f.read()
        else:
            lyrics_text = str(lyrics_input)
    else:
        lyrics_text = str(lyrics_input)

    lyrics_text = lyrics_text.strip()
    if not lyrics_text:
        raise ValueError("Lyrics content cannot be empty")

    ext = path.suffix.lower()

    if ext == ".mp3":
        audio = MP3(str(path))
        if audio.tags is None:
            audio.add_tags()
        audio.tags.delall("USLT")
        audio.tags.delall("SYLT")
        audio.tags.add(
            USLT(
                encoding=3,  # UTF-8
                lang=language,
                desc=description,
                text=lyrics_text,
            )
        )
        audio.save(v2_version=3)
        return True

    elif ext == ".flac":
        audio = FLAC(str(path))
        if audio.tags is None:
            audio.add_tags()
        audio.tags["LYRICS"] = [lyrics_text]
        audio.tags["UNSYNCEDLYRICS"] = [lyrics_text]
        audio.save()
        return True

    elif ext == ".wav":
        audio = WAVE(str(path))
        if audio.tags is None:
            audio.add_tags()
        audio.tags.delall("USLT")
        audio.tags.add(
            USLT(
                encoding=3,
                lang=language,
                desc=description,
                text=lyrics_text,
            )
        )
        audio.save()
        return True

    elif ext in (".m4a", ".mp4", ".aac"):
        audio = MP4(str(path))
        if audio.tags is None:
            audio.add_tags()
        audio.tags["\xa9lyr"] = [lyrics_text]
        audio.save()
        return True

    elif ext == ".ogg":
        audio = OggVorbis(str(path))
        if audio.tags is None:
            audio.add_tags()
        audio.tags["LYRICS"] = [lyrics_text]
        audio.save()
        return True

    else:
        raise ValueError(f"Unsupported format for lyrics injection: {ext}")


def remove_lyrics(audio_path: str) -> bool:
    """
    Removes embedded lyrics from audio file.
    """
    path = Path(audio_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    ext = path.suffix.lower()

    if ext == ".mp3":
        try:
            tags = ID3(str(path))
            tags.delall("USLT")
            tags.delall("SYLT")
            tags.save(str(path))
            return True
        except ID3NoHeaderError:
            return True

    elif ext == ".wav":
        audio = WAVE(str(path))
        if audio.tags:
            audio.tags.delall("USLT")
            audio.tags.delall("SYLT")
            audio.save()
        return True


    elif ext == ".flac":
        audio = FLAC(str(path))
        if audio.tags:
            if "LYRICS" in audio.tags:
                del audio.tags["LYRICS"]
            if "UNSYNCEDLYRICS" in audio.tags:
                del audio.tags["UNSYNCEDLYRICS"]
            audio.save()
            return True

    elif ext in (".m4a", ".mp4", ".aac"):
        audio = MP4(str(path))
        if audio.tags and "\xa9lyr" in audio.tags:
            del audio.tags["\xa9lyr"]
            audio.save()
            return True

    elif ext == ".ogg":
        audio = OggVorbis(str(path))
        if audio.tags and "LYRICS" in audio.tags:
            del audio.tags["LYRICS"]
            audio.save()
            return True

    return False
