#!/bin/bash
# 11 PM ET - Refresh funnels for tomorrow's games
cd ~/Documents/nba-onoff-api

echo "=========================================="
echo "Funnels refresh: $(date)"
echo "=========================================="

python3 funnels_api.py

git add funnels_data.json
git commit -m "Funnels refresh $(date +'%Y-%m-%d %H:%M')"
git pull --rebase && git push

echo "✓ Done: $(date)"
