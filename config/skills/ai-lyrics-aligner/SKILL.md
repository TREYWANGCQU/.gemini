---
name: AI Lyrics Aligner
description: Extract, sanitize, and synchronize lyrics from AI music prompt specs and isolated vocal audio stems into standard LRC, word-level LRC, SRT, and DAW marker tracks.
---

# AI Lyrics Aligner

## Overview
This skill provides an automated pipeline to extract ground-truth lyrics and structural metatags from AI music prompt specifications (e.g. `02_ai_music_prompt_spec.md`), align them with vocal audio tracks (e.g. `audio [vocals].wav`), and export time-synchronized lyric formats (`.lrc`, `.srt`, `.csv`).

## Core Capabilities
1. **Text Normalization & Metatag Extraction**: Strips performance cues while capturing section markers (`[Verse]`, `[Chorus]`, `[Bridge]`).
2. **Audio Alignment & Reconciliation**: Matches vocal audio waveforms against prompt lyrics with tolerance for AI ad-libs and vocal rubato.
3. **Multi-Format Export**:
   - Standard Line-Level LRC (`[mm:ss.xx]`)
   - Syllable/Word-Level Enhanced LRC
   - SubRip Subtitles (`.srt`)
   - DAW Track Markers (`.csv`)

## Directory Structure
- `scripts/extract_lyrics.py`: Markdown parser for AI music prompt specs.
- `scripts/align_lyrics.py`: Core forced alignment and timecode resolver.
- `scripts/lrc_formatter.py`: Formatter for standard LRC, SRT, and DAW markers.

## Usage Workflow

### 1. Extract Ground-Truth Lyrics from Spec
```bash
python "C:\Users\Reaticle\.gemini\config\skills\ai-lyrics-aligner\scripts\extract_lyrics.py" --input "<path_to_spec.md>" --output "extracted_lyrics.json"
```

### 2. Run Audio Alignment & Export Formats
```bash
python "C:\Users\Reaticle\.gemini\config\skills\ai-lyrics-aligner\scripts\align_lyrics.py" --audio "<path_to_vocals.wav>" --lyrics "extracted_lyrics.json" --output-lrc "output.lrc" --output-srt "output.srt" --output-markers "markers.csv"
```
