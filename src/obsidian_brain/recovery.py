import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def find_unprocessed_sessions(
    projects_subdir: Path,
    processed_ids: set[str],
    max_age_days: int = 30,
    batch_limit: int = 10,
) -> list[Path]:
    if not projects_subdir.exists():
        return []

    cutoff = time.time() - (max_age_days * 86400)
    unprocessed = []

    for f in projects_subdir.glob("*.jsonl"):
        if not f.is_file():
            continue
        session_id = f.stem
        if session_id in processed_ids:
            continue
        if f.stat().st_mtime < cutoff:
            continue
        unprocessed.append(f)

    unprocessed.sort(key=lambda f: f.stat().st_mtime)
    return unprocessed[:batch_limit]
