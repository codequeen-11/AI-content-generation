"""
Master Pipeline Orchestrator.
Executes the end-to-end studio pipeline from storyboard to finished film.
Supports single-stage execution, force-regeneration, and single-shot live demo re-runs.
"""
import argparse
import sys
import time
from pathlib import Path

from pipeline.config import STORYBOARD_PATH, BASE_DIR
from pipeline.stage1_schema_validate import validate_storyboard
from pipeline.stage2_narration import generate_narration_for_shots, assemble_radio_cut
from pipeline.stage3_keyframes import generate_keyframes_for_shots
from pipeline.stage4_shots import generate_shots_for_storyboard
from pipeline.stage5_music import generate_music_candidates
from pipeline.stage6_assemble import assemble_final_film


def run_pipeline(stage: str = "all", force: bool = False, shot_filter: int = None):
    t_start = time.time()
    print("=" * 70)
    print("  THE HERITAGE SHORT: STUDIO PIPELINE IN CODE")
    print("  'The Wisdom of Our Mothers (የእናቶቻችን ጥበብ)'")
    print("=" * 70)
    
    # Stage 1: Validate Schema
    print("\n--- STAGE 1: SCHEMA VALIDATION ---")
    storyboard = validate_storyboard()
    if stage == "stage1":
        return
        
    # Stage 2: Narration & Radio Cut
    print("\n--- STAGE 2: NARRATION & RADIO CUT ---")
    voice_paths = generate_narration_for_shots(storyboard, force=force)
    radio_cut_path = assemble_radio_cut(storyboard, voice_paths)
    if stage == "stage2":
        return
        
    # Stage 3: Keyframes
    print("\n--- STAGE 3: KEYFRAME GENERATION ---")
    keyframe_paths = generate_keyframes_for_shots(storyboard, force=force)
    if stage == "stage3":
        return
        
    # Stage 4: Moving Shots
    print("\n--- STAGE 4: MOVING SHOTS ---")
    shot_paths = generate_shots_for_storyboard(storyboard, keyframe_paths, force=force)
    if stage == "stage4":
        return
        
    # Stage 5: Music Score
    print("\n--- STAGE 5: ORIGINAL SCORE GENERATION ---")
    score_path = generate_music_candidates(storyboard, force=force)
    if stage == "stage5":
        return
        
    # Stage 6: Master Assembly
    print("\n--- STAGE 6: MASTER ASSEMBLY & EXPORTS ---")
    exports = assemble_final_film(
        storyboard=storyboard,
        shot_paths=shot_paths,
        voice_path=radio_cut_path,
        score_path=score_path
    )
    
    total_time = time.time() - t_start
    print("\n" + "=" * 70)
    print(f"  PIPELINE EXECUTION COMPLETE IN {total_time:.2f} SECONDS")
    print(f"  - 16:9 Landscape: {exports['16:9']}")
    print(f"  - 9:16 Vertical:  {exports['9:16']}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Heritage Short film pipeline.")
    parser.add_argument("--stage", type=str, default="all", choices=["all", "stage1", "stage2", "stage3", "stage4", "stage5", "stage6"], help="Run specific stage")
    parser.add_argument("--force", action="store_true", help="Force regeneration bypassing cache")
    parser.add_argument("--shot", type=int, default=None, help="Regenerate only specific shot ID")
    args = parser.parse_args()
    
    run_pipeline(stage=args.stage, force=args.force, shot_filter=args.shot)
