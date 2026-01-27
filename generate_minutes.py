#!/usr/bin/env python3
"""
Generate minutes data for all teams - run locally or via GitHub Action
Saves to minutes_data.json which is committed to repo
"""

from gamelogs_api import fetch_league_game_logs, process_team_data, get_player_stats, TEAM_IDS
import json
from datetime import datetime
import pytz

def generate_all_minutes_data():
    """Fetch and process minutes data for all teams"""
    print("Fetching league game logs...")
    all_games = fetch_league_game_logs()
    
    if not all_games:
        print("ERROR: Failed to fetch game logs")
        return None
    
    print(f"Got {len(all_games)} game log entries")
    
    all_data = {}
    
    for team_name, team_id in TEAM_IDS.items():
        print(f"Processing {team_name}...")
        
        games, players = process_team_data(all_games, team_id)
        
        if not games:
            print(f"  No games found for {team_name}")
            continue
        
        # Build player list with stats
        player_list = []
        for player_name in players:
            stats = get_player_stats(players, player_name)
            player_list.append({
                'name': player_name,
                'season': stats['season'],
                'last_10': stats['last_10']
            })
        
        # Sort by season average minutes
        player_list.sort(key=lambda x: x['season']['avg'], reverse=True)
        
        all_data[team_name] = {
            'players': player_list,
            'games': games,
            'player_logs': players
        }
        
        print(f"  ✓ {len(player_list)} players, {len(games)} games")
    
    return all_data

def save_minutes_data(data, filepath='minutes_data.json'):
    """Save minutes data to JSON file"""
    et = pytz.timezone('US/Eastern')
    
    output = {
        'updated': datetime.now(et).strftime("%Y-%m-%d %H:%M:%S ET"),
        'teams': data
    }
    
    with open(filepath, 'w') as f:
        json.dump(output, f)
    
    print(f"\n✓ Saved to {filepath}")
    print(f"  Updated: {output['updated']}")
    print(f"  Teams: {len(data)}")

if __name__ == "__main__":
    data = generate_all_minutes_data()
    if data:
        save_minutes_data(data)
    else:
        print("Failed to generate data")
        exit(1)
