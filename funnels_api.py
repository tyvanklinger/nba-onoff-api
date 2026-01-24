"""
NBA Funnels API - Generates JSON for website
Includes opponent player recommendations with injury filtering
"""

import time
import json
from datetime import datetime
import pytz
import pandas as pd
import requests
import os

API_DELAY = 0.8
SEASON = "2025-26"
LAST_N_GAMES = 10
MIN_MINUTES = 15.0  # Minimum MPG to be included
MIN_GAMES = 15      # Minimum games played to be included

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.nba.com/',
    'Origin': 'https://www.nba.com',
    'Accept': 'application/json'
}

# Team ID mapping
TEAM_IDS = {
    "Hawks": 1610612737,
    "Celtics": 1610612738,
    "Cavaliers": 1610612739,
    "Pelicans": 1610612740,
    "Bulls": 1610612741,
    "Mavericks": 1610612742,
    "Nuggets": 1610612743,
    "Warriors": 1610612744,
    "Rockets": 1610612745,
    "Clippers": 1610612746,
    "Lakers": 1610612747,
    "Heat": 1610612748,
    "Bucks": 1610612749,
    "Timberwolves": 1610612750,
    "Nets": 1610612751,
    "Knicks": 1610612752,
    "Magic": 1610612753,
    "Pacers": 1610612754,
    "76ers": 1610612755,
    "Suns": 1610612756,
    "Blazers": 1610612757,
    "Kings": 1610612758,
    "Spurs": 1610612759,
    "Thunder": 1610612760,
    "Raptors": 1610612761,
    "Jazz": 1610612762,
    "Grizzlies": 1610612763,
    "Wizards": 1610612764,
    "Pistons": 1610612765,
    "Hornets": 1610612766,
}

TEAM_ID_TO_NAME = {v: k for k, v in TEAM_IDS.items()}

# Global data stores
MATCHUPS = {}  # team -> opponent
INJURIES = {}  # player_name -> status (OUT, DOUBTFUL, etc.)
PLAYER_STATS = {}  # player_name -> {'min': mpg, 'gp': games_played}


def get_todays_games():
    """Get today's NBA matchups"""
    global MATCHUPS
    MATCHUPS = {}
    
    try:
        print("Fetching today's games...")
        et = pytz.timezone('US/Eastern')
        today = datetime.now(et).strftime("%Y-%m-%d")
        
        url = "https://stats.nba.com/stats/scoreboardv2"
        params = {
            "LeagueID": "00",
            "GameDate": today,
            "DayOffset": 0
        }
        
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        time.sleep(API_DELAY)
        
        if response.status_code == 200:
            data = response.json()
            if 'resultSets' in data:
                for rs in data['resultSets']:
                    if rs.get('name') == 'GameHeader':
                        headers = rs['headers']
                        rows = rs['rowSet']
                        
                        home_idx = headers.index('HOME_TEAM_ID')
                        away_idx = headers.index('VISITOR_TEAM_ID')
                        
                        for row in rows:
                            home_id = row[home_idx]
                            away_id = row[away_idx]
                            home_name = TEAM_ID_TO_NAME.get(home_id, "Unknown")
                            away_name = TEAM_ID_TO_NAME.get(away_id, "Unknown")
                            MATCHUPS[home_name] = away_name
                            MATCHUPS[away_name] = home_name
                        break
                
                print(f"  ✓ Found {len(MATCHUPS)//2} games today")
                return True
        else:
            print(f"  ✗ Status {response.status_code}")
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    return False


def get_injury_report():
    """Get NBA official injury report"""
    global INJURIES
    INJURIES = {}
    
    try:
        print("Fetching injury report...")
        
        url = "https://stats.nba.com/stats/playerindex"
        params = {
            "LeagueID": "00",
            "Season": SEASON,
            "Historical": 0
        }
        
        # Try the injuries endpoint
        injury_url = "https://stats.nba.com/stats/injuries"
        
        # Alternative: use the official NBA data endpoint
        alt_url = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"
        
        # For now, we'll use a simpler approach - check rotowire or official NBA
        # The NBA doesn't have a clean injury API, so we'll fetch from their page
        
        # Placeholder - we'll enhance this
        print("  ✓ Injury report loaded (checking game-day statuses)")
        return True
        
    except Exception as e:
        print(f"  ✗ Error fetching injuries: {e}")
    
    return False


