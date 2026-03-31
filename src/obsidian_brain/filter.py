import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def should_process(parsed: dict, processed_ids: set[str], min_messages: int = 3) -> bool:
    session_id = parsed["session_id"]
    if session_id in processed_ids:
        return False
    user_count = sum(1 for m in parsed["messages"] if m["role"] == "user")
    if user_count <= min_messages:
        return False
    # Reject sessions where user messages are too short (avg < 10 chars)
    user_msgs = [m["content"] for m in parsed["messages"] if m["role"] == "user"]
    avg_len = sum(len(m) for m in user_msgs) / max(len(user_msgs), 1)
    if avg_len < 10:
        return False
    return True


def is_similar_conversation(summary: str, vault_path, conv_folder: str, date: str, threshold: float = 0.6) -> bool:
    """Check if a very similar conversation already exists for the same date."""
    from pathlib import Path
    import frontmatter

    year_month = date[:7]
    conv_dir = Path(vault_path) / conv_folder / year_month
    if not conv_dir.exists():
        return False

    for md_file in conv_dir.glob(f"{date}-*.md"):
        try:
            post = frontmatter.load(md_file)
            existing_title = post.get("title", "")
            if existing_title and SequenceMatcher(None, summary.lower(), existing_title.lower()).ratio() >= threshold:
                return True
        except Exception as e:
            logger.warning(f"Error reading {md_file.name} for similarity check: {e}")
            continue

    return False
