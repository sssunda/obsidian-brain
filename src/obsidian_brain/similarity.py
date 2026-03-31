"""Shared similarity utilities for deduplication."""
from difflib import SequenceMatcher

DEFAULT_THRESHOLD = 0.5
MAX_INSIGHTS = 10


def is_similar(a: str, b: str, threshold: float = DEFAULT_THRESHOLD) -> bool:
    """Check if two strings are semantically similar using both sequence and word overlap."""
    a_lower, b_lower = a.lower(), b.lower()
    # Sequence similarity (word order matters)
    seq_ratio = SequenceMatcher(None, a_lower, b_lower).ratio()
    if seq_ratio >= threshold:
        return True
    # Jaccard similarity (word set overlap, order doesn't matter)
    words_a = set(a_lower.split())
    words_b = set(b_lower.split())
    if not words_a or not words_b:
        return False
    jaccard = len(words_a & words_b) / len(words_a | words_b)
    return jaccard >= threshold


def has_similar_insight(new_insight: str, content: str, threshold: float = DEFAULT_THRESHOLD) -> bool:
    """Check if content already contains a similar insight line."""
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("- (") and ")" in line:
            existing = line.split(")", 1)[1].strip()
            if is_similar(new_insight, existing, threshold):
                return True
    return False


def count_insights(content: str) -> int:
    """Count insight lines in content."""
    return sum(1 for line in content.split("\n") if line.strip().startswith("- ("))


def trim_insights(content: str, max_count: int = MAX_INSIGHTS) -> str:
    """Keep only the most recent N insights, removing oldest."""
    lines = content.split("\n")
    result = []
    in_section = False
    insight_lines = []

    for line in lines:
        if line.strip() == "## 인사이트":
            in_section = True
            result.append(line)
            continue
        if in_section and line.startswith("## "):
            # Flush kept insights before leaving section
            if len(insight_lines) > max_count:
                insight_lines = insight_lines[-max_count:]
            result.extend(insight_lines)
            insight_lines = []
            in_section = False
            result.append(line)
            continue

        if in_section and line.strip().startswith("- ("):
            insight_lines.append(line)
        elif in_section:
            result.append(line)
        else:
            result.append(line)

    # Flush remaining insights (section was last)
    if insight_lines:
        if len(insight_lines) > max_count:
            insight_lines = insight_lines[-max_count:]
        result.extend(insight_lines)

    return "\n".join(result)