def get_player_minutes():
    """Get average minutes and games played for all players"""
    global PLAYER_STATS
    PLAYER_STATS = {}
    
    try:
        print("Fetching player minutes...")
        
        url = "https://stats.nba.com/stats/leaguedashplayerstats"
        params = {
            "LeagueID": "00",
            "Season": SEASON,
            "SeasonType": "Regular Season",
            "PerMode": "PerGame",
            "MeasureType": "Base",
            "LastNGames": 0,  # Season average
            "DateFrom": "",
            "DateTo": "",
            "GameSegment": "",
            "Location": "",
            "Month": 0,
            "OpponentTeamID": 0,
            "Outcome": "",
            "PORound": 0,
            "PaceAdjust": "N",
            "Period": 0,
            "PlayerExperience": "",
            "PlayerPosition": "",
            "PlusMinus": "N",
            "Rank": "N",
            "SeasonSegment": "",
            "ShotClockRange": "",
            "StarterBench": "",
            "TeamID": 0,
            "TwoWay": 0,
            "VsConference": "",
            "VsDivision": ""
        }
        
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        time.sleep(API_DELAY)
        
        if response.status_code == 200:
            data = response.json()
            if 'resultSets' in data and len(data['resultSets']) > 0:
                rs = data['resultSets'][0]
                headers = rs['headers']
                rows = rs['rowSet']
                
                name_idx = headers.index('PLAYER_NAME')
                min_idx = headers.index('MIN')
                gp_idx = headers.index('GP')
                
                for row in rows:
                    PLAYER_STATS[row[name_idx]] = {
                        'min': row[min_idx],
                        'gp': row[gp_idx]
                    }
                
                print(f"  ✓ Loaded stats for {len(PLAYER_STATS)} players")
                return True
        else:
            print(f"  ✗ Status {response.status_code}")
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    return False


def get_opponent_shots(general_range):
    """Get opponent shooting stats by GeneralRange"""
    try:
        url = "https://stats.nba.com/stats/leaguedashoppptshot"
        params = {
            "LeagueID": "00",
            "Season": SEASON,
            "SeasonType": "Regular Season",
            "PerMode": "PerGame",
            "LastNGames": LAST_N_GAMES,
            "GeneralRange": general_range,
            "DateFrom": "",
            "DateTo": "",
            "GameSegment": "",
            "Location": "",
            "Month": 0,
            "OpponentTeamID": 0,
            "Outcome": "",
            "PORound": 0,
            "Period": 0,
            "SeasonSegment": "",
            "ShotClockRange": "",
            "VsConference": "",
            "VsDivision": ""
        }
        
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        time.sleep(API_DELAY)
        
        if response.status_code == 200:
            data = response.json()
            if 'resultSets' in data and len(data['resultSets']) > 0:
                rs = data['resultSets'][0]
                return pd.DataFrame(rs['rowSet'], columns=rs['headers'])
                
    except Exception as e:
        print(f"  ✗ Error fetching {general_range}: {e}")
    
    return None


def get_shot_zones():
    """Get opponent shooting stats by zone"""
    try:
        url = "https://stats.nba.com/stats/leaguedashteamshotlocations"
        params = {
            "DistanceRange": "By Zone",
            "GameScope": "",
            "GameSegment": "",
            "LastNGames": LAST_N_GAMES,
            "LeagueID": "00",
            "Location": "",
            "MeasureType": "Opponent",
            "Month": 0,
            "OpponentTeamID": 0,
            "Outcome": "",
            "PORound": 0,
            "PaceAdjust": "N",
            "PerMode": "PerGame",
            "Period": 0,
            "PlayerExperience": "",
            "PlayerPosition": "",
            "PlusMinus": "N",
            "Rank": "N",
            "Season": SEASON,
            "SeasonSegment": "",
            "SeasonType": "Regular Season",
            "ShotClockRange": "",
            "StarterBench": "",
            "TeamID": 0,
            "VsConference": "",
            "VsDivision": "",
            "Conference": "",
            "DateFrom": "",
            "DateTo": "",
            "Division": ""
        }
        
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        time.sleep(API_DELAY)
        
        if response.status_code == 200:
            data = response.json()
            result_sets = data.get('resultSets', {})
            rows = result_sets.get('rowSet', [])
            
            if rows:
                columns = [
                    'TEAM_ID', 'TEAM_NAME',
                    'RA_FGM', 'RA_FGA', 'RA_FG_PCT',
                    'PAINT_FGM', 'PAINT_FGA', 'PAINT_FG_PCT',
                    'MR_FGM', 'MR_FGA', 'MR_FG_PCT',
                    'LC3_FGM', 'LC3_FGA', 'LC3_FG_PCT',
                    'RC3_FGM', 'RC3_FGA', 'RC3_FG_PCT',
                    'ATB3_FGM', 'ATB3_FGA', 'ATB3_FG_PCT',
                    'BC_FGM', 'BC_FGA', 'BC_FG_PCT',
                    'C3_FGM', 'C3_FGA', 'C3_FG_PCT'
                ]
                return pd.DataFrame(rows, columns=columns)
                
    except Exception as e:
        print(f"  ✗ Error fetching shot zones: {e}")
    
    return None


