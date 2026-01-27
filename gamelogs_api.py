#!/usr/bin/env python3
"""
Game Logs API - Fetches player game logs with teammate availability
Uses leaguegamelog to include traded players
"""

import requests
import json
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Referer': 'https://www.nba.com/',
    'Origin': 'https://www.nba.com',
    'x-nba-stats-origin': 'stats',
    'x-nba-stats-token': 'true'
}

TEAM_IDS = {
    'Atlanta Hawks': 1610612737,
    'Boston Celtics': 1610612738,
    'Brooklyn Nets': 1610612751,
    'Charlotte Hornets': 1610612766,
    'Chicago Bulls': 1610612741,
    'Cleveland Cavaliers': 1610612739,
    'Dallas Mavericks': 1610612742,
    'Denver Nuggets': 1610612743,
    'Detroit Pistons': 1610612765,
    'Golden State Warriors': 1610612744,
    'Houston Rockets': 1610612745,
    'Indiana Pacers': 1610612754,
    'LA Clippers': 1610612746,
    'Los Angeles Lakers': 1610612747,
    'Memphis Grizzlies': 1610612763,
    'Miami Heat': 1610612748,
    'Milwaukee Bucks': 1610612749,
    'Minnesota Timberwolves': 1610612750,
    'New Orleans Pelicans': 1610612740,
    'New York Knicks': 1610612752,
    'Oklahoma City Thunder': 1610612760,
    'Orlando Magic': 1610612753,
    'Philadelphia 76ers': 1610612755,
    'Phoenix Suns': 1610612756,
    'Portland Trail Blazers': 1610612757,
    'Sacramento Kings': 1610612758,
    'San Antonio Spurs': 1610612759,
    'Toronto Raptors': 1610612761,
    'Utah Jazz': 1610612762,
    'Washington Wizards': 1610612764,
}

def get_current_season():
    """Get current NBA season string (e.g., '2025-26')"""
    now = datetime.now()
    year = now.year
    month = now.month
    if month >= 10:
        return f"{year}-{str(year + 1)[2:]}"
    else:
        return f"{year - 1}-{str(year)[2:]}"

def fetch_league_game_logs(season=None):
    """Fetch all player game logs for the entire league"""
    if season is None:
        season = get_current_season()
    
    url = 'https://stats.nba.com/stats/leaguegamelog'
    params = {
        'Counter': 0,
        'Direction': 'DESC',
        'LeagueID': '00',
        'PlayerOrTeam': 'P',
        'Season': season,
        'SeasonType': 'Regular Season',
        'Sorter': 'DATE',
    }
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        headers = data['resultSets'][0]['headers']
        rows = data['resultSets'][0]['rowSet']
        
        return [dict(zip(headers, row)) for row in rows]
    except Exception as e:
        print(f"Error fetching league game logs: {e}")
        return []

def process_team_data(all_games, team_id):
    """Process league game logs for a specific team"""
    
    team_games = [g for g in all_games if g['TEAM_ID'] == team_id]
    
    if not team_games:
        return None, None
    
    games = {}  # game_id -> {date, matchup, active: [player names]}
    players = {}  # player_name -> [{game_id, date, min}]
    
    for g in team_games:
        game_id = g['GAME_ID']
        player = g['PLAYER_NAME']
        minutes = g['MIN'] or 0
        
        if game_id not in games:
            games[game_id] = {
                'date': g['GAME_DATE'],
                'matchup': g['MATCHUP'],
                'active': []
            }
        games[game_id]['active'].append(player)
        
        if player not in players:
            players[player] = []
        players[player].append({
            'game_id': game_id,
            'date': g['GAME_DATE'],
            'min': minutes
        })
    
    # Sort each player's games by date (most recent first)
    for player in players:
        players[player].sort(key=lambda x: x['date'], reverse=True)
    
    return games, players

