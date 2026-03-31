#!/usr/bin/env bash
# scripts/migrate-docs.sh
# Migrate existing vault docs to latest format
# - Remove "None" description text from Concepts
# - Remove empty sections from Conversations
# - Add type: conversation to Conversation frontmatter
# - Deduplicate near-identical insights in Concepts

set -euo pipefail

if ! command -v python3 &> /dev/null; then
    echo "Error: python3 required"
    exit 1
fi

VAULT_PATH="${1:-}"
if [ -z "$VAULT_PATH" ]; then
    read -p "Obsidian Vault 경로: " VAULT_PATH
fi
VAULT_PATH="${VAULT_PATH/#\~/$HOME}"

if [ ! -d "$VAULT_PATH" ]; then
    echo "Error: $VAULT_PATH not found"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Migrating vault: $VAULT_PATH"
uv run --project "$PROJECT_DIR" python3 -c "
import sys
sys.path.insert(0, '$PROJECT_DIR/src')
from obsidian_brain.migrate import migrate_vault
from pathlib import Path
migrate_vault(Path('$VAULT_PATH'))
"
echo "Migration complete!"
