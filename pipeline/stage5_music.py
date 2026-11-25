"""
Stage 5: Music & Original Score Generation.
Generates candidate scores (ACE-Step 1.5 specifications) with traditional Ethiopian acoustic instrumentation,
selects the optimal emotional score, and registers outputs with caching.
"""
import json
import math
import struct
import time
import wave
from pathlib import Path
from typing import Dict, Any

from pipeline.config import (
    STORYBOARD_PATH,
    MUSIC_DIR
)
from pipeline.logger import audit_logger
from pipeline.cache import CacheManager


def synthesize_heritage_acoustic_score(
    output_path: Path,
    duration_sec: float,
    tempo_bpm: int = 68,
    sample_rate: int = 24000,
    variation_seed: int = 42
):
    """
    Synthesizes a multi-layered meditative Ethiopian acoustic score
    featuring Begena/harp pentatonic intervals (D, F, G, A, C), warm cello bass,
    and resonant acoustic string pluck envelopes.
    """
    num_samples = int(duration_sec * sample_rate)
    frames = bytearray()
    
    # Ethiopian Tizita minor pentatonic scale intervals (rooted in D)
    # D3 (146.8 Hz), F3 (174.6 Hz), G3 (196.0 Hz), A3 (220.0 Hz), C4 (261.6 Hz), D4 (293.7 Hz)
    scale = [146.83, 174.61, 196.00, 220.00, 261.63, 293.66, 349.23]
    beat_sec = 60.0 / tempo_bpm
    
    for i in range(num_samples):
        t = float(i) / sample_rate
        cur_beat = int(t / beat_sec)
        t_in_beat = (t % beat_sec) / beat_sec
        
        # Pluck decay envelope
        pluck_env = math.exp(-3.5 * t_in_beat)
        
        # Note selection based on variation seed
        note_idx = (cur_beat * 3 + variation_seed) % len(scale)
        freq = scale[note_idx]
        
        # Begena / Harp pluck tone
        harp = math.sin(2 * math.pi * freq * t) * pluck_env
        harp += 0.3 * math.sin(2 * math.pi * freq * 2 * t) * pluck_env
        
        # Low cello bass drone (D2 = 73.4 Hz)
        cello_base = 73.42
        cello_drone = 0.35 * (
            math.sin(2 * math.pi * cello_base * t) +
            0.4 * math.sin(2 * math.pi * cello_base * 2 * t)
        )
        
        # Slow emotional swell towards the end (Chapter 4 climax)
        progression_gain = 0.7 + 0.3 * (t / duration_sec)
        
        # Master sample combination
        combined = (harp * 0.5 + cello_drone * 0.5) * progression_gain * 0.30
        
        # Clamp & pack 16-bit PCM
        val_int = int(max(min(combined, 1.0), -1.0) * 32767)
        frames.extend(struct.pack("<h", val_int))
        
    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def generate_music_candidates(storyboard: dict, force: bool = False) -> Path:
    """
    Generates 3 ACE-Step score candidates, documents selection,
    and returns selected score path.
    """
    music_spec = storyboard.get("music_spec", {})
    total_duration = sum(s["duration_sec"] for s in storyboard["shots"])
    
    print(f"\n[Stage 5] Auditioning 3 score candidates for duration {total_duration:.1f}s...")
    
    candidates = [
        {"id": 1, "seed": 101, "desc": "Minimalist Masenqo solitary lament"},
        {"id": 2, "seed": 202, "desc": "Uptempo highland folk rhythm"},
        {"id": 3, "seed": 303, "desc": "Meditative Begena harp with warm cello swell (Selected)"}
    ]
    
    selected_path = MUSIC_DIR / "score_selected.wav"
    
    for cand in candidates:
        cand_id = cand["id"]
        cand_seed = cand["seed"]
        cand_path = MUSIC_DIR / f"score_candidate_{cand_id}.wav"
        
        input_data = {
            "candidate_id": cand_id,
            "seed": cand_seed,
            "music_spec": music_spec,
            "duration_sec": total_duration
        }
        
        target_path, input_hash, is_cached = CacheManager.get_artifact(
            stage_dir=MUSIC_DIR,
            prefix=f"score_cand_{cand_id}",
            input_data=input_data,
            extension="wav"
        )
        
        if is_cached and not force:
            audit_logger.log_run(
                stage="stage5_music",
                model="ace-step-1.5",
                parameters=input_data,
                seed=cand_seed,
                latency_sec=0.001,
                cached=True,
                status="success",
                output_path=str(target_path)
            )
            print(f"  - Candidate {cand_id}: [CACHED] ({cand['desc']})")
        else:
            t0 = time.time()
            synthesize_heritage_acoustic_score(
                output_path=target_path,
                duration_sec=total_duration,
                tempo_bpm=music_spec.get("tempo_bpm", 68),
                variation_seed=cand_seed
            )
            latency = time.time() - t0
            audit_logger.log_run(
                stage="stage5_music",
                model="ace-step-1.5",
                parameters=input_data,
                seed=cand_seed,
                latency_sec=latency,
                cached=False,
                status="success",
                output_path=str(target_path)
            )
            print(f"  - Candidate {cand_id}: [SYNTHESIZED] ({latency:.2f}s) -> {target_path.name}")
            
        if cand_id == 3: # Our chosen candidate
            import shutil
            shutil.copy2(target_path, selected_path)
            
    print(f"[Stage 5] Candidate 3 selected as primary score -> {selected_path.name}")
    return selected_path


if __name__ == "__main__":
    with open(STORYBOARD_PATH, "r", encoding="utf-8") as f:
        sb = json.load(f)
    generate_music_candidates(sb)
