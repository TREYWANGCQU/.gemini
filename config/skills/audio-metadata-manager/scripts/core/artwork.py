# scripts/core/artwork.py
"""
Artwork (Cover Art) Manager
Supports extracting, embedding, verifying, and removing cover images across MP3, FLAC, WAV, M4A, and OGG formats.
"""

from io import BytesIO
from pathlib import Path
from typing import Optional, Union
import mimetypes

try:
    from PIL import Image
except ImportError:
    Image = None

from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, APIC, ID3NoHeaderError
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE


def _detect_mime_and_validate(image_data: bytes, specified_mime: Optional[str] = None) -> tuple[str, int, int]:
    """
    Validates image bytes, returns (mime_type, width, height).
    """
    if not image_data:
        raise ValueError("Image data cannot be empty")

    width, height = 0, 0
    detected_mime = specified_mime

    if Image:
        try:
            with Image.open(BytesIO(image_data)) as img:
                width, height = img.width, img.height
                fmt = (img.format or "").upper()
                if fmt in ("JPEG", "JPG"):
                    detected_mime = "image/jpeg"
                elif fmt == "PNG":
                    detected_mime = "image/png"
                elif fmt == "WEBP":
                    detected_mime = "image/webp"
                else:
                    detected_mime = f"image/{fmt.lower()}"
        except Exception as e:
            raise ValueError(f"Invalid image file or corrupted image stream: {e}")
    else:
        # Simple magic bytes fallback
        if image_data.startswith(b"\xff\xd8\xff"):
            detected_mime = "image/jpeg"
        elif image_data.startswith(b"\x89PNG\r\n\x1a\n"):
            detected_mime = "image/png"
        elif image_data.startswith(b"RIFF") and b"WEBP" in image_data[:16]:
            detected_mime = "image/webp"
        else:
            detected_mime = specified_mime or "image/jpeg"

    return detected_mime, width, height


def extract_artwork(audio_path: str, output_path: Optional[str] = None) -> Optional[bytes]:
    """
    Extracts embedded cover artwork bytes from audio file.
    If output_path is provided, writes image file to disk.
    """
    path = Path(audio_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    ext = path.suffix.lower()
    img_data: Optional[bytes] = None
    default_ext = ".jpg"

    if ext == ".mp3":
        try:
            tags = ID3(str(path))
            for k, v in tags.items():
                if k.startswith("APIC"):
                    img_data = v.data
                    if v.mime == "image/png":
                        default_ext = ".png"
                    break
        except ID3NoHeaderError:
            img_data = None

    elif ext == ".wav":
        audio = WAVE(str(path))
        if audio.tags:
            for k, v in audio.tags.items():
                if k.startswith("APIC"):
                    img_data = v.data
                    if v.mime == "image/png":
                        default_ext = ".png"
                    break

    elif ext == ".flac":
        audio = FLAC(str(path))
        if audio.pictures:
            pic = audio.pictures[0]
            img_data = pic.data
            if pic.mime == "image/png":
                default_ext = ".png"

    elif ext in (".m4a", ".mp4", ".aac"):
        audio = MP4(str(path))
        if audio.tags and "covr" in audio.tags and audio.tags["covr"]:
            covr = audio.tags["covr"][0]
            img_data = bytes(covr)
            if getattr(covr, "imageformat", None) == MP4Cover.FORMAT_PNG:
                default_ext = ".png"

    elif ext == ".ogg":
        audio = OggVorbis(str(path))
        if audio.pictures:
            pic = audio.pictures[0]
            img_data = pic.data
            if pic.mime == "image/png":
                default_ext = ".png"

    if not img_data:
        return None

    if output_path:
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "wb") as f:
            f.write(img_data)

    return img_data



def set_artwork(
    audio_path: str,
    image_input: Union[str, bytes],
    mime: Optional[str] = None,
    description: str = "Album Front Cover",
) -> bool:
    """
    Injects or replaces cover artwork in the specified audio file.
    image_input can be a filepath (str) or raw image bytes.
    """
    path = Path(audio_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if isinstance(image_input, (str, Path)):
        img_file = Path(image_input).resolve()
        if not img_file.is_file():
            raise FileNotFoundError(f"Image file not found: {image_input}")
        with open(img_file, "rb") as f:
            image_data = f.read()
    else:
        image_data = image_input

    detected_mime, width, height = _detect_mime_and_validate(image_data, mime)
    ext = path.suffix.lower()

    if ext == ".mp3":
        audio = MP3(str(path))
        if audio.tags is None:
            audio.add_tags()
        # Remove existing APIC
        audio.tags.delall("APIC")
        audio.tags.add(
            APIC(
                encoding=3,  # UTF-8
                mime=detected_mime,
                type=3,  # Front Cover
                desc=description,
                data=image_data,
            )
        )
        audio.save(v2_version=3)
        return True

    elif ext == ".flac":
        audio = FLAC(str(path))
        # Clear existing pictures
        audio.clear_pictures()
        pic = Picture()
        pic.type = 3  # Front Cover
        pic.mime = detected_mime
        pic.desc = description
        pic.width = width
        pic.height = height
        pic.depth = 24
        pic.data = image_data
        audio.add_picture(pic)
        audio.save()
        return True

    elif ext == ".wav":
        audio = WAVE(str(path))
        if audio.tags is None:
            audio.add_tags()
        audio.tags.delall("APIC")
        audio.tags.add(
            APIC(
                encoding=3,
                mime=detected_mime,
                type=3,
                desc=description,
                data=image_data,
            )
        )
        audio.save()
        return True

    elif ext in (".m4a", ".mp4", ".aac"):
        audio = MP4(str(path))
        if audio.tags is None:
            audio.add_tags()
        fmt = MP4Cover.FORMAT_PNG if detected_mime == "image/png" else MP4Cover.FORMAT_JPEG
        audio.tags["covr"] = [MP4Cover(image_data, imageformat=fmt)]
        audio.save()
        return True

    elif ext == ".ogg":
        audio = OggVorbis(str(path))
        audio.clear_pictures()
        pic = Picture()
        pic.type = 3
        pic.mime = detected_mime
        pic.desc = description
        pic.width = width
        pic.height = height
        pic.depth = 24
        pic.data = image_data
        audio.add_picture(pic)
        audio.save()
        return True

    else:
        raise ValueError(f"Unsupported format for artwork injection: {ext}")


def remove_artwork(audio_path: str) -> bool:
    """
    Removes embedded cover artwork from audio file to reduce file size.
    """
    path = Path(audio_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    ext = path.suffix.lower()

    if ext == ".mp3":
        try:
            tags = ID3(str(path))
            tags.delall("APIC")
            tags.save(str(path))
            return True
        except ID3NoHeaderError:
            return True

    elif ext == ".wav":
        audio = WAVE(str(path))
        if audio.tags:
            audio.tags.delall("APIC")
            audio.save()
        return True


    elif ext == ".flac":
        audio = FLAC(str(path))
        audio.clear_pictures()
        audio.save()
        return True

    elif ext in (".m4a", ".mp4", ".aac"):
        audio = MP4(str(path))
        if audio.tags and "covr" in audio.tags:
            del audio.tags["covr"]
            audio.save()
        return True

    elif ext == ".ogg":
        audio = OggVorbis(str(path))
        audio.clear_pictures()
        audio.save()
        return True

    return False
