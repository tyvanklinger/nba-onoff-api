#!/usr/bin/env python3
"""
Export on/off cache data to JSON files for the website frontend.
Run this after --update to generate fresh data for the website.
"""

import json
import os
from pathlib import Path
from collections import defaultdict

# Paths
CACHE_DIR = Path(__file__).parent / "onoff_cache"
OUTPUT_DIR = Path(__file__).parent.parent / "public" / "data" / "onoff"

TEAMS = [
    "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets",
    "Chicago Bulls", "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets",
    "Detroit Pistons", "Golden State Warriors", "Houston Rockets", "Indiana Pacers",
    "Los Angeles Clippers", "Los Angeles Lakers", "Memphis Grizzlies", "Miami Heat",
    "Milwaukee Bucks", "Minnesota Timberwolves", "New Orleans Pelicans", "New York Knicks",
    "Oklahoma City Thunder", "Orlando Magic", "Philadelphia 76ers", "Phoenix Suns",
    "Portland Trail Blazers", "Sacramento Kings", "San Antonio Spurs", "Toronto Raptors",
    "Utah Jazz", "Washington Wizards"
]

def calculate_usg(fga, fta, tov, team_fga, team_fta, team_tov):
    """Calculate usage rate"""
    player_poss = fga + 0.44 * fta + tov
    team_poss = team_fga + 0.44 * team_fta + team_tov
    if team_poss == 0:
        return 0
    return 100 * player_poss / team_poss

def process_team(team_name, season="2025-26"):
    """Process a team's cache and return stats"""
    cache_file = CACHE_DIR / f"{team_name.replace(' ', '_')}_{season}_combo.json"
    
    if not cache_file.exists():
        print(f"  ⚠️  Cache not found: {team_name}")
        return None
    
    with open(cache_file, 'r') as f:
        cache = json.load(f)
    
    events = cache.get('events', [])
    roster = cache.get('roster', [])
    
    # Calculate stats for all players (no filter)
    player_stats = defaultdict(lambda: defaultdict(float))
    player_time = defaultdict(float)
    player_team_stats = defaultdict(lambda: defaultdict(float))
    
    for ev in events:
        pid = ev['player_id']
        player_time[pid] += ev.get('time', 0)
        
        for stat, val in ev.get('stats', {}).items():
            player_stats[pid][stat] += val
        
        if ev.get('is_team_stat'):
            lineup = set(ev['lineup'])
            for stat in ['FGA', 'FTA', 'TOV']:
                if stat in ev.get('stats', {}):
                    for player_on_court in lineup:
                        player_team_stats[player_on_court][stat] += ev['stats'][stat]
    
    # Build results
    results = []
    for teammate in roster:
        pid = teammate['id']
        mins = player_time.get(pid, 0) / 60
        
        if mins < 5:
            continue
        
        stats = player_stats.get(pid, {})
        mult = 36 / mins if mins > 0 else 0
        
        fga = stats.get('FGA', 0)
        fta = stats.get('FTA', 0)
        tov = stats.get('TOV', 0)
        fg3a = stats.get('FG3A', 0)
        fg3m = stats.get('FG3M', 0)
        fgm = stats.get('FGM', 0)
        pts = stats.get('PTS', 0)
        reb = stats.get('REB', 0)
        ast = stats.get('AST', 0)
        
        usg = calculate_usg(fga, fta, tov,
                           player_team_stats[pid]['FGA'],
                           player_team_stats[pid]['FTA'],
                           player_team_stats[pid]['TOV'])
        
        results.append({
            'id': pid,
            'name': teammate['name'],
            'pos': teammate.get('pos', ''),
            'min': round(mins, 1),
            'usg': round(usg, 1),
            'pts': round(pts * mult, 1),
            'reb': round(reb * mult, 1),
            'ast': round(ast * mult, 1),
            'fg3m': round(fg3m * mult, 1),
            'fg3a': round(fg3a * mult, 1),
            'fg3_pct': round(100 * fg3m / fg3a, 1) if fg3a > 0 else 0,
            'fgm': round(fgm * mult, 1),
            'fga': round(fga * mult, 1),
            'fg_pct': round(100 * fgm / fga, 1) if fga > 0 else 0,
            'tov': round(tov * mult, 1),
            'pra': round((pts + reb + ast) * mult, 1),
            'pr': round((pts + reb) * mult, 1),
            'pa': round((pts + ast) * mult, 1),
        })
    
    # Sort by minutes
    results.sort(key=lambda x: x['min'], reverse=True)
    
    return {
        'team': team_name,
        'season': season,
        'games': cache.get('games_processed', 0),
        'updated': cache.get('built_at', ''),
        'roster': [{'id': p['id'], 'name': p['name']} for p in roster],
        'players': results
    }

def main():
    print("\n🏀 Exporting On/Off Data for Website")
    print("=" * 50)
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    all_teams = []
    
    for team in TEAMS:
        print(f"  Processing {team}...")
        data = process_team(team)
        
        if data:
            # Save individual team file
            slug = team.lower().replace(' ', '-')
            output_file = OUTPUT_DIR / f"{slug}.json"
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            all_teams.append({
                'name': team,
                'slug': slug,
                'games': data['games'],
                'updated': data['updated']
            })
    
    # Save teams index
    index_file = OUTPUT_DIR / "teams.json"
    with open(index_file, 'w') as f:
        json.dump({'teams': all_teams}, f, indent=2)
    
    print("\n" + "=" * 50)
    print(f"✅ Exported {len(all_teams)} teams to {OUTPUT_DIR}")
    print(f"✅ Teams index: {index_file}")

if __name__ == "__main__":
    main()
