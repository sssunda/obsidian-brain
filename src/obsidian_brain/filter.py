import logging
from difflib import SequenceMatcher
from pathlib import Path

logger = logging.getLogger(__name__)


def should_process(parsed: dict, processed_ids: set[str], min_messages: int = 3) -> bool:
    session_id = parsed["session_id"]
    if session_id in processed_ids:
        return False
    user_count = sum(1 for m in parsed["messages"] if m["role"] == "user")
    if user_count <= min_messages:
        return False
    user_msgs = [m["content"] for m in parsed["messages"] if m["role"] == "user"]
    avg_len = sum(len(m) for m in user_msgs) / max(len(user_msgs), 1)
    if avg_len < 10:
        return False
    return True


def is_similar_experience(title: str, vault_path, exp_folder: str = "Experiences", threshold: float = 0.6) -> bool:
    """Check if a similar experience note already exists."""
    exp_dir = Path(vault_path) / exp_folder
    if not exp_dir.exists():
        return False

    title_lower = title.lower()
    title_words = set(title_lower.split())

    for md_file in exp_dir.glob("*.md"):
        existing_title = md_file.stem
        existing_lower = existing_title.lower()

        if SequenceMatcher(None, title_lower, existing_lower).ratio() >= threshold:
            logger.info(f"Experience dedup: '{title}' similar to existing '{existing_title}'")
            return True

        existing_words = set(existing_lower.split())
        if title_words and existing_words:
            jaccard = len(title_words & existing_words) / len(title_words | existing_words)
            if jaccard >= threshold:
                logger.info(f"Experience dedup (jaccard): '{title}' similar to existing '{existing_title}'")
                return True

    return False
