#!/usr/bin/env bash
# Deploy "Sosed" from your Mac: commit + push to GitHub + update on VPS.
#
# Usage:
#   ./scripts/deploy.sh
#   ./scripts/deploy.sh "fix prompts"
#
# Optional env overrides:
#   DEPLOY_HOST=root@50.114.102.254
#   DEPLOY_DIR=/opt/sosed-bot
#   DEPLOY_BRANCH=master

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DEPLOY_HOST="${DEPLOY_HOST:-root@50.114.102.254}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/sosed-bot}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-master}"
COMMIT_MSG="${1:-Update Sosed bot}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: not a git repository: $ROOT" >&2
  exit 1
fi

CURRENT_BRANCH="$(git branch --show-current)"
if [[ "$CURRENT_BRANCH" != "$DEPLOY_BRANCH" ]]; then
  echo "Warning: current branch is '$CURRENT_BRANCH', deploy branch is '$DEPLOY_BRANCH'"
fi

echo "== Git: stage & commit =="
git add -A
if git diff --staged --quiet; then
  echo "No file changes to commit."
else
  git commit -m "$COMMIT_MSG"
fi

echo "== Git: push to origin/$DEPLOY_BRANCH =="
git push origin "$DEPLOY_BRANCH"

echo "== Server: pull & restart Docker ($DEPLOY_HOST) =="
ssh "$DEPLOY_HOST" bash -s <<EOF
set -euo pipefail
cd "$DEPLOY_DIR"
if [[ ! -d .git ]]; then
  echo "Error: $DEPLOY_DIR is not a git repo. Clone first on the server." >&2
  exit 1
fi
git fetch origin
git checkout "$DEPLOY_BRANCH"
git pull --ff-only origin "$DEPLOY_BRANCH"
docker compose up -d --build
docker compose ps
echo "--- last logs ---"
docker compose logs --tail=40
EOF

echo "== Done =="
