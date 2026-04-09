from obsidian_brain.filter import should_process, is_similar_experience


def _make_parsed(session_id, user_msgs):
    messages = []
    for msg in user_msgs:
        messages.append({"role": "user", "content": msg})
        messages.append({"role": "assistant", "content": "response to: " + msg})
    return {"session_id": session_id, "messages": messages}


def test_skip_too_few_user_messages():
    parsed = _make_parsed("abc", ["hi", "thanks"])
    assert should_process(parsed, processed_ids=set(), min_messages=3) is False


def test_process_enough_messages():
    parsed = _make_parsed("abc", [
        "Docker 네트워킹 설정 방법을 알려줘",
        "bridge와 host 네트워크의 차이가 뭐야?",
        "컨테이너 간 통신은 어떻게 하지?",
        "docker-compose에서 네트워크 설정하는 법",
    ])
    assert should_process(parsed, processed_ids=set(), min_messages=3) is True


def test_skip_already_processed():
    parsed = _make_parsed("abc", ["질문 " * 10 for _ in range(10)])
    assert should_process(parsed, processed_ids={"abc"}, min_messages=3) is False


def test_skip_exactly_three_user_messages():
    parsed = _make_parsed("abc", [
        "첫 번째 질문입니다 설명해주세요",
        "두 번째 질문도 궁금합니다",
        "세 번째 질문까지만 할게요",
    ])
    assert should_process(parsed, processed_ids=set(), min_messages=3) is False


def test_skip_short_messages():
    parsed = _make_parsed("abc", ["ㅇ", "ㅎ", "ㅇㅇ", "ㄴㄴ", "ㅋ"])
    assert should_process(parsed, processed_ids=set(), min_messages=3) is False


def test_experience_dedup_exact_match(tmp_path):
    exp_dir = tmp_path / "Experiences"
    exp_dir.mkdir()
    (exp_dir / "schema 서브모듈 커밋 누락으로 Django 부팅 불가.md").write_text("# test")
    assert is_similar_experience(
        "schema 서브모듈 커밋 누락으로 Django 부팅 불가",
        tmp_path, "Experiences",
    ) is True


def test_experience_dedup_similar_title(tmp_path):
    exp_dir = tmp_path / "Experiences"
    exp_dir.mkdir()
    (exp_dir / "schema 서브모듈 커밋 누락으로 Django 부팅 불가.md").write_text("# test")
    assert is_similar_experience(
        "schema 서브모듈 커밋 누락으로 Django ModuleNotFoundError",
        tmp_path, "Experiences",
    ) is True


def test_experience_dedup_different_topic(tmp_path):
    exp_dir = tmp_path / "Experiences"
    exp_dir.mkdir()
    (exp_dir / "schema 서브모듈 커밋 누락으로 Django 부팅 불가.md").write_text("# test")
    assert is_similar_experience(
        "Celery 태스크 내 in-memory 캐시 vs Redis",
        tmp_path, "Experiences",
    ) is False


def test_experience_dedup_empty_dir(tmp_path):
    exp_dir = tmp_path / "Experiences"
    exp_dir.mkdir()
    assert is_similar_experience("아무 제목", tmp_path, "Experiences") is False


def test_experience_dedup_no_dir(tmp_path):
    assert is_similar_experience("아무 제목", tmp_path, "Experiences") is False


def test_experience_dedup_threshold_06(tmp_path):
    """With threshold 0.6, moderately similar titles should NOT match."""
    exp_dir = tmp_path / "Experiences"
    exp_dir.mkdir()
    (exp_dir / "Django QuerySet 평가 시점 함정.md").write_text("# test")
    assert is_similar_experience(
        "Django ORM 성능 최적화 팁",
        tmp_path, "Experiences",
    ) is False
