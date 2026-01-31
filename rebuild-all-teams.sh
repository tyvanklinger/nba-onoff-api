#!/bin/bash
# Rebuild all 30 NBA team caches from scratch
# This will take approximately 15-20 hours total
# Run with: ./rebuild-all-teams.sh

cd /Users/tyvanklinger/Documents/nba-onoff-api

echo "========================================"
echo "  NBA On/Off Cache - FULL REBUILD"
echo "  This will take ~15-20 hours"
echo "========================================"
echo ""
echo "Starting at: $(date)"
echo ""

teams=(
  "Atlanta Hawks"
  "Boston Celtics"
  "Brooklyn Nets"
  "Charlotte Hornets"
  "Chicago Bulls"
  "Cleveland Cavaliers"
  "Dallas Mavericks"
  "Denver Nuggets"
  "Detroit Pistons"
  "Golden State Warriors"
  "Houston Rockets"
  "Indiana Pacers"
  "Los Angeles Clippers"
  "Los Angeles Lakers"
  "Memphis Grizzlies"
  "Miami Heat"
  "Milwaukee Bucks"
  "Minnesota Timberwolves"
  "New Orleans Pelicans"
  "New York Knicks"
  "Oklahoma City Thunder"
  "Orlando Magic"
  "Philadelphia 76ers"
  "Phoenix Suns"
  "Portland Trail Blazers"
  "Sacramento Kings"
  "San Antonio Spurs"
  "Toronto Raptors"
  "Utah Jazz"
  "Washington Wizards"
)

total=${#teams[@]}
current=0

for team in "${teams[@]}"; do
  current=$((current + 1))
  echo ""
  echo "========================================"
  echo "[$current/$total] Building: $team"
  echo "========================================"
  /opt/homebrew/bin/python3 "python/${team} 2025-2026.py" --build
  
  if [ $? -eq 0 ]; then
    echo "SUCCESS: $team"
  else
    echo "FAILED: $team"
  fi
  
  sleep 5
done

echo ""
echo "========================================"
echo "  REBUILD COMPLETE"
echo "  Finished at: $(date)"
echo "========================================"

echo ""
echo "Pushing to GitHub..."
git add -A
git commit -m "Rebuilt all team caches with traded player fix $(date +'%Y-%m-%d')"
git push

echo "Done!"