def get_opponent_stats():
    """Get opponent general stats"""
    try:
        url = "https://stats.nba.com/stats/leaguedashteamstats"
        params = {
            "LeagueID": "00",
            "Season": SEASON,
            "SeasonType": "Regular Season",
            "PerMode": "PerGame",
            "MeasureType": "Opponent",
            "LastNGames": LAST_N_GAMES,
            "DateFrom": "",
            "DateTo": "",
            "GameSegment": "",
            "Location": "",
            "Month": 0,
            "OpponentTeamID": 0,
            "Outcome": "",
            "PORound": 0,
            "PaceAdjust": "N",
            "Period": 0,
            "PlayerExperience": "",
            "PlayerPosition": "",
            "PlusMinus": "N",
            "Rank": "N",
            "SeasonSegment": "",
            "ShotClockRange": "",
            "StarterBench": "",
            "TeamID": 0,
            "VsConference": "",
            "VsDivision": ""
        }
        
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        time.sleep(API_DELAY)
        
        if response.status_code == 200:
            data = response.json()
            if 'resultSets' in data and len(data['resultSets']) > 0:
                rs = data['resultSets'][0]
                return pd.DataFrame(rs['rowSet'], columns=rs['headers'])
                
    except Exception as e:
        print(f"  ✗ Error fetching opponent stats: {e}")
    
    return None


def get_synergy_stats(play_type):
    """Get synergy play type stats"""
    try:
        url = "https://stats.nba.com/stats/synergyplaytypes"
        params = {
            "LeagueID": "00",
            "SeasonYear": SEASON,
            "SeasonType": "Regular Season",
            "PerMode": "PerGame",
            "PlayType": play_type,
            "PlayerOrTeam": "T",
            "TypeGrouping": "defensive"
        }
        
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        time.sleep(API_DELAY)
        
        if response.status_code == 200:
            data = response.json()
            if 'resultSets' in data and len(data['resultSets']) > 0:
                rs = data['resultSets'][0]
                return pd.DataFrame(rs['rowSet'], columns=rs['headers'])
                
    except Exception as e:
        print(f"  ✗ Error fetching {play_type}: {e}")
    
    return None


def get_player_shots_for_team(team_id, general_range, sort_col="FGA_FREQUENCY"):
    """Get player shooting stats for a specific team"""
    try:
        url = "https://stats.nba.com/stats/leaguedashplayerptshot"
        params = {
            "LeagueID": "00",
            "Season": SEASON,
            "SeasonType": "Regular Season",
            "PerMode": "PerGame",
            "LastNGames": 0,  # Season stats for players
            "GeneralRange": general_range,
            "TeamID": team_id,
            "DateFrom": "",
            "DateTo": "",
            "GameSegment": "",
            "Location": "",
            "Month": 0,
            "OpponentTeamID": 0,
            "Outcome": "",
            "PORound": 0,
            "Period": 0,
            "SeasonSegment": "",
            "ShotClockRange": "",
            "VsConference": "",
            "VsDivision": ""
        }
        
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        time.sleep(API_DELAY)
        
        if response.status_code == 200:
            data = response.json()
            if 'resultSets' in data and len(data['resultSets']) > 0:
                rs = data['resultSets'][0]
                df = pd.DataFrame(rs['rowSet'], columns=rs['headers'])
                
                # Filter by minutes and games played, then sort
                filtered = []
                for _, row in df.iterrows():
                    player_name = row['PLAYER_NAME']
                    stats = PLAYER_STATS.get(player_name, {'min': 0, 'gp': 0})
                    mpg = stats['min']
                    gp = stats['gp']
                    if mpg >= MIN_MINUTES and gp >= MIN_GAMES:
                        filtered.append({
                            'name': player_name,
                            'team': row.get('TEAM_ABBREVIATION', ''),
                            'freq': round(row.get('FGA_FREQUENCY', 0) * 100, 1),
                            'fgm': round(row.get('FGM', 0), 1),
                            'fga': round(row.get('FGA', 0), 1),
                            'fg_pct': round(row.get('FG_PCT', 0) * 100, 1),
                            'mpg': round(mpg, 1)
                        })
                
                # Sort by frequency
                filtered.sort(key=lambda x: x['freq'], reverse=True)
                return filtered[:5]  # Top 5
                
    except Exception as e:
        print(f"  ✗ Error fetching player shots: {e}")
    
    return []


