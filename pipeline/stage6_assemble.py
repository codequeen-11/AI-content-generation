"""
Stage 6: Programmatic Video Assembly & Delivery.
Executes FFmpeg compositing:
- Subtitle generation and burn-in
- Dynamic sidechain audio ducking
- EBU R128 loudness normalisation (-14 LUFS)
- Dual-aspect rendering: 16:9 (Horizontal) and 9:16 (Vertical)
"""
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List

from pipeline.config import (
    STORYBOARD_PATH,
    ASSEMBLY_DIR,
    EXPORTS_DIR,
    VIDEO_FPS,
    TARGET_LUFS,
    LRA,
    TRUE_PEAK,
    DUCKING_THRESHOLD,
    DUCKING_RATIO,
    DUCKING_ATTACK_MS,
    DUCKING_RELEASE_MS,
    get_ffmpeg_bin
)
from pipeline.logger import audit_logger


def format_srt_time(seconds: float) -> str:
    """Converts seconds into SRT timestamp format HH:MM:SS,mmm"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def format_ass_time(seconds: float) -> str:
    """Converts seconds into ASS timestamp format H:MM:SS.cc"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        secs += 1
        centis = 0
    return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"


def generate_subtitles_ass(storyboard: dict, output_path: Path, aspect_ratio: str = "16:9") -> Path:
    """Generates broadcast-grade ASS subtitle file with precise aspect-ratio metrics and bottom positioning."""
    shots = storyboard["shots"]
    current_time = 0.0
    
    if aspect_ratio == "9:16":
        res_x, res_y = 1080, 1920
        font_size = 50
        outline = 4.0
        shadow = 2.0
        margin_v = 260
        margin_lr = 70
    else:
        res_x, res_y = 1920, 1080
        font_size = 42
        outline = 3.5
        shadow = 2.0
        margin_v = 70
        margin_lr = 100
        
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {res_x}
PlayResY: {res_y}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,{outline},{shadow},2,{margin_lr},{margin_lr},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    dialogues = []
    for shot in shots:
        start_t = current_time
        duration = shot["duration_sec"]
        end_t = current_time + duration
        current_time = end_t
        
        text = shot.get("subtitles_text", "").strip()
        if not text:
            continue
        clean_text = text.replace("\n", "\\N")
        dialogues.append(
            f"Dialogue: 0,{format_ass_time(start_t)},{format_ass_time(end_t)},Default,,0,0,0,,{clean_text}"
        )
        
    full_ass = header + "\n".join(dialogues) + "\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_ass)
        
    print(f"[Stage 6] Generated ASS subtitle file ({aspect_ratio}) -> {output_path.name}")
    return output_path


def generate_subtitles_srt(storyboard: dict, output_path: Path) -> Path:
    """Creates a standards-compliant SRT subtitle file from storyboard cues."""
    shots = storyboard["shots"]
    current_time = 0.0
    srt_lines = []
    
    sub_index = 1
    for shot in shots:
        start_t = current_time
        duration = shot["duration_sec"]
        end_t = current_time + duration
        current_time = end_t
        
        text = shot.get("subtitles_text", "").strip()
        if not text:
            continue
            
        srt_lines.append(f"{sub_index}")
        srt_lines.append(f"{format_srt_time(start_t)} --> {format_srt_time(end_t)}")
        srt_lines.append(text)
        srt_lines.append("")
        sub_index += 1
        
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))
        
    print(f"[Stage 6] Generated subtitle file with {sub_index - 1} cues -> {output_path.name}")
    return output_path


def concatenate_video_shots(shot_paths: Dict[int, Path], output_path: Path) -> Path:
    """Concatenates all shot video clips into a single continuous video reel."""
    ffmpeg_bin = get_ffmpeg_bin()
    concat_list_path = ASSEMBLY_DIR / "concat_shots.txt"
    
    sorted_ids = sorted(shot_paths.keys())
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for sid in sorted_ids:
            # Forward slashes for FFmpeg compatibility
            fpath = str(shot_paths[sid]).replace("\\", "/")
            f.write(f"file '{fpath}'\n")
            
    cmd = [
        ffmpeg_bin,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_path),
        "-c", "copy",
        str(output_path)
    ]
    
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg video concatenation failed: {res.stderr}")
        
    print(f"[Stage 6] Video reel joined -> {output_path.name}")
    return output_path


def mix_and_duck_audio(voice_path: Path, score_path: Path, output_path: Path) -> Path:
    """
    Applies sidechain audio ducking and loudness normalisation to master soundtrack.
    """
    ffmpeg_bin = get_ffmpeg_bin()
    
    # Filtergraph:
    # 1. Voice in [1:a] triggers compressor on score [0:a]
    # 2. Mixes ducked score and voice together
    # 3. Applies EBU R128 loudness normalisation (-14 LUFS)
    filter_complex = (
        f"[0:a][1:a]sidechaincompress="
        f"threshold={DUCKING_THRESHOLD}:ratio={DUCKING_RATIO}:"
        f"attack={DUCKING_ATTACK_MS}:release={DUCKING_RELEASE_MS}[ducked_music];"
        f"[ducked_music][1:a]amix=inputs=2:duration=longest:weights=0.35 1.7[mixed];"
        f"[mixed]loudnorm=I={TARGET_LUFS}:LRA={LRA}:TP={TRUE_PEAK}[master_audio]"
    )
    
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", str(score_path),
        "-i", str(voice_path),
        "-filter_complex", filter_complex,
        "-map", "[master_audio]",
        "-c:a", "pcm_s16le",
        str(output_path)
    ]
    
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg audio ducking/mixing failed: {res.stderr}")
        
    print(f"[Stage 6] Audio mix & ducking complete -> {output_path.name}")
    return output_path


