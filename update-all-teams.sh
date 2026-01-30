#!/bin/bash
cd /Users/tyvanklinger/Documents/nba-onoff-api

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

for team in "${teams[@]}"; do
  echo "Updating $team..."
  /opt/homebrew/bin/python3 "python/${team} 2025-2026.py" --update
  sleep 2
done

git add -A
git commit -m "🏀 Auto-update NBA on/off data $(date +'%Y-%m-%d')"
git push
