import fcntl
import time
from io import TextIOWrapper
from pathlib import Path


def acquire_lock(lock_path: Path, timeout: int = 30) -> TextIOWrapper | None:
    """Acquire file lock. Returns file object on success, None on timeout."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = open(lock_path, "w")
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fd.write(str(time.time()))
            fd.flush()
            return fd
        except OSError:
            if time.monotonic() >= deadline:
                fd.close()
                return None
            time.sleep(0.5)


def release_lock(fd, lock_path: Path) -> None:
    """Release file lock and remove lock file."""
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()
        lock_path.unlink(missing_ok=True)
    except OSError:
        pass
