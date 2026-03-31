import json
from datetime import datetime, timezone
from pathlib import Path


def parse_transcript(transcript_path: Path) -> dict:
    messages = []
    session_id = transcript_path.stem

    with open(transcript_path) as f:
        for line in f:
            record = json.loads(line)
            record_type = record.get("type")

            if record_type == "user":
                content = record.get("message", {}).get("content", "")
                if isinstance(content, str) and content.strip():
                    messages.append({"role": "user", "content": content})

            elif record_type == "assistant":
                content = record.get("message", {}).get("content", [])
                text_parts = []
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                elif isinstance(content, str):
                    text_parts.append(content)
                combined = "\n".join(text_parts).strip()
                if combined:
                    messages.append({"role": "assistant", "content": combined})

    mtime = transcript_path.stat().st_mtime
    date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")

    return {
        "session_id": session_id,
        "source": "claude-code",
        "date": date_str,
        "messages": messages,
    }


def encode_cwd(cwd: str) -> str:
    return cwd.replace("/", "-") if cwd != "/" else "-"


def build_transcript_path(session_id: str, cwd: str) -> Path:
    encoded = encode_cwd(cwd)
    return Path.home() / ".claude" / "projects" / encoded / f"{session_id}.jsonl"
