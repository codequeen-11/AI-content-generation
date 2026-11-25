"""
One-command entrypoint for the Heritage Short Film Pipeline.
Usage:
  python run_pipeline.py
  python run_pipeline.py --stage stage1
  python run_pipeline.py --force
"""
import sys
from pipeline.run import run_pipeline

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run the Heritage Short film pipeline.")
    parser.add_argument("--stage", type=str, default="all", choices=["all", "stage1", "stage2", "stage3", "stage4", "stage5", "stage6"], help="Run specific stage")
    parser.add_argument("--force", action="store_true", help="Force regeneration bypassing cache")
    parser.add_argument("--shot", type=int, default=None, help="Regenerate only specific shot ID")
    args = parser.parse_args()
    
    run_pipeline(stage=args.stage, force=args.force, shot_filter=args.shot)
