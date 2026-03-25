from obsidian_brain.lockfile import acquire_lock, release_lock


def test_acquire_and_release(tmp_path):
    """Can acquire lock, then release it."""
    lock_path = tmp_path / "pipeline.lock"
    lock_fd = acquire_lock(lock_path, timeout=2)
    assert lock_fd is not None
    assert lock_path.exists()
    release_lock(lock_fd, lock_path)
    assert not lock_path.exists()


def test_acquire_blocks_second_caller(tmp_path):
    """Second acquire with timeout=0 returns None if already locked."""
    lock_path = tmp_path / "pipeline.lock"
    fd1 = acquire_lock(lock_path, timeout=2)
    assert fd1 is not None
    fd2 = acquire_lock(lock_path, timeout=0)
    assert fd2 is None
    release_lock(fd1, lock_path)