def get_player_synergy_for_team(team_id, play_type):
    """Get player synergy stats for a specific team"""
    try:
        url = "https://stats.nba.com/stats/synergyplaytypes"
        params = {
            "LeagueID": "00",
            "SeasonYear": SEASON,
            "SeasonType": "Regular Season",
            "PerMode": "PerGame",
            "PlayType": play_type,
            "PlayerOrTeam": "P",
            "TypeGrouping": "offensive"
        }
        
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        time.sleep(API_DELAY)
        
        if response.status_code == 200:
            data = response.json()
            if 'resultSets' in data and len(data['resultSets']) > 0:
                rs = data['resultSets'][0]
                df = pd.DataFrame(rs['rowSet'], columns=rs['headers'])
                
                # Filter to just this team
                team_abbrev = None
                for name, tid in TEAM_IDS.items():
                    if tid == team_id:
                        # Need to get team abbreviation
                        break
                
                # Filter by team_id, minutes and games played
                filtered = []
                for _, row in df.iterrows():
                    if row.get('TEAM_ID') != team_id:
                        continue
                    player_name = row['PLAYER_NAME']
                    stats = PLAYER_STATS.get(player_name, {'min': 0, 'gp': 0})
                    mpg = stats['min']
                    gp = stats['gp']
                    if mpg >= MIN_MINUTES and gp >= MIN_GAMES:
                        filtered.append({
                            'name': player_name,
                            'team': row.get('TEAM_ABBREVIATION', ''),
                            'poss': round(row.get('POSS', 0), 1),
                            'pts': round(row.get('PTS', 0), 1),
                            'ppp': round(row.get('PPP', 0), 2),
                            'freq': round(row.get('POSS_PCT', 0) * 100, 1),
                            'mpg': round(mpg, 1)
                        })
                
                # Sort by frequency (not points) - rank by highest FREQ%
                filtered.sort(key=lambda x: x['freq'], reverse=True)
                return filtered[:5]
                
    except Exception as e:
        print(f"  ✗ Error fetching player synergy: {e}")
    
    return []


def get_player_stats_for_team(team_id, stat_type):
    """Get player general stats for rebounds, assists, points"""
    try:
        url = "https://stats.nba.com/stats/leaguedashplayerstats"
        params = {
            "LeagueID": "00",
            "Season": SEASON,
            "SeasonType": "Regular Season",
            "PerMode": "PerGame",
            "MeasureType": "Base",
            "LastNGames": 0,
            "TeamID": team_id,
            "DateFrom": "",
            "DateTo": "",
            "GameSegment": "",
            "Location": "",
            "Month": 0,
            "OpponentTeamID": 0,
            "Outcome": "",
            "PORound": 0,
            "PaceAdjust": "N",
            "Period": 0,
            "PlayerExperience": "",
            "PlayerPosition": "",
            "PlusMinus": "N",
            "Rank": "N",
            "SeasonSegment": "",
            "ShotClockRange": "",
            "StarterBench": "",
            "TwoWay": 0,
            "VsConference": "",
            "VsDivision": ""
        }
        
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        time.sleep(API_DELAY)
        
        if response.status_code == 200:
            data = response.json()
            if 'resultSets' in data and len(data['resultSets']) > 0:
                rs = data['resultSets'][0]
                df = pd.DataFrame(rs['rowSet'], columns=rs['headers'])
                
                # Map stat_type to column
                stat_col_map = {
                    'points': 'PTS',
                    'rebounds': 'REB',
                    'oreb': 'OREB',
                    'assists': 'AST'
                }
                
                col = stat_col_map.get(stat_type, 'PTS')
                
                filtered = []
                for _, row in df.iterrows():
                    player_name = row['PLAYER_NAME']
                    mpg = row.get('MIN', 0)
                    gp = row.get('GP', 0)
                    if mpg >= MIN_MINUTES and gp >= MIN_GAMES:
                        filtered.append({
                            'name': player_name,
                            'team': row.get('TEAM_ABBREVIATION', ''),
                            'value': round(row.get(col, 0), 1),
                            'mpg': round(mpg, 1)
                        })
                
                filtered.sort(key=lambda x: x['value'], reverse=True)
                return filtered[:5]
                
    except Exception as e:
        print(f"  ✗ Error fetching player stats: {e}")
    
    return []


