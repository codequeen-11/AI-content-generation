"""
Stage 1: Schema Validation.
Validates storyboard.json against schema/storyboard.schema.json before every run.
"""
import json
import time
import jsonschema
from pipeline.config import SCHEMA_PATH, STORYBOARD_PATH
from pipeline.logger import audit_logger


def validate_storyboard(storyboard_path=STORYBOARD_PATH, schema_path=SCHEMA_PATH) -> dict:
    t0 = time.time()
    
    with open(schema_path, "r", encoding="utf-8") as sf:
        schema = json.load(sf)
        
    with open(storyboard_path, "r", encoding="utf-8") as df:
        storyboard = json.load(df)
        
    try:
        jsonschema.validate(instance=storyboard, schema=schema)
        
        # Verify shot count and total duration
        total_duration = sum(s["duration_sec"] for s in storyboard["shots"])
        shot_count = len(storyboard["shots"])
        
        latency = time.time() - t0
        audit_logger.log_run(
            stage="stage1_schema_validate",
            model="jsonschema-validator",
            parameters={"shots_count": shot_count, "total_duration_sec": total_duration},
            seed=None,
            latency_sec=latency,
            cached=False,
            status="success",
            output_path=str(storyboard_path)
        )
        print(f"[Stage 1] Schema validation successful: {shot_count} shots, total duration {total_duration:.1f}s.")
        return storyboard
    except jsonschema.exceptions.ValidationError as err:
        latency = time.time() - t0
        audit_logger.log_run(
            stage="stage1_schema_validate",
            model="jsonschema-validator",
            parameters={},
            seed=None,
            latency_sec=latency,
            cached=False,
            status="error",
            error_message=str(err.message)
        )
        raise RuntimeError(f"[Stage 1] Schema validation failed: {err.message}")


if __name__ == "__main__":
    validate_storyboard()
