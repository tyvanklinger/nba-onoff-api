#!/bin/bash
cd ~/Documents/nba-onoff-api

echo "=========================================="
echo "Funnels refresh: $(date)"
echo "=========================================="

# Remove any stale lock file
rm -f .git/index.lock

# Pull latest first
git stash
git pull || true
git stash pop || true

# Run the script
/opt/homebrew/bin/python3 funnels_api.py

# Commit and push
git add .
git commit -m "Funnels refresh $(date +'%Y-%m-%d %H:%M')" || true
git pull --rebase || git pull || true
git push

echo "✓ Done: $(date)"
