import argparse
import logging
import sys
import time
from datetime import date, datetime
from pathlib import Path

from .config import load_config
from .digest import run_daily_digest
from .lockfile import acquire_lock, release_lock
from .parser import build_transcript_path
from .pipeline import process_session
from .recovery import find_unprocessed_sessions
from .vault import load_processed_ids, rotate_processed


MAX_RETRY_COUNT = 3


def load_failed_ids(vault_path: Path) -> set[str]:
    """Load session IDs that failed MAX_RETRY_COUNT times (permanently skip)."""
    failed_file = vault_path / ".obsidian-brain" / ".failed"
    if not failed_file.exists():
        return set()
    text = failed_file.read_text().strip()
    if not text:
        return set()
    # Count failures per session
    counts: dict[str, int] = {}
    for line in text.splitlines():
        if line.strip():
            sid = line.split("\t")[0]
            counts[sid] = counts.get(sid, 0) + 1
    return {sid for sid, count in counts.items() if count >= MAX_RETRY_COUNT}


def setup_logging(vault_path: Path) -> None:
    log_dir = vault_path / ".obsidian-brain" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{date.today().isoformat()}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stderr),
        ],
    )


def cmd_process(args) -> None:
    vault_path = Path(args.vault_path).expanduser().resolve()
    setup_logging(vault_path)
    logger = logging.getLogger(__name__)

    lock_path = vault_path / ".obsidian-brain" / "pipeline.lock"
    lock_fd = acquire_lock(lock_path, timeout=60)
    if lock_fd is None:
        logger.warning("Could not acquire lock, another process is running")
        sys.exit(1)

    try:
        transcript = build_transcript_path(args.session_id, args.cwd)
        if not transcript.exists():
            logger.error(f"Transcript not found: {transcript}")
            sys.exit(1)

        result = process_session(
            transcript_path=transcript,
            vault_path=vault_path,
        )
        if result:
            logger.info(f"Created: {result}")
    except Exception as e:
        logger.exception(f"Failed to process session {args.session_id}: {e}")
        failed_file = vault_path / ".obsidian-brain" / ".failed"
        with open(failed_file, "a") as f:
            f.write(f"{args.session_id}\t{e}\t{datetime.now().isoformat()}\n")
        sys.exit(1)
    finally:
        release_lock(lock_fd, lock_path)


def cmd_recover(args) -> None:
    vault_path = Path(args.vault_path).expanduser().resolve()
    setup_logging(vault_path)
    logger = logging.getLogger(__name__)
    config = load_config(vault_path)

    lock_path = vault_path / ".obsidian-brain" / "pipeline.lock"
    lock_fd = acquire_lock(lock_path, timeout=0)
    if lock_fd is None:
        logger.info("Another process is running, skipping recovery")
        return

    try:
        processed = load_processed_ids(vault_path)
        failed = load_failed_ids(vault_path)
        skip_ids = processed | failed
        claude_dir = Path.home() / ".claude"
        projects_dir = claude_dir / "projects"
        if not projects_dir.exists():
            return

        # Rotate old processed entries
        try:
            rotate_processed(vault_path, config.get("processed_retention_days", 30))
        except Exception as e:
            logger.warning(f"Rotation failed: {e}")

        total_processed = 0
        for encoded_dir in projects_dir.iterdir():
            if not encoded_dir.is_dir():
                continue

            sessions = find_unprocessed_sessions(
                projects_subdir=encoded_dir,
                processed_ids=skip_ids,
                max_age_days=config.get("processed_retention_days", 30),
                batch_limit=config.get("batch_limit", 10),
            )

            for transcript in sessions:
                try:
                    result = process_session(
                        transcript_path=transcript,
                        vault_path=vault_path,
                    )
                    if result:
                        total_processed += 1
                        logger.info(f"Recovered: {result}")
                    time.sleep(config.get("rate_limit_seconds", 2))
                except Exception as e:
                    logger.warning(f"Recovery failed for {transcript.stem}: {e}")

        logger.info(f"Recovery complete: {total_processed} sessions processed")

        # Run daily digest
        try:
            conv_folder = config.get("folders", {}).get("conversations", "Conversations")
            digest_path = run_daily_digest(
                vault_path=vault_path,
                conv_folder=conv_folder,
                max_retries=config.get("max_retries", 3),
                digest_days=config.get("processed_retention_days", 30),
            )
            if digest_path:
                logger.info(f"Daily digest updated: {digest_path}")
        except Exception as e:
            logger.warning(f"Digest failed: {e}")

    finally:
        release_lock(lock_fd, lock_path)