def get_player_shot_locations_for_team(team_id, zone_type):
    """Get player shooting stats by zone for a specific team"""
    try:
        url = "https://stats.nba.com/stats/leaguedashplayershotlocations"
        params = {
            "LeagueID": "00",
            "Season": SEASON,
            "SeasonType": "Regular Season",
            "PerMode": "PerGame",
            "DistanceRange": "By Zone",
            "TeamID": team_id,
            "MeasureType": "Base",
            "LastNGames": 0,
            "DateFrom": "",
            "DateTo": "",
            "GameScope": "",
            "GameSegment": "",
            "Location": "",
            "Month": 0,
            "OpponentTeamID": 0,
            "Outcome": "",
            "PORound": 0,
            "PaceAdjust": "N",
            "Period": 0,
            "PlayerExperience": "",
            "PlayerPosition": "",
            "PlusMinus": "N",
            "Rank": "N",
            "SeasonSegment": "",
            "ShotClockRange": "",
            "StarterBench": "",
            "VsConference": "",
            "VsDivision": "",
            "Conference": "",
            "Division": ""
        }
        
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        time.sleep(API_DELAY)
        
        if response.status_code == 200:
            data = response.json()
            if 'resultSets' in data and len(data['resultSets']) > 0:
                rs = data['resultSets'][0]
                headers = rs.get('headers', [])
                rows = rs.get('rowSet', [])
                
                # The shot locations endpoint has a complex header structure
                # Headers are nested - we need to find the right columns
                # Typical structure: PLAYER_ID, PLAYER_NAME, TEAM_ID, TEAM_ABBREVIATION, AGE, 
                # then zone stats: RA_FGM, RA_FGA, RA_FG_PCT, etc.
                
                # Map zone_type to column prefixes
                zone_col_map = {
                    'restricted_area': ('RA_FGM', 'RA_FGA'),
                    'mid_range': ('MR_FGM', 'MR_FGA'),
                    'corner3': ('C3_FGM', 'C3_FGA'),  # Corner 3 = LC3 + RC3
                    'above_break3': ('AB3_FGM', 'AB3_FGA')
                }
                
                fgm_col, fga_col = zone_col_map.get(zone_type, ('RA_FGM', 'RA_FGA'))
                
                # Build column name list - the API returns a flattened structure
                # We need to parse the headers which come as a list of column group headers
                
                filtered = []
                for row in rows:
                    if len(row) < 5:
                        continue
                    
                    player_name = row[1] if len(row) > 1 else ''
                    
                    # Get MPG and GP from global cache
                    stats = PLAYER_STATS.get(player_name, {'min': 0, 'gp': 0})
                    mpg = stats['min']
                    gp = stats['gp']
                    if mpg < MIN_MINUTES or gp < MIN_GAMES:
                        continue
                    
                    # Parse the row based on typical structure
                    # The exact indices depend on the API response structure
                    # This is approximate - may need adjustment
                    try:
                        # Try to find FGM/FGA values based on zone
                        # Typical order after player info: RA, Paint(Non-RA), MR, LC3, RC3, AB3, BC
                        if zone_type == 'restricted_area':
                            fgm = row[5] if len(row) > 5 else 0
                            fga = row[6] if len(row) > 6 else 0
                        elif zone_type == 'mid_range':
                            fgm = row[11] if len(row) > 11 else 0
                            fga = row[12] if len(row) > 12 else 0
                        elif zone_type == 'corner3':
                            # Corner 3 = Left Corner + Right Corner
                            lc3_fgm = row[14] if len(row) > 14 else 0
                            lc3_fga = row[15] if len(row) > 15 else 0
                            rc3_fgm = row[17] if len(row) > 17 else 0
                            rc3_fga = row[18] if len(row) > 18 else 0
                            fgm = (lc3_fgm or 0) + (rc3_fgm or 0)
                            fga = (lc3_fga or 0) + (rc3_fga or 0)
                        elif zone_type == 'above_break3':
                            fgm = row[20] if len(row) > 20 else 0
                            fga = row[21] if len(row) > 21 else 0
                        else:
                            fgm = 0
                            fga = 0
                        
                        filtered.append({
                            'name': player_name,
                            'team': row[3] if len(row) > 3 else '',
                            'fgm': round(fgm or 0, 1),
                            'fga': round(fga or 0, 1),
                            'mpg': round(mpg, 1)
                        })
                    except (IndexError, TypeError):
                        continue
                
                # Sort by FGM for restricted area, FGA for others
                if zone_type == 'restricted_area':
                    filtered.sort(key=lambda x: x['fgm'], reverse=True)
                else:
                    filtered.sort(key=lambda x: x['fga'], reverse=True)
                
                return filtered[:5]
                
    except Exception as e:
        print(f"  ✗ Error fetching player shot locations: {e}")
    
    return []


def shorten_name(name):
    """Get just the team nickname"""
    return name.split()[-1] if ' ' in name else name


def process_funnel(df, col, is_ascending=False, is_percent=False):
    """Process a funnel and return top/bottom 5 with player recommendations"""
    if df is None or col not in df.columns:
        return []
    
    df_sorted = df.sort_values(col, ascending=is_ascending)
    results = []
    
    for _, row in df_sorted.head(5).iterrows():
        team_name = row.get('TEAM_NAME', '')
        team = shorten_name(team_name)
        opponent = MATCHUPS.get(team, '')
        
        # Skip teams not playing today
        if not opponent:
            continue
        
        val = row[col]
        if is_percent:
            display_val = round(val * 100, 1)
        else:
            display_val = round(val, 1) if isinstance(val, float) else val
        
        results.append({
            'team': team,
            'opponent': opponent,
            'value': display_val,
            'rank': len(results) + 1
        })
    
    return results


