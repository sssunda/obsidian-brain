import json
import logging
import shutil
import subprocess
import time

logger = logging.getLogger(__name__)


def ensure_claude_available() -> None:
    """Check that claude CLI is installed and accessible."""
    if not shutil.which("claude"):
        raise FileNotFoundError(
            "claude CLI not found. Install from https://docs.anthropic.com/en/docs/claude-code"
        )


def _extract_result(output: dict, schema: dict) -> dict:
    """Extract structured result from claude -p JSON output, validate required keys."""
    result = None
    if "structured_output" in output and isinstance(output["structured_output"], dict):
        result = output["structured_output"]
    elif "structured_output" in output and isinstance(output["structured_output"], str):
        result = json.loads(output["structured_output"])
    elif "result" in output and isinstance(output["result"], str) and output["result"]:
        result = json.loads(output["result"])
    elif "result" in output and isinstance(output["result"], dict):
        result = output["result"]
    else:
        result = output

    # Validate required keys from schema
    required = schema.get("required", [])
    missing = [k for k in required if k not in result]
    if missing:
        raise ValueError(f"Response missing required keys: {missing}")

    return result


def call_claude(prompt: str, schema: dict, max_retries: int = 3, model: str = "sonnet") -> dict:
    """Call claude -p with JSON schema and return parsed result."""
    ensure_claude_available()
    schema_json = json.dumps(schema)

    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                [
                    "claude", "-p",
                    "--model", model,
                    "--output-format", "json",
                    "--json-schema", schema_json,
                ],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                logger.warning(f"claude -p failed (attempt {attempt + 1}): {result.stderr[:200]}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                continue

            output = json.loads(result.stdout)
            return _extract_result(output, schema)

        except (json.JSONDecodeError, subprocess.TimeoutExpired, ValueError) as e:
            logger.warning(f"claude -p error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)

    raise RuntimeError(f"claude -p failed after {max_retries} attempts")
