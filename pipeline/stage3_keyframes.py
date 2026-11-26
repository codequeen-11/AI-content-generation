"""
Stage 3: Keyframe Generation via Cloudflare Workers AI (FLUX.1 schnell).
Generates photorealistic keyframe images conditioned on authentic Ethiopian cultural
style block and character sheet, with center-safe framing for both 16:9 and 9:16 exports.
"""
import base64
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
    KEYFRAMES_DIR,
    CLOUDFLARE_API_TOKEN,
    CLOUDFLARE_ACCOUNT_ID
)
from pipeline.logger import audit_logger
from pipeline.cache import CacheManager


def call_cloudflare_flux(
    prompt: str,
    account_id: str,
    api_token: str,
    output_path: Path
) -> bool:
    """
    Calls Cloudflare Workers AI (@cf/black-forest-labs/flux-1-schnell).
    Direct free tier integration as specified in challenge documentation.
    """
    acc = account_id.strip()
    tok = api_token.strip()
    if not acc or not tok:
        return False
        
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    headers = {
        "Authorization": f"Bearer {tok}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": prompt
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            content_type = resp.headers.get("content-type", "")
            if "image" in content_type:
                img = Image.open(BytesIO(resp.content)).convert("RGB")
                img_hd = img.resize((1920, 1080), Image.Resampling.LANCZOS)
                img_hd.save(output_path, "PNG")
                return True
            else:
                res_data = resp.json()
                b64_img = res_data.get("result", {}).get("image")
                if b64_img:
                    raw_bytes = base64.b64decode(b64_img)
                    img = Image.open(BytesIO(raw_bytes)).convert("RGB")
                    img_hd = img.resize((1920, 1080), Image.Resampling.LANCZOS)
                    img_hd.save(output_path, "PNG")
                    return True
        else:
            print(f"    [Cloudflare Status {resp.status_code}] {resp.text[:120]}")
            return False
    except Exception as e:
        print(f"    [Cloudflare Error] {e}")
        return False


def call_diffusion_fallback(
    prompt: str,
    seed: int,
    output_path: Path,
    retries: int = 2
) -> bool:
    """Fast diffusion fallback if cloud endpoint is busy."""
    encoded_prompt = urllib.parse.quote(prompt.strip())
    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?model=turbo&width=1024&height=576&seed={seed}&nologo=true"
    )
    
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 10000:
                img = Image.open(BytesIO(resp.content)).convert("RGB")
                img_hd = img.resize((1920, 1080), Image.Resampling.LANCZOS)
                img_hd.save(output_path, "PNG")
                return True
            else:
                time.sleep(2.0)
        except Exception:
            time.sleep(2.0)
            
    return False


def create_procedural_fallback_card(
    path: Path,
    shot: dict,
    width: int = 1920,
    height: int = 1080
):
    """Fallback visual card if offline."""
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


def generate_keyframes_for_shots(storyboard: dict, force: bool = False) -> Dict[int, Path]:
    """Generates keyframes for each shot with content-addressable caching."""
    keyframe_paths = {}
    shots = storyboard["shots"]
    style_block = storyboard.get("style_block", {})
    char_ref = storyboard.get("character_reference", {})
    
    using_cf = bool(CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID)
    engine_name = "Cloudflare Workers AI (FLUX.1 schnell)" if using_cf else "High-Speed Diffusion Fallback"
    print(f"\n[Stage 3] Generating keyframes for {len(shots)} shots via {engine_name}...")
    
    for shot in shots:
        shot_id = shot["id"]
        prompt = shot["keyframe_prompt"]
        seed = shot.get("seed", 42000 + shot_id)
        
        # Center-safe composition with explicit Ethiopian cultural anchors
        if shot_id == 13:
            full_prompt = f"{prompt}, perfectly centered, clean 16:9 graphic design"
        elif shot_id == 9:
            full_prompt = (
                f"{prompt}, subject centered in middle of frame, authentic Ethiopian university graduation, "
                f"photorealistic 35mm documentary film photography, natural daylight, highly detailed"
            )
        elif shot_id == 10:
            full_prompt = (
                f"{prompt}, subject centered in middle of frame, authentic generational embrace, "
                f"photorealistic 35mm documentary portrait photography, natural lighting, highly detailed"
            )
        else:
            full_prompt = (
                f"{prompt}. Authentic Ethiopian cultural heritage, traditional white Netela cotton scarf "
                f"with colorful woven Tibeb border, subject centered in middle of frame, "
                f"cinematic 35mm film still, warm golden morning light, highly detailed"
            )
        
        input_data = {
            "shot_id": shot_id,
            "prompt": prompt,
            "seed": seed,
            "engine": "cloudflare-flux-v4" if using_cf else "diffusion-v4",
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
        success = False
        model_name = "flux.1-schnell-cloudflare" if using_cf else "diffusion-fast"
        
        if using_cf:
            success = call_cloudflare_flux(full_prompt, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN, target_path)
            
        if not success:
            success = call_diffusion_fallback(full_prompt, seed, target_path)
            if success:
                model_name = "diffusion-fast"
                
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
        time.sleep(1.5)
        
    return keyframe_paths


if __name__ == "__main__":
    with open(STORYBOARD_PATH, "r", encoding="utf-8") as f:
        sb = json.load(f)
    generate_keyframes_for_shots(sb)
