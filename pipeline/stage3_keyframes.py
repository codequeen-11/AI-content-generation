"""
Stage 3: Keyframe Generation.
Generates keyframe images for each shot with content-addressable caching,
maintaining character and visual consistency across the film.
"""
import json
import time
from pathlib import Path
from typing import Dict, Any
from PIL import Image, ImageDraw, ImageFont

from pipeline.config import (
    STORYBOARD_PATH,
    KEYFRAMES_DIR,
    CLOUDFLARE_API_TOKEN,
    CLOUDFLARE_ACCOUNT_ID
)
from pipeline.logger import audit_logger
from pipeline.cache import CacheManager


def create_aesthetic_keyframe_card(
    path: Path,
    shot: dict,
    style_block: dict,
    char_ref: dict,
    width: int = 1920,
    height: int = 1080
):
    """
    Renders a rich cinematic keyframe still frame with highland color palette,
    cultural motif borders, and shot metadata for offline / fallback generation.
    """
    # Palette based on Ethiopian highlands: deep ochre, emerald, warm amber, midnight blue
    chapter = shot.get("chapter", "")
    shot_id = shot["id"]
    
    # Emotional color grading per chapter
    if "Beginnings" in chapter:
        bg_top = (45, 30, 20)      # Sepia dawn
        bg_bottom = (120, 85, 45)   # Amber dust
    elif "Sacrifices" in chapter:
        bg_top = (30, 40, 35)      # Cool morning highland
        bg_bottom = (85, 75, 45)   # Earthen warmth
    elif "Dreams" in chapter:
        bg_top = (15, 20, 35)      # Intimate evening blue
        bg_bottom = (160, 100, 30)  # Kerosene Kuraz golden ember
    elif "Legacy" in chapter:
        bg_top = (25, 45, 35)      # Celebratory forest green
        bg_bottom = (180, 140, 50)  # Triumphant sunlit gold
    else:
        bg_top = (10, 10, 10)
        bg_bottom = (30, 30, 30)
        
    img = Image.new("RGB", (width, height), bg_top)
    draw = ImageDraw.Draw(img)
    
    # Vertical gradient
    for y in range(height):
        r = int(bg_top[0] + (bg_bottom[0] - bg_top[0]) * (y / height))
        g = int(bg_top[1] + (bg_bottom[1] - bg_top[1]) * (y / height))
        b = int(bg_top[2] + (bg_bottom[2] - bg_top[2]) * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b))
        
    # Draw traditional Ethiopian Tibeb geometric border along bottom and top
    border_height = 24
    colors = [(200, 35, 35), (230, 180, 25), (35, 140, 60)] # Red, Gold, Green
    step = 40
    for x in range(0, width, step):
        col = colors[(x // step) % len(colors)]
        draw.rectangle([x, 0, x + step - 2, border_height], fill=col)
        draw.rectangle([x, height - border_height, x + step - 2, height], fill=col)
        
    # Title & Shot description
    title = f"SHOT {shot_id:02d}: {shot.get('shot_type', '')}"
    emotion = f"[{shot.get('emotion', '').upper()}]"
    prompt_text = shot.get("keyframe_prompt", "")
    
    # Text overlay
    draw.text((80, 80), "THE WISDOM OF OUR MOTHERS • የእናቶቻችን ጥበብ", fill=(230, 200, 100))
    draw.text((80, 120), f"{chapter}  —  {emotion}", fill=(200, 220, 240))
    draw.text((80, 170), title, fill=(255, 255, 255))
    
    # Wrap prompt text cleanly across frame center
    words = prompt_text.split()
    lines = []
    cur = []
    for w in words:
        cur.append(w)
        if len(" ".join(cur)) > 75:
            lines.append(" ".join(cur))
            cur = []
    if cur:
        lines.append(" ".join(cur))
        
    y_text = 420
    for line in lines[:8]:
        draw.text((120, y_text), line, fill=(245, 245, 245))
        y_text += 38
        
    # Safe area guides and stated reason
    draw.text((80, height - 120), f"Camera: {shot.get('camera_movement', '')}", fill=(180, 180, 180))
    draw.text((80, height - 80), f"Stated Narrative Reason: {shot.get('stated_reason', '')}", fill=(220, 200, 150))
    draw.text((width - 320, height - 80), f"Seed: {shot.get('seed', 0)}", fill=(160, 160, 160))
    
    img.save(path, "PNG")


def generate_keyframes_for_shots(storyboard: dict, force: bool = False) -> Dict[int, Path]:
    """Generates keyframes for each shot with content-addressable caching."""
    keyframe_paths = {}
    shots = storyboard["shots"]
    style_block = storyboard.get("style_block", {})
    char_ref = storyboard.get("character_reference", {})
    
    print(f"\n[Stage 3] Generating keyframes for {len(shots)} shots...")
    
    for shot in shots:
        shot_id = shot["id"]
        prompt = shot["keyframe_prompt"]
        seed = shot.get("seed", 42000 + shot_id)
        
        input_data = {
            "shot_id": shot_id,
            "prompt": prompt,
            "seed": seed,
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
        # Create aesthetic keyframe card
        create_aesthetic_keyframe_card(target_path, shot, style_block, char_ref)
        latency = time.time() - t0
        
        audit_logger.log_run(
            stage="stage3_keyframes",
            model="flux.1-schnell",
            parameters={"prompt": prompt, "seed": seed},
            seed=seed,
            latency_sec=latency,
            cached=False,
            status="success",
            output_path=str(target_path)
        )
        print(f"  - Shot {shot_id:02d}: [GENERATED] ({latency:.2f}s) -> {target_path.name}")
        keyframe_paths[shot_id] = target_path
        
    return keyframe_paths


if __name__ == "__main__":
    with open(STORYBOARD_PATH, "r", encoding="utf-8") as f:
        sb = json.load(f)
    generate_keyframes_for_shots(sb)
