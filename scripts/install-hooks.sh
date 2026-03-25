#!/usr/bin/env bash
# scripts/install-hooks.sh
# Installs Claude Code hooks for obsidian-brain

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Obsidian Brain Hook Installer"
echo "=============================="
echo ""

# Ask for vault path
read -p "Obsidian Vault 경로를 입력하세요 (예: ~/ObsidianVault): " VAULT_PATH
VAULT_PATH="${VAULT_PATH/#\~/$HOME}"

if [ ! -d "$VAULT_PATH" ]; then
    echo "Error: $VAULT_PATH 디렉토리가 존재하지 않습니다."
    exit 1
fi

# Create .obsidian-brain directory
mkdir -p "$VAULT_PATH/.obsidian-brain/logs"

# Create default config if not exists
if [ ! -f "$VAULT_PATH/.obsidian-brain/config.yaml" ]; then
    cat > "$VAULT_PATH/.obsidian-brain/config.yaml" << EOF
vault_path: $VAULT_PATH
min_messages: 3
max_transcript_chars: 50000
max_retries: 3
processed_retention_days: 30
slug_language: en
folders:
  conversations: Conversations
  concepts: Concepts
  projects: Projects
EOF
    echo "Created config: $VAULT_PATH/.obsidian-brain/config.yaml"
fi

# Create vault directories
mkdir -p "$VAULT_PATH/Conversations"
mkdir -p "$VAULT_PATH/Concepts"
mkdir -p "$VAULT_PATH/Projects"

echo ""
echo "설치 완료!"
echo ""
echo "Claude Code hooks를 설정하려면 ~/.claude/settings.json에 아래를 추가하세요:"
echo ""
cat << EOF
{
  "hooks": {
    "SessionEnd": [
      {
        "command": "uv run --project $PROJECT_DIR python -m obsidian_brain process --session-id \$SESSION_ID --cwd \$CWD --vault-path $VAULT_PATH &",
        "timeout": 5000
      }
    ],
    "SessionStart": [
      {
        "command": "uv run --project $PROJECT_DIR python -m obsidian_brain recover --vault-path $VAULT_PATH &",
        "timeout": 5000
      }
    ]
  }
}
EOF
