"""
Content-addressable caching manager.
Computes SHA-256 hash of stage inputs so reruns only regenerate changed shots.
"""
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def compute_input_hash(data: Dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 hash for an input dictionary."""
    normalized_json = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(normalized_json.encode("utf-8")).hexdigest()[:12]


class CacheManager:
    @staticmethod
    def get_artifact(
        stage_dir: Path,
        prefix: str,
        input_data: Dict[str, Any],
        extension: str
    ) -> Tuple[Path, str, bool]:
        """
        Returns (target_filepath, input_hash, is_cached).
        Target path format: <stage_dir>/<prefix>_<input_hash>.<extension>
        """
        input_hash = compute_input_hash(input_data)
        target_path = stage_dir / f"{prefix}_{input_hash}.{extension}"
        is_cached = target_path.exists() and target_path.stat().st_size > 0
        return target_path, input_hash, is_cached
