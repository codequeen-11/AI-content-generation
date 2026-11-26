"""
Stage 2: Narration Generation & Radio Cut Assembly.
Generates line-by-line speech audio for each shot in authentic AMHARIC
using Gemini Flash-Lite TTS with Edge-TTS (am-ET-MekdesNeural) neural voice fallback,
while keeping English subtitles intact.
"""
import asyncio
import base64
import json
import math
import os
import struct
import subprocess
import time
import wave
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Optional

import requests
import edge_tts

from pipeline.config import (
    STORYBOARD_PATH,
    NARRATION_DIR,
    ASSEMBLY_DIR,
    GEMINI_API_KEY,
    get_ffmpeg_bin
)
from pipeline.logger import audit_logger
from pipeline.cache import CacheManager


def generate_silence_wav(path: Path, duration_sec: float, sample_rate: int = 24000):
    """Creates a clean PCM WAV silence file of exact duration."""
    num_samples = int(duration_sec * sample_rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_samples)


def pad_or_trim_wav(raw_wav_bytes: bytes, target_path: Path, target_duration_sec: float):
    """Adjusts speech audio file duration to match shot duration with natural trailing silence."""
    with wave.open(BytesIO(raw_wav_bytes), "rb") as in_wf:
        sample_rate = in_wf.getframerate()
        channels = in_wf.getnchannels()
        sampwidth = in_wf.getsampwidth()
        frames = in_wf.readframes(in_wf.getnframes())

    current_samples = len(frames) // (channels * sampwidth)
    target_samples = int(target_duration_sec * sample_rate)

    if current_samples < target_samples:
        padding = b"\x00" * ((target_samples - current_samples) * channels * sampwidth)
        final_frames = frames + padding
    else:
        final_frames = frames[: target_samples * channels * sampwidth]

    with wave.open(str(target_path), "wb") as out_wf:
        out_wf.setnchannels(channels)
        out_wf.setsampwidth(sampwidth)
        out_wf.setframerate(sample_rate)
        out_wf.writeframes(final_frames)


def generate_edge_amharic_tts(text: str, target_path: Path, target_duration_sec: float, retries: int = 3) -> bool:
    """
    Generates natural human Amharic speech using Edge Neural Voice (am-ET-MekdesNeural).
    Single consistent Ethiopian lady voice across all segments with zero interruption and natural decay.
    """
    temp_mp3 = target_path.with_suffix(".tmp.mp3")
    
    async def _render():
        communicate = edge_tts.Communicate(text.strip(), "am-ET-MekdesNeural", rate="+0%")
        await communicate.save(str(temp_mp3))
        
    for attempt in range(retries):
        try:
            asyncio.run(_render())
            if temp_mp3.exists() and temp_mp3.stat().st_size > 1000:
                break
            time.sleep(1.5)
        except Exception as e:
            print(f"    [Edge TTS Mekdes Retry {attempt+1}] {e}")
            time.sleep(2.0)
            
    if not temp_mp3.exists():
        return False
        
    try:
        ffmpeg_bin = get_ffmpeg_bin()
        ffprobe = ffmpeg_bin.replace("ffmpeg.exe", "ffprobe.exe")
        
        # Probe exact spoken length
        probe_cmd = [
            ffprobe, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(temp_mp3)
        ]
        out = subprocess.check_output(probe_cmd).decode().strip()
        spoken_dur = float(out)
        
        # Ensure at least 0.8s headroom for natural music breathing and zero interruption
        min_headroom = 0.8
        max_allowed_voice = target_duration_sec - min_headroom
        
        if spoken_dur > max_allowed_voice:
            tempo = spoken_dur / max_allowed_voice
            tempo = min(max(tempo, 1.0), 1.20)
            af = f"atempo={tempo:.3f},apad=whole_dur={target_duration_sec}"
        else:
            af = f"apad=whole_dur={target_duration_sec}"
            
        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(temp_mp3),
            "-af", af,
            "-t", str(target_duration_sec),
            "-ar", "24000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            str(target_path)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return res.returncode == 0
    except Exception as e:
        print(f"    [FFmpeg Speech Process Error] {e}")
        return False
    finally:
        if temp_mp3.exists():
            temp_mp3.unlink()


