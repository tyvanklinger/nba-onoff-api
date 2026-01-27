#!/bin/bash
# 4 AM ET - Refresh minutes data after last night's games
cd ~/Documents/nba-onoff-api

echo "=========================================="
echo "Minutes data refresh: $(date)"
echo "=========================================="

python3 generate_minutes.py

git add minutes_data.json
git commit -m "Minutes refresh $(date +'%Y-%m-%d %H:%M')"
git push

echo "✓ Done: $(date)"
