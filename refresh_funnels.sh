#!/bin/bash
cd ~/Documents/nba-onoff-api

echo "=========================================="
echo "Funnels refresh: $(date)"
echo "=========================================="

<<<<<<< Updated upstream
# Remove any stale lock file
rm -f .git/index.lock

# Pull latest first
git stash
git pull || true
git stash pop || true
=======
# Stash any local changes first
git stash

# Pull latest
git pull --rebase || git pull
>>>>>>> Stashed changes

# Run the script
/opt/homebrew/bin/python3 funnels_api.py

# Commit and push
git add .
<<<<<<< Updated upstream
git commit -m "Funnels refresh $(date +'%Y-%m-%d %H:%M')" || true
git pull --rebase || git pull || true
=======
git commit -m "Funnels refresh $(date +'%Y-%m-%d %H:%M')"
git pull --rebase || git pull
>>>>>>> Stashed changes
git push

echo "✓ Done: $(date)"