def cmd_digest(args) -> None:
    vault_path = Path(args.vault_path).expanduser().resolve()
    setup_logging(vault_path)
    logger = logging.getLogger(__name__)
    config = load_config(vault_path)

    if args.force:
        marker = vault_path / ".obsidian-brain" / ".last_digest"
        if marker.exists():
            marker.unlink()

    conv_folder = config.get("folders", {}).get("conversations", "Conversations")
    digest_path = run_daily_digest(
        vault_path=vault_path,
        conv_folder=conv_folder,
        max_retries=config.get("max_retries", 3),
        digest_days=config.get("processed_retention_days", 30),
    )
    if digest_path:
        logger.info(f"Digest written: {digest_path}")
    else:
        logger.info("No digest generated (already ran today or no conversations)")


def cmd_status(args) -> None:
    vault_path = Path(args.vault_path).expanduser().resolve()
    config = load_config(vault_path)

    # Processed count
    processed = load_processed_ids(vault_path)
    failed = load_failed_ids(vault_path)

    # Document counts
    conv_dir = vault_path / config["folders"]["conversations"]
    concept_dir = vault_path / config["folders"]["concepts"]
    project_dir = vault_path / config["folders"]["projects"]

    conv_count = sum(1 for _ in conv_dir.rglob("*.md")) if conv_dir.exists() else 0
    concept_count = sum(1 for _ in concept_dir.glob("*.md")) if concept_dir.exists() else 0
    project_count = sum(1 for _ in project_dir.glob("*.md")) if project_dir.exists() else 0

    # Digest status
    digest_path = vault_path / "My Patterns.md"
    last_digest_marker = vault_path / ".obsidian-brain" / ".last_digest"
    last_digest = last_digest_marker.read_text().strip() if last_digest_marker.exists() else "never"

    # Recent errors
    log_dir = vault_path / ".obsidian-brain" / "logs"
    log_file = log_dir / f"{date.today().isoformat()}.log"
    recent_errors = []
    if log_file.exists():
        for line in log_file.read_text().splitlines()[-100:]:
            if "[ERROR]" in line or "[WARNING]" in line:
                recent_errors.append(line)

    print(f"""Obsidian Brain Status
{'=' * 40}
Vault: {vault_path}

Documents:
  Conversations: {conv_count}
  Concepts:      {concept_count}
  Projects:      {project_count}

Processing:
  Processed sessions: {len(processed)}
  Failed sessions:    {len(failed)}
  Last digest:        {last_digest}
  My Patterns.md:     {'exists' if digest_path.exists() else 'not yet'}

Recent errors ({len(recent_errors)}):""")
    for err in recent_errors[-5:]:
        print(f"  {err}")
    if not recent_errors:
        print("  (none)")


def main():
    parser = argparse.ArgumentParser(
        prog="obsidian-brain",
        description="Auto-generate Obsidian docs from AI conversations",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_process = subparsers.add_parser("process", help="Process a single session")
    p_process.add_argument("--session-id", required=True)
    p_process.add_argument("--cwd", required=True)
    p_process.add_argument("--vault-path", required=True)
    p_process.set_defaults(func=cmd_process)

    p_recover = subparsers.add_parser("recover", help="Find and process unprocessed sessions")
    p_recover.add_argument("--vault-path", required=True)
    p_recover.set_defaults(func=cmd_recover)

    p_digest = subparsers.add_parser("digest", help="Manually run daily digest")
    p_digest.add_argument("--vault-path", required=True)
    p_digest.add_argument("--force", action="store_true", help="Run even if already ran today")
    p_digest.set_defaults(func=cmd_digest)

    p_status = subparsers.add_parser("status", help="Show processing status")
    p_status.add_argument("--vault-path", required=True)
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
