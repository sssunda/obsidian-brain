from obsidian_brain.filter import should_process


def test_skip_too_few_user_messages():
    parsed = {
        "session_id": "abc",
        "messages": [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "thanks"},
            {"role": "assistant", "content": "bye"},
        ],
    }
    assert should_process(parsed, processed_ids=set(), min_messages=3) is False


def test_process_enough_messages():
    parsed = {
        "session_id": "abc",
        "messages": [
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"},
            {"role": "assistant", "content": "a2"},
            {"role": "user", "content": "q3"},
            {"role": "assistant", "content": "a3"},
            {"role": "user", "content": "q4"},
            {"role": "assistant", "content": "a4"},
        ],
    }
    assert should_process(parsed, processed_ids=set(), min_messages=3) is True


def test_skip_already_processed():
    parsed = {
        "session_id": "abc",
        "messages": [{"role": "user", "content": f"q{i}"} for i in range(10)],
    }
    assert should_process(parsed, processed_ids={"abc"}, min_messages=3) is False


def test_skip_exactly_three_user_messages():
    parsed = {
        "session_id": "abc",
        "messages": [
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"},
            {"role": "assistant", "content": "a2"},
            {"role": "user", "content": "q3"},
            {"role": "assistant", "content": "a3"},
        ],
    }
    assert should_process(parsed, processed_ids=set(), min_messages=3) is False
