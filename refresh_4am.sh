#!/bin/bash
# 4 AM ET - Refresh minutes + on/off data after last night's games
cd ~/Documents/nba-onoff-api

echo "=========================================="
echo "4 AM Data Refresh: $(date)"
echo "=========================================="

# 1. Minutes data
echo ""
echo ">>> Updating Minutes data..."
python3 generate_minutes.py

# 2. On/Off data
echo ""
echo ">>> Updating On/Off data..."
./update-all-teams.sh

# 3. Commit and push all
echo ""
echo ">>> Committing and pushing..."
git add minutes_data.json onoff_cache/
git commit -m "4 AM data refresh $(date +'%Y-%m-%d')"
git pull --rebase && git push

echo ""
echo "✓ Done: $(date)"