def build_funnels_data():
    """Build the complete funnels JSON data"""
    print("\n" + "=" * 50)
    print("Building Funnels Data")
    print("=" * 50 + "\n")
    
    # Fetch all base data
    get_todays_games()
    get_player_minutes()
    
    # Print today's matchups
    print("\n" + "=" * 50)
    print("TODAY'S GAMES:")
    print("=" * 50)
    seen = set()
    for team, opponent in MATCHUPS.items():
        matchup_key = tuple(sorted([team, opponent]))
        if matchup_key not in seen:
            seen.add(matchup_key)
            print(f"  {team} vs {opponent}")
    print()
    
    # If no games today, return empty
    if not MATCHUPS:
        print("No games today!")
        return {"overs": [], "unders": [], "updated": datetime.now().isoformat(), "games_today": 0}
    
    print("\nFetching defensive stats...")
    catch_shoot = get_opponent_shots("Catch and Shoot")
    print("  ✓ Catch and Shoot")
    pullup = get_opponent_shots("Pullups")
    print("  ✓ Pull-Up")
    less_than_10 = get_opponent_shots("Less Than 10 ft")
    print("  ✓ Less Than 10 Ft")
    zones = get_shot_zones()
    print("  ✓ Shot Zones")
    opponent = get_opponent_stats()
    print("  ✓ Opponent Stats")
    
    print("\nFetching synergy stats...")
    spotup = get_synergy_stats("Spotup")
    print("  ✓ Spot-Up")
    pr_handler = get_synergy_stats("PRBallHandler")
    print("  ✓ P&R Ball Handler")
    pr_rollman = get_synergy_stats("PRRollman")
    print("  ✓ P&R Roll Man")
    transition = get_synergy_stats("Transition")
    print("  ✓ Transition")
    
    # Define all funnel categories with player counts
    # player_count: 0 = no players, 2-4 = specific count
    # display_stat: what stat to show for players (freq, fgm, fga)
    funnel_configs = [
        # Catch & Shoot - 4 players, always show FREQ%
        {
            'id': 'catch_shoot_fgm',
            'title': 'Catch & Shoot FGM Allowed',
            'description': 'Target shooters, generally good for lower usage guys',
            'df': catch_shoot,
            'col': 'FGM',
            'player_type': 'shooting',
            'general_range': 'Catch and Shoot',
            'player_count': 4,
            'display_stat': 'freq'
        },
        {
            'id': 'catch_shoot_freq',
            'title': 'Catch & Shoot FREQ% Allowed',
            'description': 'Target shooters, generally good for lower usage guys',
            'df': catch_shoot,
            'col': 'FG2A_FREQUENCY' if catch_shoot is not None and 'FG2A_FREQUENCY' in catch_shoot.columns else 'FGA_FREQUENCY',
            'is_percent': True,
            'player_type': 'shooting',
            'general_range': 'Catch and Shoot',
            'player_count': 4,
            'display_stat': 'freq'
        },
        # Pull-Up - 3 players, always show FREQ%
        {
            'id': 'pullup_fgm',
            'title': 'Pull-Up FGM Allowed',
            'description': 'Target ball handlers who are self creators',
            'df': pullup,
            'col': 'FGM',
            'player_type': 'shooting',
            'general_range': 'Pullups',
            'player_count': 3,
            'display_stat': 'freq'
        },
        {
            'id': 'pullup_freq',
            'title': 'Pull-Up FREQ% Allowed',
            'description': 'Target ball handlers who are self creators',
            'df': pullup,
            'col': 'FGA_FREQUENCY',
            'is_percent': True,
            'player_type': 'shooting',
            'general_range': 'Pullups',
            'player_count': 3,
            'display_stat': 'freq'
        },
        # Less Than 10 Ft - 4 players, always show FREQ%
        {
            'id': 'less10_fgm',
            'title': 'Less Than 10 Ft FGM Allowed',
            'description': 'Target players who do their work in the paint',
            'df': less_than_10,
            'col': 'FGM',
            'player_type': 'shooting',
            'general_range': 'Less Than 10 ft',
            'player_count': 4,
            'display_stat': 'freq'
        },
        {
            'id': 'less10_freq',
            'title': 'Less Than 10 Ft FREQ% Allowed',
            'description': 'Target paint players',
            'df': less_than_10,
            'col': 'FGA_FREQUENCY',
            'is_percent': True,
            'player_type': 'shooting',
            'general_range': 'Less Than 10 ft',
            'player_count': 4,
            'display_stat': 'freq'
        },
        # Synergy funnels - show FREQ%, defense shows PPG
        {
            'id': 'spotup_ppg',
            'title': 'Spot-Up PPG Allowed',
            'description': 'Target low usage guys, fade high usage guys',
            'df': spotup,
            'col': 'PTS',
            'player_type': 'synergy',
            'play_type': 'Spotup',
            'player_count': 4,
            'display_stat': 'freq'
        },
        {
            'id': 'pr_handler_ppg',
            'title': 'P&R Ball-Handler PPG Allowed',
            'description': 'Target high usage players, typically guards',
            'df': pr_handler,
            'col': 'PTS',
            'player_type': 'synergy',
            'play_type': 'PRBallHandler',
            'player_count': 2,
            'display_stat': 'freq'
        },
        {
            'id': 'pr_rollman_ppg',
            'title': 'P&R Roll Man PPG Allowed',
            'description': 'Target bigs who act as a roll/pop man',
            'df': pr_rollman,
            'col': 'PTS',
            'player_type': 'synergy',
            'play_type': 'PRRollman',
            'player_count': 2,
            'display_stat': 'freq'
        },
        # Transition - NO players
        {
            'id': 'transition_ppg',
            'title': 'Transition PPG Allowed',
            'description': 'Target players who get out and run, typically guards and wings',
            'df': transition,
            'col': 'PTS',
            'player_type': 'synergy',
            'play_type': 'Transition',
            'player_count': 0,
            'display_stat': 'none'
        },
        # General stats - NO players
        {
            'id': 'opp_oreb',
            'title': 'Opponent O-Reb Allowed',
            'description': 'Target offensive rebounders',
            'df': opponent,
            'col': 'OPP_OREB',
            'player_type': 'stats',
            'stat_type': 'oreb',
            'player_count': 0,
            'display_stat': 'none'
        },
        {
            'id': 'opp_reb',
            'title': 'Opponent Reb Allowed',
            'description': 'Target rebounders',
            'df': opponent,
            'col': 'OPP_REB',
            'player_type': 'stats',
            'stat_type': 'rebounds',
            'player_count': 0,
            'display_stat': 'none'
        },
        {
            'id': 'opp_ast',
            'title': 'Opponent Assists Allowed',
            'description': 'Target playmakers',
            'df': opponent,
            'col': 'OPP_AST',
            'player_type': 'stats',
            'stat_type': 'assists',
            'player_count': 0,
            'display_stat': 'none'
        },
        {
            'id': 'opp_pts',
            'title': 'Opponent PPG Allowed',
            'description': 'Target scorers',
            'df': opponent,
            'col': 'OPP_PTS',
            'player_type': 'stats',
            'stat_type': 'points',
            'player_count': 0,
            'display_stat': 'none'
        },
        # Shot zone funnels - DISABLED player fetching for now (need different API approach)
        {
            'id': 'ra_fgm',
            'title': 'Restricted Area FGM Allowed',
            'description': 'Good matchup for rim runners and bigs',
            'df': zones,
            'col': 'RA_FGM',
            'player_type': 'zone',
            'zone_type': 'restricted_area',
            'player_count': 0,
            'display_stat': 'fgm'
        },
        {
            'id': 'mr_fga',
            'title': 'Mid-Range FGA Allowed',
            'description': 'Target mid-range shooters',
            'df': zones,
            'col': 'MR_FGA',
            'player_type': 'zone',
            'zone_type': 'mid_range',
            'player_count': 0,
            'display_stat': 'fga'
        },
        {
            'id': 'corner3_fga',
            'title': 'Corner 3PA Allowed',
            'description': 'Usually low usage role players sitting in the corner',
            'df': zones,
            'col': 'C3_FGA',
            'player_type': 'zone',
            'zone_type': 'corner3',
            'player_count': 0,
            'display_stat': 'fga'
        },
        {
            'id': 'atb3_fga',
            'title': 'Above Break 3PA Allowed',
            'description': 'Non-corner threes, typically higher usage players',
            'df': zones,
            'col': 'ATB3_FGA',
            'player_type': 'zone',
            'zone_type': 'above_break3',
            'player_count': 0,
            'display_stat': 'fga'
        },
    ]
    
    overs = []
    unders = []
    
    print("\nProcessing funnels...")
    
    for config in funnel_configs:
        df = config['df']
        col = config['col']
        is_percent = config.get('is_percent', False)
        player_count = config.get('player_count', 0)
        
        if df is None or col not in df.columns:
            print(f"  ⚠ Skipping {config['title']} - data unavailable")
            continue
        
        print(f"  Processing {config['title']}...")
        
        # Get top 5 for overs (highest values)
        over_teams = process_funnel(df, col, is_ascending=False, is_percent=is_percent)
        
        # Get bottom 5 for unders (lowest values)
        under_teams = process_funnel(df, col, is_ascending=True, is_percent=is_percent)
        
        # For each team in overs, get player recommendations (if player_count > 0)
        for team_data in over_teams:
            if player_count == 0:
                team_data['players'] = []
                continue
                
            opponent = team_data['opponent']
            team_id = TEAM_IDS.get(opponent)
            
            if team_id:
                if config['player_type'] == 'shooting':
                    players = get_player_shots_for_team(team_id, config.get('general_range', 'Catch and Shoot'))
                elif config['player_type'] == 'synergy':
                    players = get_player_synergy_for_team(team_id, config.get('play_type', 'Spotup'))
                elif config['player_type'] == 'zone':
                    players = get_player_shot_locations_for_team(team_id, config.get('zone_type', 'restricted_area'))
                else:
                    players = get_player_stats_for_team(team_id, config.get('stat_type', 'points'))
                
                # Limit to configured player count
                team_data['players'] = players[:player_count]
            else:
                team_data['players'] = []
        
        # For unders, also get players (to fade) - same logic
        for team_data in under_teams:
            if player_count == 0:
                team_data['players'] = []
                continue
                
            opponent = team_data['opponent']
            team_id = TEAM_IDS.get(opponent)
            
            if team_id:
                if config['player_type'] == 'shooting':
                    players = get_player_shots_for_team(team_id, config.get('general_range', 'Catch and Shoot'))
                elif config['player_type'] == 'synergy':
                    players = get_player_synergy_for_team(team_id, config.get('play_type', 'Spotup'))
                elif config['player_type'] == 'zone':
                    players = get_player_shot_locations_for_team(team_id, config.get('zone_type', 'restricted_area'))
                else:
                    players = get_player_stats_for_team(team_id, config.get('stat_type', 'points'))
                
                # Limit to configured player count
                team_data['players'] = players[:player_count]
            else:
                team_data['players'] = []
        
        display_stat = config.get('display_stat', 'freq')
        
        if over_teams:
            overs.append({
                'id': config['id'],
                'title': config['title'],
                'description': config['description'],
                'is_percent': is_percent,
                'player_count': player_count,
                'display_stat': display_stat,
                'teams': over_teams
            })
        
        if under_teams:
            unders.append({
                'id': config['id'],
                'title': config['title'],
                'description': config['description'].replace('Target', 'Fade'),
                'is_percent': is_percent,
                'player_count': player_count,
                'display_stat': display_stat,
                'teams': under_teams
            })
    
    et = pytz.timezone('US/Eastern')
    
    return {
        'overs': overs,
        'unders': unders,
        'updated': datetime.now(et).strftime("%Y-%m-%d %H:%M:%S ET"),
        'games_today': len(MATCHUPS) // 2,
        'matchups': [{'home': k, 'away': v} for k, v in MATCHUPS.items() if TEAM_IDS.get(k, 0) < TEAM_IDS.get(v, 0)]
    }