def generate_narration_for_shots(storyboard: dict, force: bool = False) -> Dict[int, Path]:
    """Generates authentic Amharic spoken audio for every shot using exclusively MekdesNeural."""
    audio_paths = {}
    shots = storyboard["shots"]
    
    print(f"\n[Stage 2] Generating single consistent lady voice (am-ET-MekdesNeural) for {len(shots)} shots...")
    
    for shot in shots:
        shot_id = shot["id"]
        text = shot.get("narration_text", "").strip()
        duration = shot["duration_sec"]
        
        # Cache key ensures fresh consistent single-voice generation
        input_data = {
            "shot_id": shot_id,
            "text": text,
            "duration_sec": duration,
            "language": "am-ET",
            "voice": "am-ET-MekdesNeural-exclusive-v3"
        }
        
        target_path, input_hash, is_cached = CacheManager.get_artifact(
            stage_dir=NARRATION_DIR,
            prefix=f"shot_{shot_id:02d}",
            input_data=input_data,
            extension="wav"
        )
        
        if is_cached and not force:
            audit_logger.log_run(
                stage="stage2_narration",
                model="amharic-lady-mekdes",
                parameters=input_data,
                seed=shot.get("seed"),
                latency_sec=0.001,
                cached=True,
                status="success",
                output_path=str(target_path)
            )
            print(f"  - Shot {shot_id:02d}: [CACHED MEKDES] {target_path.name}")
            audio_paths[shot_id] = target_path
            continue
            
        t0 = time.time()
        success = False
        model_name = "amharic-lady-mekdes"
        
        if not text:
            generate_silence_wav(target_path, duration_sec=duration)
            success = True
            model_name = "pcm_silence_generator"
        else:
            # Exclusively use am-ET-MekdesNeural for a single, consistent, smooth lady voice
            success = generate_edge_amharic_tts(text, target_path, duration)
            if not success:
                # Retry once if transient network jitter
                time.sleep(2.0)
                success = generate_edge_amharic_tts(text, target_path, duration)
                
        latency = time.time() - t0
        audit_logger.log_run(
            stage="stage2_narration",
            model=model_name,
            parameters=input_data,
            seed=shot.get("seed"),
            latency_sec=latency,
            cached=False,
            status="success" if success else "error",
            output_path=str(target_path)
        )
        print(f"  - Shot {shot_id:02d}: [MEKDES SPOKEN] ({latency:.2f}s) -> {target_path.name}")
        audio_paths[shot_id] = target_path
        time.sleep(0.5)
        
    return audio_paths
        
    return audio_paths


def assemble_radio_cut(storyboard: dict, audio_paths: Dict[int, Path]) -> Path:
    """Concatenates all shot audio files into outputs/assembly/radio_cut.wav."""
    radio_cut_path = ASSEMBLY_DIR / "radio_cut.wav"
    print(f"\n[Stage 2] Assembling Radio Cut -> {radio_cut_path.name}...")
    
    total_frames = bytearray()
    sample_rate = 24000
    channels = 1
    sampwidth = 2
    
    for shot in storyboard["shots"]:
        path = audio_paths[shot["id"]]
        with wave.open(str(path), "rb") as wf:
            sample_rate = wf.getframerate()
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            total_frames.extend(wf.readframes(wf.getnframes()))
            
    with wave.open(str(radio_cut_path), "wb") as out_wf:
        out_wf.setnchannels(channels)
        out_wf.setsampwidth(sampwidth)
        out_wf.setframerate(sample_rate)
        out_wf.writeframes(total_frames)
        
    total_sec = len(total_frames) / (sample_rate * channels * sampwidth)
    print(f"[Stage 2] Amharic Radio Cut compiled successfully! Total duration: {total_sec:.2f} seconds.")
    return radio_cut_path


if __name__ == "__main__":
    with open(STORYBOARD_PATH, "r", encoding="utf-8") as f:
        sb = json.load(f)
    paths = generate_narration_for_shots(sb)
    assemble_radio_cut(sb, paths)
