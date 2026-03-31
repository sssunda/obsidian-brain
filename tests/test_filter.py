from obsidian_brain.filter import should_process


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
    """Sessions with very short user messages (avg < 20 chars) should be skipped."""
    parsed = _make_parsed("abc", ["ㅇ", "ㅎ", "ㅇㅇ", "ㄴㄴ", "ㅋ"])
    assert should_process(parsed, processed_ids=set(), min_messages=3) is False