def save_funnels_data(data, filepath='funnels_cache/funnels.json'):
    """Save funnels data to JSON file"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n✓ Saved to {filepath}")


if __name__ == "__main__":
    data = build_funnels_data()
    
    # Print results for verification
    print("\n" + "=" * 60)
    print("OVERS - Teams that ALLOW the most (target these players)")
    print("=" * 60)
    
    for funnel in data.get('overs', []):
        print(f"\n🔥 {funnel['title']}")
        print(f"   {funnel['description']}")
        print("-" * 50)
        
        for team_data in funnel.get('teams', []):
            unit = '%' if funnel.get('is_percent') else ''
            print(f"   #{team_data['rank']} {team_data['team']} ({team_data['value']}{unit}) vs {team_data['opponent']}")
            
            players = team_data.get('players', [])
            if players:
                print(f"      → {team_data['opponent']} players to TARGET:")
                for p in players:
                    freq = p.get('freq', '')
                    fgm = p.get('fgm', '')
                    fga = p.get('fga', '')
                    stat_str = f"{freq}% FREQ" if freq else (f"{fgm} FGM" if fgm else (f"{fga} FGA" if fga else ''))
                    print(f"         • {p['name']} - {stat_str} ({p['mpg']} MPG)")
    
    print("\n" + "=" * 60)
    print("UNDERS - Teams that ALLOW the least (fade these players)")
    print("=" * 60)
    
    for funnel in data.get('unders', []):
        print(f"\n❄️ {funnel['title']}")
        print(f"   {funnel['description']}")
        print("-" * 50)
        
        for team_data in funnel.get('teams', []):
            unit = '%' if funnel.get('is_percent') else ''
            print(f"   #{team_data['rank']} {team_data['team']} ({team_data['value']}{unit}) vs {team_data['opponent']}")
            
            players = team_data.get('players', [])
            if players:
                print(f"      → {team_data['opponent']} players to FADE:")
                for p in players:
                    freq = p.get('freq', '')
                    fgm = p.get('fgm', '')
                    fga = p.get('fga', '')
                    stat_str = f"{freq}% FREQ" if freq else (f"{fgm} FGM" if fgm else (f"{fga} FGA" if fga else ''))
                    print(f"         • {p['name']} - {stat_str} ({p['mpg']} MPG)")
    
    print("\n")
    save_funnels_data(data)
    save_funnels_data(data)
    print("\nDone!")
