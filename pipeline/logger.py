"""
Structured audit logging to runs.jsonl.
Complies with challenge specification: records model, parameters, seed, latency, cost, and cache status.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from pipeline.config import RUNS_LOG_PATH


class AuditLogger:
    def __init__(self, log_path: Path = RUNS_LOG_PATH):
        self.log_path = log_path

    def log_run(
        self,
        stage: str,
        model: str,
        parameters: Dict[str, Any],
        seed: Optional[int],
        latency_sec: float,
        cost_usd: float = 0.0,
        cached: bool = False,
        status: str = "success",
        error_message: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Appends one structured JSON line to runs.jsonl."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "model": model,
            "parameters": parameters,
            "seed": seed,
            "latency_sec": round(latency_sec, 4),
            "cost_usd": round(cost_usd, 4),
            "cached": cached,
            "status": status,
            "error_message": error_message,
            "output_path": output_path
        }
        
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
        return entry


audit_logger = AuditLogger()
