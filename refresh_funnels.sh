#!/bin/bash
cd ~/Documents/nba-onoff-api

echo "=========================================="
echo "Funnels refresh: $(date)"
echo "=========================================="

/opt/homebrew/bin/python3 funnels_api.py

git add .
git commit -m "Funnels refresh $(date +'%Y-%m-%d %H:%M')"
git pull --rebase || git rebase --abort
git push

echo "✓ Done: $(date)"
