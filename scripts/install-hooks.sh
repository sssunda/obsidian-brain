#!/usr/bin/env bash
# scripts/install-hooks.sh
# Installs Claude Code hooks for obsidian-brain

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SETTINGS_FILE="$HOME/.claude/settings.json"

echo "Obsidian Brain Hook Installer"
echo "=============================="
echo ""

# Check jq is installed
if ! command -v jq &> /dev/null; then
    echo "Error: jq가 필요합니다. 설치해주세요:"
    echo "  brew install jq    (macOS)"
    echo "  apt install jq     (Ubuntu/Debian)"
    exit 1
fi

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
    echo "✓ Config 생성: $VAULT_PATH/.obsidian-brain/config.yaml"
fi

# Create vault directories
mkdir -p "$VAULT_PATH/Conversations"
mkdir -p "$VAULT_PATH/Concepts"
mkdir -p "$VAULT_PATH/Projects"
echo "✓ Vault 폴더 생성 완료"

# Install CSS snippet
SNIPPETS_DIR="$VAULT_PATH/.obsidian/snippets"
mkdir -p "$SNIPPETS_DIR"
if [ -f "$PROJECT_DIR/templates/obsidian-brain.css" ]; then
    cp "$PROJECT_DIR/templates/obsidian-brain.css" "$SNIPPETS_DIR/"
    echo "✓ CSS snippet 설치: $SNIPPETS_DIR/obsidian-brain.css"
fi

# Install dashboard template
if [ -f "$PROJECT_DIR/templates/dashboard.md" ] && [ ! -f "$VAULT_PATH/Brain Dashboard.md" ]; then
    cp "$PROJECT_DIR/templates/dashboard.md" "$VAULT_PATH/Brain Dashboard.md"
    echo "✓ Dashboard 생성: $VAULT_PATH/Brain Dashboard.md"
fi

# Build hooks JSON
HOOKS_JSON=$(cat << ENDJSON
{
  "SessionEnd": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "uv run --project $PROJECT_DIR python -m obsidian_brain process --session-id \$SESSION_ID --cwd \"\$CWD\" --vault-path \"$VAULT_PATH\"",
          "timeout": 120,
          "async": true
        }
      ]
    }
  ],
  "SessionStart": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "uv run --project $PROJECT_DIR python -m obsidian_brain recover --vault-path \"$VAULT_PATH\"",
          "timeout": 120,
          "async": true
        }
      ]
    }
  ]
}
ENDJSON
)

# Create settings.json if it doesn't exist
mkdir -p "$(dirname "$SETTINGS_FILE")"
if [ ! -f "$SETTINGS_FILE" ]; then
    echo '{}' > "$SETTINGS_FILE"
    echo "✓ settings.json 생성: $SETTINGS_FILE"
fi

# Check if hooks already exist
EXISTING_HOOKS=$(jq -r '.hooks // empty' "$SETTINGS_FILE")
if [ -n "$EXISTING_HOOKS" ] && [ "$EXISTING_HOOKS" != "{}" ]; then
    BACKUP_FILE="${SETTINGS_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$SETTINGS_FILE" "$BACKUP_FILE"
    echo "⚠ 기존 hooks 발견 → 백업: $BACKUP_FILE"
fi

# Merge hooks into settings.json
jq --argjson hooks "$HOOKS_JSON" '.hooks = $hooks' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" \
    && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"

echo "✓ hooks 설정 완료: $SETTINGS_FILE"
echo ""
echo "설치 완료! 다음 Claude Code 세션부터 자동으로 작동합니다."
echo ""
echo "에러 확인:"
echo "  cat \"$VAULT_PATH/.obsidian-brain/logs/\$(date +%Y-%m-%d).log\""
echo "  cat \"$VAULT_PATH/.obsidian-brain/.failed\""
