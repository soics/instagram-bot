#!/usr/bin/env bash
set -euo pipefail

# cleanup-for-push.sh
# Run BEFORE git init to strip secrets, caches, and runtime state.
# Leaves only source code and documentation.
#
# Usage:
#   cd ~/instagrambot
#   bash scripts/cleanup-for-push.sh
#   git init && git add . && git commit -m "Initial commit"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "→ Cleaning $PROJECT_DIR for public push..."

# Secrets
rm -f .env
rm -f session.json
echo "  ✓ Removed secrets (.env, session.json)"

# Runtime state
rm -f seen.json
echo "  ✓ Removed runtime state (seen.json)"

# Image cache
rm -rf img_cache/
echo "  ✓ Removed image cache (img_cache/)"

# Old backup
rm -f bot.py.save
echo "  ✓ Removed old backup (bot.py.save)"

# Python bytecode
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name '*.pyc' -delete
echo "  ✓ Removed Python bytecode (__pycache__/, *.pyc)"

# OS cruft
find . -type f -name '.DS_Store' -delete
find . -type f -name '*.swp' -delete
find . -type f -name '*~' -delete
echo "  ✓ Removed OS cruft (.DS_Store, *.swp, *~)"

echo ""
echo "Done. $PROJECT_DIR is clean for push."
echo ""
echo "Next steps:"
echo "  cd $PROJECT_DIR"
echo "  git init"
echo "  git add ."
echo "  git commit -m 'Initial commit'"
echo "  gh repo create instagram-bot --public --source=. --push"
