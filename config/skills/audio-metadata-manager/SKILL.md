---
name: audio-metadata-manager
description: Inspect, mutate, embed cover art and lyrics, batch process, and CI-audit audio metadata across MP3, FLAC, WAV, M4A, and OGG formats with lossless, zero-reencoding tag operations.
---

# Audio Metadata Manager

## Overview
This skill provides a unified, lossless audio metadata engineering toolchain designed for CLI automation and CI/CD quality gates. It supports viewing, modifying, embedding cover artwork, syncing LRC lyrics, and enforcing release-standard metadata compliance across MP3, FLAC, WAV, M4A, and OGG containers without re-encoding audio payloads.

## Core Capabilities
1. **Multi-Format Lossless Tagging**:
   - `MP3`: ID3v2.3 / ID3v2.4 frames (`TIT2`, `TPE1`, `TALB`, `APIC`, `USLT`, `TXXX`, etc.).
   - `FLAC`: Vorbis comments (`TITLE`, `ARTIST`, `LYRICS`, `METADATA_BLOCK_PICTURE`, etc.).
   - `WAV`: Dual-compatibility (RIFF `INFO` chunks & embedded `ID3` chunks).
   - `M4A/AAC`: MP4 atoms (`©nam`, `©ART`, `covr`, `©lyr`, `----:com.apple.iTunes:ISRC`).
2. **First-Class Cover Artwork (APIC / Picture / Covr)**:
   - Extract embedded album art to image files (`.jpg`, `.png`, `.webp`).
   - Validate and embed high-resolution square covers with MIME & magic-byte protection.
   - Clean/strip embedded artwork to minimize file footprint.
3. **First-Class Lyrics Pipeline (Plain & Synced LRC)**:
   - Embed synchronized LRC (`[mm:ss.xx]`) or plain text lyrics directly into container frames.
   - Extract embedded lyrics back into `.lrc` or `.txt` sidecars.
   - Seamlessly chain with `ai-lyrics-aligner` output.
4. **CI/CD Quality Gate & Rule Auditor**:
   - Audit required metadata fields (`title`, `artist`, `album`, `artwork`, `lyrics`, `isrc`).
   - Validate cover minimum resolution (e.g. `500x500`) and maximum payload byte size.
   - Enforce synchronized timestamp verification for streaming release standards.
   - Output structured JSON logs and deterministic exit codes (`0` for pass, `1` for violations, `2` for error).

---

## Directory Structure
- `scripts/audio_metadata_cli.py`: Main CLI entry point.
- `scripts/core/reader.py`: Universal audio format parser & acoustic property extractor.
- `scripts/core/writer.py`: Lossless tag mutation & transaction engine.
- `scripts/core/artwork.py`: Image validation, scaling, APIC/Picture block encoder.
- `scripts/core/lyrics.py`: Plain and LRC timestamp lyrics parser & injector.
- `scripts/core/auditor.py`: CI rule validation & violation reporting engine.

---

## CLI Usage Workflow

### 1. Inspect Audio Metadata & Artwork
```bash
# Human-readable summary
python "C:\Users\Reaticle\.gemini\config\skills\audio-metadata-manager\scripts\audio_metadata_cli.py" inspect "track.flac"

# Standard JSON output for scripts & pipelines
python "C:\Users\Reaticle\.gemini\config\skills\audio-metadata-manager\scripts\audio_metadata_cli.py" inspect "track.mp3" --json
```

### 2. Mutate Tags & Embed Artwork / Lyrics
```bash
python "C:\Users\Reaticle\.gemini\config\skills\audio-metadata-manager\scripts\audio_metadata_cli.py" mutate "track.wav" \
  --title "Dawn of Genesis" \
  --artist "AI Orchestrator" \
  --album "Cyber Odyssey" \
  --track "1/8" \
  --date "2026-08-20" \
  --genre "Cyberpunk Synthwave" \
  --isrc "CN-XXX-26-00001" \
  --set-cover "cover.jpg" \
  --set-lyrics "lyrics.lrc" \
  --custom "PROMPT_SPEC=spec-001" "BPM=128"
```

### 3. Extract Embedded Cover Artwork & Lyrics
```bash
# Extract cover image
python "C:\Users\Reaticle\.gemini\config\skills\audio-metadata-manager\scripts\audio_metadata_cli.py" extract-cover "track.flac" "extracted_cover.jpg"

# Extract embedded lyrics
python "C:\Users\Reaticle\.gemini\config\skills\audio-metadata-manager\scripts\audio_metadata_cli.py" extract-lyrics "track.mp3" "extracted_lyrics.lrc"
```

### 4. CI/CD Audit & Quality Gate
```bash
# Audit a single file or directory
python "C:\Users\Reaticle\.gemini\config\skills\audio-metadata-manager\scripts\audio_metadata_cli.py" audit "./dist_tracks" \
  --require "title,artist,album,artwork,lyrics" \
  --min-cover-res "500x500" \
  --require-synced-lyrics \
  --validate-isrc \
  --recursive \
  --json
```

---

## Metadata Tag Mapping Reference

| Universal Field | MP3 (ID3v2.3/2.4) | FLAC / OGG (Vorbis) | WAV (RIFF + ID3) | M4A (MP4 Atom) |
| :--- | :--- | :--- | :--- | :--- |
| **Title** | `TIT2` | `TITLE` | `INAM` + `TIT2` | `©nam` |
| **Artist** | `TPE1` | `ARTIST` | `IART` + `TPE1` | `©ART` |
| **Album** | `TALB` | `ALBUM` | `IPRD` + `TALB` | `©alb` |
| **Cover** | `APIC (Front)` | `METADATA_BLOCK_PICTURE` | `APIC (ID3)` | `covr` |
| **Lyrics** | `USLT` / `SYLT` | `LYRICS` | `USLT (ID3)` | `©lyr` |
| **Track No.** | `TRCK` | `TRACKNUMBER` | `ITRK` + `TRCK` | `trkn` |
| **ISRC** | `TSRC` | `ISRC` | `ISRC` + `TSRC` | `----:com.apple.iTunes:ISRC` |
| **Custom** | `TXXX:KEY` | `KEY=VAL` | `TXXX:KEY` | `----:com.apple.iTunes:KEY` |
