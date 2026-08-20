# scripts/align_lyrics.py
"""
Acoustic-Guided AI Vocal Lyrics Aligner
Aligns ground-truth lyrics from AI prompt specs against vocal stem waveforms.
Supports pure-Python standard library WAV VAD analysis with optional ML/ASR backend hooks.
"""

import argparse
import json
import math
import os
import struct
import wave
from typing import Any, Dict, List, Tuple

import lrc_formatter
from extract_lyrics import extract_lyrics_from_markdown


def analyze_wav_energy(wav_path: str, frame_duration_ms: int = 20) -> Tuple[List[float], float, int]:
    """Read WAV file and calculate frame-level RMS energy and total duration."""
    with wave.open(wav_path, "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        duration = n_frames / float(framerate)

        bytes_per_sample = sampwidth
        if bytes_per_sample not in (1, 2, 4):
            raise ValueError(f"Unsupported WAV sample width: {bytes_per_sample} bytes")

        frame_size = int(framerate * (frame_duration_ms / 1000.0))
        energies = []

        while True:
            raw_data = wf.readframes(frame_size)
            if not raw_data:
                break
            
            # Unpack samples (support 16-bit PCM standard)
            if bytes_per_sample == 2:
                fmt = f"<{len(raw_data)//2}h"
                samples = struct.unpack(fmt, raw_data)
            elif bytes_per_sample == 1:
                fmt = f"<{len(raw_data)}B"
                samples = [s - 128 for s in struct.unpack(fmt, raw_data)]
            elif bytes_per_sample == 4:
                fmt = f"<{len(raw_data)//4}i"
                samples = struct.unpack(fmt, raw_data)

            # Average channels if stereo
            if n_channels > 1:
                mono_samples = [sum(samples[i:i+n_channels]) / float(n_channels) for i in range(0, len(samples), n_channels)]
            else:
                mono_samples = samples

            if not mono_samples:
                continue

            # Calculate RMS
            sum_sq = sum(s * s for s in mono_samples)
            rms = math.sqrt(sum_sq / len(mono_samples))
            energies.append(rms)

        return energies, duration, frame_duration_ms


def detect_vocal_activity_segments(
    energies: List[float],
    duration: float,
    frame_ms: int = 20,
    threshold_ratio: float = 0.15,
    min_speech_duration_s: float = 0.6,
    min_silence_duration_s: float = 0.5
) -> List[Tuple[float, float]]:
    """Detect contiguous voice activity segments from frame energies."""
    if not energies:
        return [(0.0, duration)]

    max_e = max(energies) if energies else 1.0
    threshold = max_e * threshold_ratio

    frames_per_sec = 1000.0 / frame_ms
    min_speech_frames = int(min_speech_duration_s * frames_per_sec)
    min_silence_frames = int(min_silence_duration_s * frames_per_sec)

    is_speech = [e > threshold for e in energies]
    
    # Smooth silence gaps
    silence_count = 0
    for i in range(len(is_speech)):
        if not is_speech[i]:
            silence_count += 1
        else:
            if 0 < silence_count < min_silence_frames:
                for j in range(i - silence_count, i):
                    is_speech[j] = True
            silence_count = 0

    # Extract intervals
    segments = []
    in_segment = False
    seg_start = 0

    for i, active in enumerate(is_speech):
        if active and not in_segment:
            in_segment = True
            seg_start = i
        elif not in_segment and active:
            pass
        elif in_segment and not active:
            in_segment = False
            seg_len = i - seg_start
            if seg_len >= min_speech_frames:
                start_sec = (seg_start * frame_ms) / 1000.0
                end_sec = (i * frame_ms) / 1000.0
                segments.append((start_sec, min(duration, end_sec)))

    if in_segment:
        start_sec = (seg_start * frame_ms) / 1000.0
        segments.append((start_sec, duration))

    if not segments:
        segments = [(0.0, duration)]

    return segments


def find_companion_vocal_track(audio_path: str) -> str:
    """Find companion isolated vocal track in the same directory if available."""
    if not os.path.exists(audio_path):
        return audio_path
    
    abs_path = os.path.abspath(audio_path)
    dir_name = os.path.dirname(abs_path)
    base_name = os.path.basename(abs_path)
    
    # If the provided audio is already a vocal stem
    if "vocals" in base_name.lower():
        return audio_path
        
    # Search for companion vocal stems
    if dir_name and os.path.exists(dir_name):
        candidates = []
        for f in os.listdir(dir_name):
            if f.endswith(".wav") and "vocals" in f.lower():
                candidates.append(os.path.join(dir_name, f))
        
        # Prefer vocal track stem
        if candidates:
            # Sort: prioritize standard stem (1_*Vocals*.wav) or reaticle vocals
            candidates.sort(key=lambda x: (
                0 if "vocals_reaticle" in x.lower() else (1 if "(vocals)" in x.lower() else 2),
                len(x)
            ))
            return candidates[0]

    return audio_path


def cluster_segments_for_sections(
    segments: List[Tuple[float, float]],
    num_sections: int,
    sec_weights: List[float]
) -> List[Tuple[float, float]]:
    """Cluster raw VAD segments into section-level time intervals using dynamic acoustic silence boundaries."""
    if not segments:
        return []
    if num_sections <= 1:
        return [(segments[0][0], segments[-1][1])]

    active_start = segments[0][0]
    active_end = segments[-1][1]

    # Collect all silence gaps between adjacent speech segments
    all_splits = []
    for i in range(len(segments) - 1):
        seg_end = segments[i][1]
        next_start = segments[i+1][0]
        gap = next_start - seg_end
        all_splits.append({
            "index": i,
            "end_time": seg_end,
            "start_time": next_start,
            "gap": gap
        })

    needed_cuts = num_sections - 1
    if not all_splits:
        # Uniform fallback
        step = (active_end - active_start) / num_sections
        return [(active_start + i*step, active_start + (i+1)*step) for i in range(num_sections)]

    # Dynamic top-N gap selection
    sorted_splits = sorted(all_splits, key=lambda x: x["gap"], reverse=True)
    top_splits = sorted_splits[:needed_cuts]
    top_splits.sort(key=lambda x: x["end_time"])
    
    sec_intervals = []
    curr_s = active_start
    for s in top_splits:
        sec_intervals.append((curr_s, s["end_time"]))
        curr_s = s["start_time"]
    sec_intervals.append((curr_s, active_end))

    return sec_intervals


def align_lyrics_with_vocal_track(
    lyrics_data: Dict[str, Any],
    audio_path: str
) -> Dict[str, Any]:
    """Align lyric sections and lines against audio waveform energy profile."""
    # Check if companion vocal stem is available for VAD precision
    vocal_track_path = find_companion_vocal_track(audio_path)
    
    energies, duration, frame_ms = analyze_wav_energy(vocal_track_path)
    segments = detect_vocal_activity_segments(
        energies,
        duration,
        frame_ms,
        threshold_ratio=0.08,
        min_speech_duration_s=0.4,
        min_silence_duration_s=0.4
    )

    sections = lyrics_data.get("sections", [])
    valid_sections = [s for s in sections if s.get("lines")]
    
    if not valid_sections:
        return lyrics_data

    sec_weights = []
    for s in valid_sections:
        char_count = sum(len(line["text"]) for line in s["lines"])
        sec_weights.append(max(1, char_count))

    sec_intervals = cluster_segments_for_sections(segments, len(valid_sections), sec_weights)

    aligned_sections = []
    sec_idx = 0

    first_active_start = sec_intervals[0][0] if sec_intervals else (segments[0][0] if segments else 0.0)
    last_active_end = sec_intervals[-1][1] if sec_intervals else (segments[-1][1] if segments else duration)

    for section in sections:
        tag = section.get("tag", "")
        sec_type = section.get("type", "Verse")
        lines = section.get("lines", [])
        cues = section.get("cues", [])

        if not lines:
            if sec_type == "Intro" or "intro" in tag.lower():
                s_start = 0.0
                s_end = round(first_active_start, 2)
            else:
                s_start = round(last_active_end, 2)
                s_end = round(duration, 2)

            aligned_sections.append({
                "tag": tag,
                "type": sec_type,
                "start_time": s_start,
                "end_time": s_end,
                "lines": [],
                "cues": cues
            })
            continue

        sec_start, sec_end = sec_intervals[sec_idx]
        sec_idx += 1
        sec_dur = max(0.1, sec_end - sec_start)

        contained_segs = [seg for seg in segments if seg[0] >= sec_start - 0.25 and seg[1] <= sec_end + 0.25]

        line_weights = [max(1, len(l["text"])) for l in lines]
        tot_l_weight = sum(line_weights) if line_weights else 1

        aligned_lines = []

        if len(contained_segs) == len(lines):
            for j, l_item in enumerate(lines):
                c_start, c_end = contained_segs[j]
                aligned_lines.append({
                    "text": l_item["text"],
                    "start_time": round(c_start, 2),
                    "end_time": round(c_end, 2),
                    "is_adlib": l_item.get("is_adlib", False),
                    "raw": l_item.get("raw", "")
                })
        elif len(contained_segs) > len(lines):
            # Optimal phrase clustering: find top (len(lines) - 1) gaps to partition contained_segs into len(lines) phrases
            k_lines = len(lines)
            n_segs = len(contained_segs)
            
            # Gaps between adjacent contained segments
            int_gaps = []
            for g_i in range(n_segs - 1):
                int_gaps.append({
                    "idx": g_i,
                    "gap": contained_segs[g_i+1][0] - contained_segs[g_i][1]
                })
            
            # Top (k_lines - 1) gaps determine partition points
            sorted_gaps = sorted(int_gaps, key=lambda x: x["gap"], reverse=True)
            cut_indices = sorted([g["idx"] for g in sorted_gaps[:k_lines - 1]])
            
            # Build partitions
            groups = []
            start_idx = 0
            for cut_idx in cut_indices:
                groups.append(contained_segs[start_idx : cut_idx + 1])
                start_idx = cut_idx + 1
            groups.append(contained_segs[start_idx:])
            
            for j, l_item in enumerate(lines):
                grp = groups[j]
                grp_start = grp[0][0]
                grp_end = grp[-1][1]
                aligned_lines.append({
                    "text": l_item["text"],
                    "start_time": round(grp_start, 2),
                    "end_time": round(grp_end, 2),
                    "is_adlib": l_item.get("is_adlib", False),
                    "raw": l_item.get("raw", "")
                })
        elif len(contained_segs) > 0 and len(contained_segs) < len(lines):
            # Map lines across contained sub-segments
            tot_l = len(lines)
            num_sub = len(contained_segs)
            base_cnt = tot_l // num_sub
            rem = tot_l % num_sub
            l_counts = [base_cnt + (1 if k < rem else 0) for k in range(num_sub)]
            pos = 0
            for k, seg in enumerate(contained_segs):
                c = l_counts[k]
                sub_lines = lines[pos:pos+c]
                pos += c
                dur = seg[1] - seg[0]
                l_dur = dur / max(1, c)
                for m, l_item in enumerate(sub_lines):
                    ls = seg[0] + m * l_dur
                    le = ls + l_dur
                    aligned_lines.append({
                        "text": l_item["text"],
                        "start_time": round(ls, 2),
                        "end_time": round(le, 2),
                        "is_adlib": l_item.get("is_adlib", False),
                        "raw": l_item.get("raw", "")
                    })
        else:
            l_dur = sec_dur / max(1, len(lines))
            for j, l_item in enumerate(lines):
                ls = sec_start + j * l_dur
                le = ls + l_dur
                aligned_lines.append({
                    "text": l_item["text"],
                    "start_time": round(ls, 2),
                    "end_time": round(le, 2),
                    "is_adlib": l_item.get("is_adlib", False),
                    "raw": l_item.get("raw", "")
                })

        aligned_section = {
            "tag": tag,
            "type": sec_type,
            "start_time": round(sec_start, 2),
            "end_time": round(sec_end, 2),
            "lines": aligned_lines,
            "cues": cues
        }
        aligned_sections.append(aligned_section)

    return {
        "audio_file": os.path.basename(audio_path),
        "audio_duration_seconds": round(duration, 2),
        "total_sections": len(aligned_sections),
        "sections": aligned_sections
    }


def main():
    parser = argparse.ArgumentParser(description="Acoustic-guided AI Vocal Lyrics Aligner")
    parser.add_argument("--audio", required=True, help="Path to vocal WAV file")
    parser.add_argument("--lyrics", required=True, help="Path to prompt markdown file or parsed JSON")
    parser.add_argument("--output-lrc", required=False, help="Path to output .lrc file")
    parser.add_argument("--output-srt", required=False, help="Path to output .srt file")
    parser.add_argument("--output-markers", required=False, help="Path to output DAW marker .csv file")
    parser.add_argument("--output-json", required=False, help="Path to output aligned json")
    parser.add_argument("--title", required=False, default="", help="Song title for LRC metadata")
    parser.add_argument("--artist", required=False, default="", help="Artist name for LRC metadata")
    args = parser.parse_args()

    if not os.path.exists(args.audio):
        raise FileNotFoundError(f"Audio file not found: {args.audio}")

    if not os.path.exists(args.lyrics):
        raise FileNotFoundError(f"Lyrics file not found: {args.lyrics}")

    # Load or extract lyrics
    if args.lyrics.endswith(".json"):
        with open(args.lyrics, "r", encoding="utf-8") as f:
            lyrics_data = json.load(f)
    else:
        with open(args.lyrics, "r", encoding="utf-8") as f:
            content = f.read()
        lyrics_data = extract_lyrics_from_markdown(content)

    aligned_result = align_lyrics_with_vocal_track(lyrics_data, args.audio)

    meta = {}
    if args.title:
        meta["ti"] = args.title
    if args.artist:
        meta["ar"] = args.artist

    if args.output_lrc:
        lrc_text = lrc_formatter.generate_standard_lrc(aligned_result, meta)
        with open(args.output_lrc, "w", encoding="utf-8") as f:
            f.write(lrc_text)
        print(f"Generated standard LRC -> {args.output_lrc}")

    if args.output_srt:
        srt_text = lrc_formatter.generate_srt(aligned_result)
        with open(args.output_srt, "w", encoding="utf-8") as f:
            f.write(srt_text)
        print(f"Generated SRT subtitles -> {args.output_srt}")

    if args.output_markers:
        csv_text = lrc_formatter.generate_daw_marker_csv(aligned_result)
        with open(args.output_markers, "w", encoding="utf-8") as f:
            f.write(csv_text)
        print(f"Generated DAW marker CSV -> {args.output_markers}")

    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(aligned_result, f, ensure_ascii=False, indent=2)
        print(f"Generated aligned JSON -> {args.output_json}")


if __name__ == "__main__":
    main()
