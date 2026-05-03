#!/usr/bin/env bash
# One-shot script to push this project to GitHub.
#
# Usage:  bash push_to_github.sh
#
# Prerequisite:
#   1. You have created an EMPTY repository on GitHub at
#      https://github.com/Allen2Git/nvda-limited-attention
#      (don't tick "Add README/license/gitignore" when creating it)
#   2. git is installed and you are signed in (PAT or SSH).
#
# This script:
#   - Cleans any stale .git from the Cowork VM
#   - Initializes a fresh git repo
#   - Stages + commits with a descriptive message
#   - Pushes to the GitHub origin

set -e

REPO_URL="https://github.com/Allen2Git/nvda-limited-attention.git"
BRANCH="main"

echo ">>> Cleaning stale VM metadata (if any)..."
rm -rf .git _archive 2>/dev/null || true

echo ">>> Initializing fresh git repository..."
git init
git branch -M "${BRANCH}"

echo ">>> Staging files (respecting .gitignore)..."
git add -A

echo ">>> Files that will be committed:"
git diff --cached --stat

echo ">>> Creating initial commit..."
git commit -m "Initial commit: NVDA earnings limited-attention study (MBA course project)

Tsinghua-Cornell MBA course project on testing whether the classic
limited-attention hypothesis (open-hour overshoot followed by
intraday reversal) still holds for NVIDIA earnings in 2020-2026.

Main finding: null result.  beta_1 = +0.06 (t=0.28, R^2=0.006).
85% of the earnings shock is absorbed in pre-market.  Three
mechanism: pre-market institutional trading, real-time social
media, retail pre-market app access.

See README for the research journey (four iterations before we
settled on this topic) and method details."

echo ">>> Linking remote..."
git remote add origin "${REPO_URL}" 2>/dev/null || git remote set-url origin "${REPO_URL}"

echo ">>> Pushing to ${REPO_URL}  (branch: ${BRANCH})..."
echo "    If prompted, use your GitHub username 'Allen2Git' and a"
echo "    Personal Access Token (not your password)."
echo ""
git push -u origin "${BRANCH}"

echo ""
echo ">>> Done!  View your repository at:"
echo "    https://github.com/Allen2Git/nvda-limited-attention"
