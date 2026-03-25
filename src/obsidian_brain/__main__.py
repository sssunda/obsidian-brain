import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from .config import load_config
from .lockfile import acquire_lock, release_lock
from .parser import build_transcript_path
from .pipeline import process_session
from .recovery import find_unprocessed_sessions
from .vault import load_processed_ids


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
        claude_dir = Path.home() / ".claude"
        projects_dir = claude_dir / "projects"
        if not projects_dir.exists():
            return

        total_processed = 0
        for encoded_dir in projects_dir.iterdir():
            if not encoded_dir.is_dir():
                continue

            sessions = find_unprocessed_sessions(
                projects_subdir=encoded_dir,
                processed_ids=processed,
                max_age_days=config.get("processed_retention_days", 30),
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
                except Exception as e:
                    logger.warning(f"Recovery failed for {transcript.stem}: {e}")

        logger.info(f"Recovery complete: {total_processed} sessions processed")
    finally:
        release_lock(lock_fd, lock_path)


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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