def calculate_stats(minutes_list):
    """Calculate avg and median from a list of minutes"""
    if not minutes_list:
        return {'avg': 0, 'median': 0, 'games_count': 0}
    
    avg = sum(minutes_list) / len(minutes_list)
    
    sorted_m = sorted(minutes_list)
    n = len(sorted_m)
    if n % 2 == 0:
        median = (sorted_m[n//2 - 1] + sorted_m[n//2]) / 2
    else:
        median = sorted_m[n//2]
    
    return {
        'avg': round(avg, 1),
        'median': round(median, 1),
        'games_count': n
    }

def get_player_stats(players, player_name):
    """Get season and last 10 stats for a player"""
    if player_name not in players:
        return None
    
    games = players[player_name]
    all_mins = [g['min'] for g in games]
    last_10_mins = [g['min'] for g in games[:10]]
    
    return {
        'season': calculate_stats(all_mins),
        'last_10': calculate_stats(last_10_mins)
    }

def get_filtered_stats(games, players, player_name, with_players=None, without_players=None):
    """
    Get minute stats for a player with teammate filters
    
    Args:
        games: {game_id: {date, matchup, active: [player names]}}
        players: {player_name: [{game_id, date, min}]}
        player_name: Player to get stats for
        with_players: List of players who must have played
        without_players: List of players who must NOT have played
    """
    if player_name not in players:
        return {'avg': 0, 'median': 0, 'games_count': 0, 'error': f'Player not found: {player_name}'}
    
    filtered_mins = []
    
    for g in players[player_name]:
        game_id = g['game_id']
        if game_id not in games:
            continue
        
        active = games[game_id]['active']
        
        # Check "with" players - must be active
        if with_players:
            if not all(p in active for p in with_players):
                continue
        
        # Check "without" players - must NOT be active
        if without_players:
            if any(p in active for p in without_players):
                continue
        
        filtered_mins.append(g['min'])
    
    return calculate_stats(filtered_mins)

def fetch_and_process_team(team_name):
    """Main function to fetch and process all data for a team"""
    if team_name not in TEAM_IDS:
        return {'error': f'Team not found: {team_name}'}
    
    team_id = TEAM_IDS[team_name]
    
    print(f"Fetching game logs for {team_name}...")
    all_games = fetch_league_game_logs()
    
    if not all_games:
        return {'error': 'Failed to fetch game logs'}
    
    print("Processing team data...")
    games, players = process_team_data(all_games, team_id)
    
    if not games:
        return {'error': 'No games found for team'}
    
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
    
    return {
        'team': team_name,
        'players': player_list,
        'games': games,
        'player_logs': players
    }


# For testing
if __name__ == "__main__":
    result = fetch_and_process_team("Atlanta Hawks")
    
    if 'error' not in result:
        print(f"\n{result['team']} - {len(result['players'])} players")
        print("-" * 50)
        
        print("All players:")
        for player in result['players']:
            print(f"  {player['name']}")
        
        print("\n" + "-" * 50)
        print("Top 5 by minutes:")
        for player in result['players'][:5]:
            print(f"{player['name']}")
            print(f"  Season: {player['season']['avg']} avg, {player['season']['median']} median ({player['season']['games_count']} games)")
            print(f"  Last 10: {player['last_10']['avg']} avg, {player['last_10']['median']} median")
        
        # Test filtered stats - use exact names from API
        print("\n" + "=" * 50)
        print("Dyson Daniels with Jalen Johnson + NAW, without Trae Young + Kristaps Porziņģis:")
        filtered = get_filtered_stats(
            result['games'],
            result['player_logs'],
            'Dyson Daniels',
            with_players=['Jalen Johnson', 'Nickeil Alexander-Walker'],
            without_players=['Trae Young', 'Kristaps Porziņģis']
        )
        print(f"  Avg: {filtered['avg']}, Median: {filtered['median']} ({filtered['games_count']} games)")
    else:
        print(result['error'])
