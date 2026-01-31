#!/bin/bash
cd ~/Documents/nba-onoff-api

echo "=========================================="
echo "4 AM Data Refresh: $(date)"
echo "=========================================="

<<<<<<< Updated upstream
# Remove any stale lock file
rm -f .git/index.lock

# Pull latest first
git stash
git pull || true
git stash pop || true

echo ""
echo ">>> Updating Minutes data..."
/opt/homebrew/bin/python3 generate_minutes.py

echo ""
echo ">>> Updating On/Off data..."
./update-all-teams.sh

echo ""
echo ">>> Committing and pushing..."
git add .
git commit -m "🏀 Auto-update NBA data $(date +'%Y-%m-%d')" || true
git pull --rebase || git pull || true
git push
=======
echo ">>> Updating Minutes data..."
/opt/homebrew/bin/python3 generate_minutes.py

echo ">>> Updating On/Off data..."
./update-all-teams.sh

echo ">>> Pushing..."
git add .
git commit -m "4 AM refresh $(date +'%Y-%m-%d %H:%M')" || true
git pull --rebase || git rebase --abort
git push || echo "Push failed"
>>>>>>> Stashed changes

echo "✓ Done: $(date)"