def export_aspect_ratio_film(
    video_path: Path,
    audio_path: Path,
    sub_path: Path,
    output_path: Path,
    aspect_ratio: str = "16:9"
) -> Path:
    """
    Assembles final deliverables in specified aspect ratio (16:9 or 9:16) with burned-in subtitles.
    For 9:16, employs broadcast-grade ambient reframe so 100% of the cinematic 16:9 scene
    remains visible with elegant bottom-aligned subtitles.
    """
    ffmpeg_bin = get_ffmpeg_bin()
    escaped_sub = str(sub_path).replace("\\", "/").replace(":", "\\:")
    
    if aspect_ratio == "9:16":
        # Cinematic ambient-blur vertical layout:
        # Full 16:9 foreground video centered at y=560 (1080x608),
        # ambient softly blurred and darkened background filling 1080x1920,
        # and subtitles positioned in bottom safe zone with zero visual obstruction.
        vf = (
            f"[0:v]split[bg][fg];"
            f"[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:25,eq=brightness=-0.15[bg_blur];"
            f"[fg]scale=1080:608[fg_scaled];"
            f"[bg_blur][fg_scaled]overlay=0:560,"
            f"subtitles='{escaped_sub}'"
        )
    else: # 16:9
        vf = (
            f"scale=1920:1080,"
            f"subtitles='{escaped_sub}'"
        )
        
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-shortest",
        str(output_path)
    ]
    
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        # Fallback without subtitle filter if fontconfig error
        print(f"  [Notice] Retrying without filter overlay: {res.stderr[:100]}...")
        vf_plain = "scale=1920:1080" if aspect_ratio == "16:9" else "[0:v]split[bg][fg];[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:25,eq=brightness=-0.15[bg_blur];[fg]scale=1080:608[fg_scaled];[bg_blur][fg_scaled]overlay=0:560"
        cmd[cmd.index("-vf") + 1] = vf_plain
        res_plain = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res_plain.returncode != 0:
            raise RuntimeError(f"FFmpeg export failed: {res_plain.stderr}")
            
    print(f"[Stage 6] Exported {aspect_ratio} short film -> {output_path.name}")
    return output_path


def assemble_final_film(
    storyboard: dict,
    shot_paths: Dict[int, Path],
    voice_path: Path,
    score_path: Path
) -> Dict[str, Path]:
    """Runs full Stage 6 assembly pipeline and outputs 16:9 and 9:16 films."""
    import shutil
    t0 = time.time()
    print("\n[Stage 6] Commencing master assembly...")
    
    # 1. Generate subtitle assets (both SRT and format-specific ASS)
    srt_path = ASSEMBLY_DIR / "subtitles.srt"
    generate_subtitles_srt(storyboard, srt_path)
    
    ass_16x9 = ASSEMBLY_DIR / "subtitles_16x9.ass"
    ass_9x16 = ASSEMBLY_DIR / "subtitles_9x16.ass"
    generate_subtitles_ass(storyboard, ass_16x9, "16:9")
    generate_subtitles_ass(storyboard, ass_9x16, "9:16")
    
    # 2. Join video reel
    video_reel_path = ASSEMBLY_DIR / "video_reel.mp4"
    concatenate_video_shots(shot_paths, video_reel_path)
    
    # 3. Audio mix & ducking
    mixed_audio_path = ASSEMBLY_DIR / "master_soundtrack.wav"
    mix_and_duck_audio(voice_path, score_path, mixed_audio_path)
    
    # 4. Master exports (with faststart and ambient 9:16 framing)
    export_16x9 = EXPORTS_DIR / "film_16x9_heritage_short.mp4"
    export_9x16 = EXPORTS_DIR / "film_9x16_heritage_short.mp4"
    
    export_aspect_ratio_film(video_reel_path, mixed_audio_path, ass_16x9, export_16x9, "16:9")
    export_aspect_ratio_film(video_reel_path, mixed_audio_path, ass_9x16, export_9x16, "9:16")
    
    # 5. Mirror to user Downloads folder for convenience
    downloads_dir = Path("C:/Users/pc/Downloads")
    if downloads_dir.exists():
        try:
            shutil.copy2(export_16x9, downloads_dir / export_16x9.name)
            shutil.copy2(export_9x16, downloads_dir / export_9x16.name)
            print(f"[Stage 6] Synced latest exports to {downloads_dir}")
        except Exception as e:
            print(f"[Stage 6] Note: could not mirror to Downloads: {e}")
            
    latency = time.time() - t0
    audit_logger.log_run(
        stage="stage6_assemble",
        model="ffmpeg-assembler",
        parameters={
            "aspect_ratios": ["16:9", "9:16"],
            "target_lufs": TARGET_LUFS,
            "ducking_attack_ms": DUCKING_ATTACK_MS
        },
        seed=None,
        latency_sec=latency,
        cached=False,
        status="success",
        output_path=str(export_16x9)
    )
    print(f"\n[Stage 6] Assembly Complete! Finished in {latency:.2f}s.")
    return {"16:9": export_16x9, "9:16": export_9x16}
