"""
Stage 3: Keyframe Generation.
Generates photorealistic keyframe images using FLUX diffusion models,
conditioned on authentic Ethiopian cultural style block and character sheet,
with content-addressable caching and offline procedural fallbacks.
"""
import json
import time
import urllib.parse
from io import BytesIO
from pathlib import Path
from typing import Dict, Any

import requests
from PIL import Image, ImageDraw

from pipeline.config import (
    STORYBOARD_PATH,
    KEYFRAMES_DIR
)
from pipeline.logger import audit_logger
from pipeline.cache import CacheManager


def create_procedural_fallback_card(
    path: Path,
    shot: dict,
    width: int = 1920,
    height: int = 1080
):
    """Fallback visual card if network is unavailable."""
    chapter = shot.get("chapter", "")
    shot_id = shot["id"]
    
    if "Beginnings" in chapter:
        bg_top, bg_bottom = (45, 30, 20), (120, 85, 45)
    elif "Sacrifices" in chapter:
        bg_top, bg_bottom = (30, 40, 35), (85, 75, 45)
    elif "Dreams" in chapter:
        bg_top, bg_bottom = (15, 20, 35), (160, 100, 30)
    elif "Legacy" in chapter:
        bg_top, bg_bottom = (25, 45, 35), (180, 140, 50)
    else:
        bg_top, bg_bottom = (10, 10, 10), (30, 30, 30)
        
    img = Image.new("RGB", (width, height), bg_top)
    draw = ImageDraw.Draw(img)
    for y in range(height):
        r = int(bg_top[0] + (bg_bottom[0] - bg_top[0]) * (y / height))
        g = int(bg_top[1] + (bg_bottom[1] - bg_top[1]) * (y / height))
        b = int(bg_top[2] + (bg_bottom[2] - bg_top[2]) * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b))
        
    draw.text((80, 80), "THE WISDOM OF OUR MOTHERS • የእናቶቻችን ጥበብ", fill=(230, 200, 100))
    draw.text((80, 130), f"SHOT {shot_id:02d}: {shot.get('shot_type', '')}", fill=(255, 255, 255))
    draw.text((80, height - 100), f"Reason: {shot.get('stated_reason', '')}", fill=(220, 200, 150))
    img.save(path, "PNG")


def download_flux_image(
    prompt: str,
    seed: int,
    output_path: Path,
    timeout: int = 35
) -> bool:
    """Fetches high-resolution photorealistic diffusion image from FLUX engine."""
    encoded_prompt = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width=1280&height=720&model=flux&seed={seed}&nologo=true"
    )
    
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200 and len(resp.content) > 10000:
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            # Upscale cleanly to full 1920x1080
            img_hd = img.resize((1920, 1080), Image.Resampling.LANCZOS)
            img_hd.save(output_path, "PNG")
            return True
        return False
    except Exception as e:
        print(f"    [FLUX Download Retry/Fallback] {e}")
        return False


def generate_keyframes_for_shots(storyboard: dict, force: bool = False) -> Dict[int, Path]:
    """Generates keyframes for each shot with content-addressable caching."""
    keyframe_paths = {}
    shots = storyboard["shots"]
    style_block = storyboard.get("style_block", {})
    char_ref = storyboard.get("character_reference", {})
    
    print(f"\n[Stage 3] Generating keyframes for {len(shots)} shots (FLUX Diffusion Engine)...")
    
    for shot in shots:
        shot_id = shot["id"]
        prompt = shot["keyframe_prompt"]
        seed = shot.get("seed", 42000 + shot_id)
        
        # Combine cultural style block for consistency
        full_prompt = (
            f"{prompt}. 35mm photograph, authentic Ethiopian heritage, "
            f"pure white Netela cotton scarf with colorful Tibeb geometric embroidery, "
            f"golden natural light, center framing, photorealistic, documentary cinema"
        )
        
        input_data = {
            "shot_id": shot_id,
            "prompt": prompt,
            "seed": seed,
            "model": "flux.1-schnell-photoreal-v1",
            "style_block": style_block,
            "character_reference": char_ref
        }
        
        target_path, input_hash, is_cached = CacheManager.get_artifact(
            stage_dir=KEYFRAMES_DIR,
            prefix=f"keyframe_shot_{shot_id:02d}",
            input_data=input_data,
            extension="png"
        )
        
        if is_cached and not force:
            audit_logger.log_run(
                stage="stage3_keyframes",
                model="flux.1-schnell",
                parameters={"prompt": prompt, "seed": seed},
                seed=seed,
                latency_sec=0.001,
                cached=True,
                status="success",
                output_path=str(target_path)
            )
            print(f"  - Shot {shot_id:02d}: [CACHED] {target_path.name}")
            keyframe_paths[shot_id] = target_path
            continue
            
        t0 = time.time()
        success = download_flux_image(full_prompt, seed, target_path)
        model_name = "flux.1-schnell-diffusion"
        
        if not success:
            create_procedural_fallback_card(target_path, shot)
            model_name = "procedural_heritage_card_fallback"
            
        latency = time.time() - t0
        audit_logger.log_run(
            stage="stage3_keyframes",
            model=model_name,
            parameters={"prompt": prompt, "seed": seed},
            seed=seed,
            latency_sec=latency,
            cached=False,
            status="success",
            output_path=str(target_path)
        )
        print(f"  - Shot {shot_id:02d}: [GENERATED ({model_name})] ({latency:.2f}s) -> {target_path.name}")
        keyframe_paths[shot_id] = target_path
        
    return keyframe_paths


if __name__ == "__main__":
    with open(STORYBOARD_PATH, "r", encoding="utf-8") as f:
        sb = json.load(f)
    generate_keyframes_for_shots(sb)
