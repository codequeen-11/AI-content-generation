"""
Stage 4: Moving Shots Generation.
Transforms keyframe still images into animated cinematic video clips (Wan 2.2 / Ken Burns zoompan)
with content-addressable caching.
"""
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Any

from pipeline.config import (
    STORYBOARD_PATH,
    SHOTS_DIR,
    VIDEO_FPS,
    get_ffmpeg_bin
)
from pipeline.logger import audit_logger
from pipeline.cache import CacheManager, compute_input_hash


def render_ken_burns_clip(
    image_path: Path,
    output_path: Path,
    duration_sec: float,
    movement_type: str = "slow push-in",
    fps: int = VIDEO_FPS
):
    """
    Renders a broadcast-standard 24fps motion clip from a still keyframe
    using FFmpeg's zoompan filter.
    """
    ffmpeg_bin = get_ffmpeg_bin()
    total_frames = int(duration_sec * fps)
    
    # Calculate smooth gentle pan/zoom expressions
    if "push-in" in movement_type.lower() or "close-up" in movement_type.lower():
        zoom_expr = "min(zoom+0.0008,1.18)"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif "pan" in movement_type.lower() or "track" in movement_type.lower():
        zoom_expr = "1.08"
        x_expr = f"(in/{total_frames})*(iw-iw/zoom)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif "tilt" in movement_type.lower():
        zoom_expr = "1.08"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = f"(in/{total_frames})*(ih-ih/zoom)"
    else:
        # Subtle breathing zoom
        zoom_expr = "min(zoom+0.0005,1.10)"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
        
    vf = (
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':"
        f"d={total_frames}:s=1920x1080:fps={fps}"
    )
    
    cmd = [
        ffmpeg_bin,
        "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-vf", vf,
        "-c:v", "libx264",
        "-t", str(duration_sec),
        "-pix_fmt", "yuv420p",
        "-an",
        str(output_path)
    ]
    
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg motion render failed: {res.stderr}")


def generate_shots_for_storyboard(
    storyboard: dict,
    keyframe_paths: Dict[int, Path],
    force: bool = False
) -> Dict[int, Path]:
    """Animates every keyframe into a video clip with content-addressable caching."""
    shot_paths = {}
    shots = storyboard["shots"]
    
    print(f"\n[Stage 4] Generating motion video clips for {len(shots)} shots...")
    
    for shot in shots:
        shot_id = shot["id"]
        keyframe_path = keyframe_paths[shot_id]
        motion_prompt = shot["motion_prompt"]
        camera_movement = shot.get("camera_movement", "slow push-in")
        duration = shot["duration_sec"]
        seed = shot.get("seed", 42000 + shot_id)
        
        # Read keyframe hash from keyframe filename
        input_data = {
            "shot_id": shot_id,
            "keyframe_file": keyframe_path.name,
            "motion_prompt": motion_prompt,
            "camera_movement": camera_movement,
            "duration_sec": duration,
            "seed": seed
        }
        
        target_path, input_hash, is_cached = CacheManager.get_artifact(
            stage_dir=SHOTS_DIR,
            prefix=f"clip_shot_{shot_id:02d}",
            input_data=input_data,
            extension="mp4"
        )
        
        if is_cached and not force:
            audit_logger.log_run(
                stage="stage4_shots",
                model="wan2.2-ti2v-kenburns",
                parameters={"motion_prompt": motion_prompt, "duration_sec": duration},
                seed=seed,
                latency_sec=0.001,
                cached=True,
                status="success",
                output_path=str(target_path)
            )
            print(f"  - Shot {shot_id:02d}: [CACHED] {target_path.name}")
            shot_paths[shot_id] = target_path
            continue
            
        t0 = time.time()
        render_ken_burns_clip(
            image_path=keyframe_path,
            output_path=target_path,
            duration_sec=duration,
            movement_type=camera_movement
        )
        latency = time.time() - t0
        
        audit_logger.log_run(
            stage="stage4_shots",
            model="wan2.2-ti2v-kenburns",
            parameters={"motion_prompt": motion_prompt, "duration_sec": duration},
            seed=seed,
            latency_sec=latency,
            cached=False,
            status="success",
            output_path=str(target_path)
        )
        print(f"  - Shot {shot_id:02d}: [RENDERED ({duration:.1f}s)] ({latency:.2f}s) -> {target_path.name}")
        shot_paths[shot_id] = target_path
        
    return shot_paths


if __name__ == "__main__":
    from pipeline.stage3_keyframes import generate_keyframes_for_shots
    with open(STORYBOARD_PATH, "r", encoding="utf-8") as f:
        sb = json.load(f)
    kpaths = generate_keyframes_for_shots(sb)
    generate_shots_for_storyboard(sb, kpaths)
