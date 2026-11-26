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


def generate_edge_amharic_tts(text: str, target_path: Path, target_duration_sec: float) -> bool:
    """
    Generates natural human Amharic speech using Edge Neural Voice (am-ET-MekdesNeural).
    Zero quota limits, broadcast-grade pronunciation.
    """
    temp_mp3 = target_path.with_suffix(".tmp.mp3")
    
    async def _render():
        communicate = edge_tts.Communicate(text.strip(), "am-ET-MekdesNeural", rate="-4%")
        await communicate.save(str(temp_mp3))
        
    try:
        asyncio.run(_render())
        ffmpeg_bin = get_ffmpeg_bin()
        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(temp_mp3),
            "-af", f"apad=whole_dur={target_duration_sec}",
            "-t", str(target_duration_sec),
            "-ar", "24000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            str(target_path)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if temp_mp3.exists():
            temp_mp3.unlink()
        return res.returncode == 0
    except Exception as e:
        print(f"    [Edge TTS Amharic Error] {e}")
        if temp_mp3.exists():
            temp_mp3.unlink()
        return False


def call_gemini_amharic_tts(
    clean_text: str,
    target_path: Path,
    target_duration: float,
    api_key: str
) -> tuple[bool, str]:
    """
    Calls Gemini Flash-Lite TTS endpoint with pure Amharic text.
    """
    if not api_key:
        return False, ""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash-lite-tts:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": clean_text.strip()}]}]
    }

    try:
        resp = requests.post(url, json=payload, timeout=25)
        if resp.status_code == 200:
            res_json = resp.json()
            candidates = res_json.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    if "inlineData" in part and part["inlineData"].get("data"):
                        audio_bytes = base64.b64decode(part["inlineData"]["data"])
                        pad_or_trim_wav(audio_bytes, target_path, target_duration)
                        return True, "gemini-3.8-flash-lite-tts"
        return False, ""
    except Exception:
        return False, ""


def generate_narration_for_shots(storyboard: dict, force: bool = False) -> Dict[int, Path]:
    """Generates authentic Amharic spoken audio for every shot in storyboard."""
    audio_paths = {}
    shots = storyboard["shots"]
    
    print(f"\n[Stage 2] Generating authentic AMHARIC spoken narration for {len(shots)} shots...")
    
    for shot in shots:
        shot_id = shot["id"]
        text = shot.get("narration_text", "").strip()
        duration = shot["duration_sec"]
        
        # input_data defines cache key - v6-amharic ensures fresh Amharic renders
        input_data = {
            "shot_id": shot_id,
            "text": text,
            "duration_sec": duration,
            "language": "am-ET",
            "model": "amharic-neural-v6"
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
                model="amharic-tts-engine",
                parameters=input_data,
                seed=shot.get("seed"),
                latency_sec=0.001,
                cached=True,
                status="success",
                output_path=str(target_path)
            )
            print(f"  - Shot {shot_id:02d}: [CACHED AMHARIC] {target_path.name}")
            audio_paths[shot_id] = target_path
            continue
            
        t0 = time.time()
        success = False
        model_name = "gemini-3.8-flash-lite-tts"
        
        if not text:
            generate_silence_wav(target_path, duration_sec=duration)
            success = True
            model_name = "pcm_silence_generator"
        else:
            if GEMINI_API_KEY:
                success, model_used = call_gemini_amharic_tts(text, target_path, duration, GEMINI_API_KEY)
                if success:
                    model_name = model_used
                    time.sleep(2.0)
                
            if not success:
                # Guaranteed native Amharic neural voice (am-ET-MekdesNeural)
                success = generate_edge_amharic_tts(text, target_path, duration)
                model_name = "amharic-neural-mekdes"
                
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
        print(f"  - Shot {shot_id:02d}: [AMHARIC SPOKEN ({model_name})] ({latency:.2f}s) -> {target_path.name}")
        audio_paths[shot_id] = target_path
        
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
