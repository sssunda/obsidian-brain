def should_process(parsed: dict, processed_ids: set[str], min_messages: int = 3) -> bool:
    session_id = parsed["session_id"]
    if session_id in processed_ids:
        return False
    user_count = sum(1 for m in parsed["messages"] if m["role"] == "user")
    return user_count > min_messages
