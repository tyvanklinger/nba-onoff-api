#!/usr/bin/env python3
"""
TEAM ON/OFF STATS - UNLIMITED COMBOS VERSION
================================================

Filter by ANY combination of players ON or OFF court.
Updated: Now includes traded players in historical data.

Requirements: pip install nba_api pandas requests
"""

import pandas as pd
import numpy as np
import time
import requests
import json
import argparse
from collections import defaultdict
from pathlib import Path
from datetime import datetime

from nba_api.stats.endpoints import leaguegamefinder, commonteamroster
from nba_api.stats.static import players, teams

# ============================================
# CONFIGURATION
# ============================================
TEAM_NAME = "Minnesota Timberwolves"
SEASON = "2025-26"
SEASON_TYPE = "Regular Season"
CACHE_DIR = Path("./onoff_cache")
REQUEST_DELAY = 0.7

# ============================================
# LOOKUPS
# ============================================
def get_player_id(name):
    all_players = players.get_players()
    for p in all_players:
        if p['full_name'].lower() == name.lower():
            return p['id']
    for p in all_players:
        if name.lower() in p['full_name'].lower():
            return p['id']
    return None

def get_player_name(player_id):
    all_players = players.get_players()
    for p in all_players:
        if p['id'] == player_id:
            return p['full_name']
    return f"Unknown-{player_id}"

def get_team_id(name):
    all_teams = teams.get_teams()
    for t in all_teams:
        if name.lower() in t['full_name'].lower():
            return t['id']
    return None

# ============================================
# USG% CALCULATION
# ============================================
def calculate_usg(player_fga, player_fta, player_tov, team_fga, team_fta, team_tov):
    team_usage = team_fga + (0.44 * team_fta) + team_tov
    if team_usage <= 0:
        return 0
    player_usage = player_fga + (0.44 * player_fta) + player_tov
    return 100 * player_usage / team_usage

# ============================================
# ROSTER (current roster - used for reference only)
# ============================================
def get_roster(team_id, season):
    time.sleep(REQUEST_DELAY)
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=team_id, season=season)
        df = roster.get_data_frames()[0]
        return [{'id': row['PLAYER_ID'], 'name': row['PLAYER'], 
                 'pos': row.get('POSITION', ''), 'num': row.get('NUM', '')} 
                for _, row in df.iterrows()]
    except Exception as e:
        print(f"Roster error: {e}")
        return []

# ============================================
# API CALLS
# ============================================
def get_pbp(game_id):
    url = f"https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'Referer': 'https://www.nba.com/',
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json().get('game', {}).get('actions', [])
    except:
        pass
    return []

def get_boxscore(game_id):
    url = f"https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'Referer': 'https://www.nba.com/',
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

def get_starters(game_id, team_id):
    data = get_boxscore(game_id)
    if not data:
        return set()
    
    try:
        game = data.get('game', {})
        for team_key in ['homeTeam', 'awayTeam']:
            team_data = game.get(team_key, {})
            if team_data.get('teamId') == team_id:
                players_list = team_data.get('players', [])
                starters = set()
                
                for p in players_list:
                    if p.get('starter') == '1' or p.get('starter') == 1:
                        starters.add(p.get('personId'))
                    elif p.get('position') and p.get('position').strip():
                        starters.add(p.get('personId'))
                
                if len(starters) >= 5:
                    return starters
                
                def get_mins(p):
                    mins = p.get('statistics', {}).get('minutes', '0')
                    if isinstance(mins, str) and 'PT' in mins:
                        import re
                        match = re.search(r'(\d+)M', mins)
                        return int(match.group(1)) if match else 0
                    return 0
                
                sorted_p = sorted(players_list, key=get_mins, reverse=True)
                return set(p.get('personId') for p in sorted_p[:5])
    except:
        pass
    return set()

def get_team_games(team_id, season):
    time.sleep(REQUEST_DELAY)
    finder = leaguegamefinder.LeagueGameFinder(
        team_id_nullable=team_id,
        season_nullable=season,
        season_type_nullable=SEASON_TYPE
    )
    df = finder.get_data_frames()[0]
    return sorted(df['GAME_ID'].unique().tolist())

# ============================================
# CLOCK PARSING
# ============================================
def parse_clock(clock_str):
    if not clock_str:
        return None
    clock_str = str(clock_str).strip()
    if clock_str.startswith('PT'):
        import re
        match = re.match(r'PT(\d+)M([\d.]+)S', clock_str)
        if match:
            return int(int(match.group(1)) * 60 + float(match.group(2)))
    if ':' in clock_str:
        parts = clock_str.split(':')
        try:
            return int(parts[0]) * 60 + int(float(parts[1]))
        except:
            pass
    return None

# ============================================
# PROCESS GAME - STORE RAW EVENTS WITH LINEUP
# ============================================
def process_game_raw(game_id, team_id):
    """
    Process game and return list of stat events with lineup info.
    Each event: {player_id, lineup (set), stats (dict), time_elapsed}
    
    NOTE: No roster filtering - captures ALL player events for the team.
    This ensures traded players are still included in historical data.
    """
    events = []
    
    current_lineup = get_starters(game_id, team_id)
    if len(current_lineup) < 5:
        return None
    
    time.sleep(REQUEST_DELAY)
    
    actions = get_pbp(game_id)
    if not actions:
        return None
    
    prev_period = 0
    prev_clock = 720
    
    for action in actions:
        period = action.get('period', 1)
        clock = parse_clock(action.get('clock'))
        action_type = str(action.get('actionType', '')).lower()
        sub_type = str(action.get('subType', '')).lower()
        description = str(action.get('description', '')).lower()
        shot_result = str(action.get('shotResult', '')).lower()
        
        if period != prev_period:
            prev_period = period
            prev_clock = 720 if period <= 4 else 300
        
        time_elapsed = 0
        if clock is not None:
            time_elapsed = prev_clock - clock
            if time_elapsed < 0 or time_elapsed > 120:
                time_elapsed = 0
            prev_clock = clock
        
        lineup_snapshot = frozenset(current_lineup)
        
        if time_elapsed > 0:
            for pid in current_lineup:
                events.append({
                    'player_id': pid,
                    'lineup': lineup_snapshot,
                    'stats': {},
                    'time': time_elapsed,
                    'is_team_stat': False
                })
        
        if 'substitution' in action_type:
            person_id = action.get('personId')
            team_sub = action.get('teamId')
            
            if team_sub == team_id and person_id:
                if sub_type == 'in':
                    current_lineup.add(person_id)
                elif sub_type == 'out':
                    current_lineup.discard(person_id)
                
                if len(current_lineup) > 5:
                    current_lineup = set(list(current_lineup)[-5:])
            continue
        
        person_id = action.get('personId')
        assist_person = action.get('assistPersonId')
        
        is_3pt = '3pt' in action_type or '3pt' in description or 'three' in description
        is_made = 'made' in description or shot_result == 'made'
        is_missed = 'miss' in description or shot_result == 'missed'
        
        stat_lineup = frozenset(current_lineup)
        
        if person_id and person_id in current_lineup and ('2pt' in action_type or '3pt' in action_type or 'dunk' in action_type or 'layup' in action_type or 'shot' in action_type):
            stats = {}
            if is_made:
                stats['FGM'] = 1
                stats['FGA'] = 1
                if is_3pt:
                    stats['FG3M'] = 1
                    stats['FG3A'] = 1
                    stats['PTS'] = 3
                else:
                    stats['PTS'] = 2
            elif is_missed:
                stats['FGA'] = 1
                if is_3pt:
                    stats['FG3A'] = 1
            
            if stats:
                events.append({
                    'player_id': person_id,
                    'lineup': stat_lineup,
                    'stats': stats,
                    'time': 0,
                    'is_team_stat': True
                })
        
        elif person_id and person_id in current_lineup and ('freethrow' in action_type or 'free throw' in description):
            stats = {'FTA': 1}
            if is_made or 'made' in description:
                stats['FTM'] = 1
                stats['PTS'] = 1
            
            events.append({
                'player_id': person_id,
                'lineup': stat_lineup,
                'stats': stats,
                'time': 0,
                'is_team_stat': True
            })
        
        elif person_id and person_id in current_lineup and 'rebound' in action_type:
            events.append({
                'player_id': person_id,
                'lineup': stat_lineup,
                'stats': {'REB': 1},
                'time': 0,
                'is_team_stat': False
            })
        
        elif person_id and person_id in current_lineup and 'turnover' in action_type:
            events.append({
                'player_id': person_id,
                'lineup': stat_lineup,
                'stats': {'TOV': 1},
                'time': 0,
                'is_team_stat': True
            })
        
        if assist_person and assist_person in current_lineup and is_made:
            events.append({
                'player_id': assist_person,
                'lineup': stat_lineup,
                'stats': {'AST': 1},
                'time': 0,
                'is_team_stat': False
            })
    
    return events

# ============================================
# BUILD ROSTER FROM EVENTS
# ============================================
def build_roster_from_events(events):
    """
    Build roster from actual play-by-play data.
    This includes ALL players who played for the team this season,
    including those who were later traded.
    """
    player_time = defaultdict(float)
    
    for ev in events:
        pid = ev['player_id']
        player_time[pid] += ev.get('time', 0)
    
    roster = []
    for pid, total_time in player_time.items():
        if total_time > 0:
            name = get_player_name(pid)
            roster.append({
                'id': pid,
                'name': name,
                'pos': '',
                'num': ''
            })
    
    roster.sort(key=lambda x: player_time[x['id']], reverse=True)
    
    return roster

# ============================================
# BUILD CACHE - STORE RAW EVENTS
# ============================================
def build_cache(team_name=TEAM_NAME, season=SEASON):
    print("\n" + "=" * 70)
    print(f"  BUILDING ON/OFF CACHE (Combo Version)")
    print(f"  {team_name} | {season}")
    print("=" * 70)
    
    team_id = get_team_id(team_name)
    if not team_id:
        print(f"Team not found: {team_name}")
        return None
    
    print(f"\nTeam ID: {team_id}")
    
    print("\nGetting current roster (for reference)...")
    current_roster = get_roster(team_id, season)
    if current_roster:
        print(f"   Current roster has {len(current_roster)} players")
    
    print("\nGetting games...")
    game_ids = get_team_games(team_id, season)
    if not game_ids:
        print("No games found")
        return None
    print(f"   Found {len(game_ids)} games")
    
    all_events = []
    games_ok = 0
    
    print(f"\nProcessing {len(game_ids)} games...")
    print("-" * 70)
    
    for i, gid in enumerate(game_ids):
        pct = (i + 1) / len(game_ids) * 100
        print(f"[{i+1:3d}/{len(game_ids)}] {gid} ({pct:5.1f}%)", end="")
        
        game_events = process_game_raw(gid, team_id)
        
        if game_events:
            games_ok += 1
            for ev in game_events:
                ev['lineup'] = list(ev['lineup'])
                ev['game_id'] = gid
            all_events.extend(game_events)
            print(f" OK ({len(game_events)} events)")
        else:
            print(" -")
    
    print("-" * 70)
    print(f"Processed {games_ok}/{len(game_ids)} games")
    print(f"Total events: {len(all_events)}")
    
    print("\nBuilding roster from play-by-play data...")
    roster = build_roster_from_events(all_events)
    print(f"   Found {len(roster)} players who played this season:")
    for p in roster[:15]:
        print(f"      {p['name']}")
    if len(roster) > 15:
        print(f"      ... and {len(roster) - 15} more")
    
    CACHE_DIR.mkdir(exist_ok=True)
    
    cache_data = {
        'team': team_name,
        'team_id': team_id,
        'season': season,
        'games_processed': games_ok,
        'built_at': datetime.now().isoformat(),
        'roster': roster,
        'events': all_events
    }
    
    cache_file = CACHE_DIR / f"{team_name.replace(' ', '_')}_{season}_combo.json"
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f)
    
    print(f"\nCache saved: {cache_file}")
    print(f"   Size: {cache_file.stat().st_size / 1024 / 1024:.1f} MB")
    
    return cache_file

# ============================================
# UPDATE CACHE - ONLY FETCH NEW GAMES
# ============================================
def update_cache(team_name=TEAM_NAME, season=SEASON):
    cache_file = CACHE_DIR / f"{team_name.replace(' ', '_')}_{season}_combo.json"
    
    if not cache_file.exists():
        print(f"No existing cache found. Run --build first.")
        return None
    
    print("\n" + "=" * 70)
    print(f"  UPDATING ON/OFF CACHE")
    print(f"  {team_name} | {season}")
    print("=" * 70)
    
    print("\nLoading existing cache...")
    with open(cache_file, 'r') as f:
        cache = json.load(f)
    
    existing_events = cache.get('events', [])
    existing_roster = cache.get('roster', [])
    
    existing_game_ids = set()
    for ev in existing_events:
        if 'game_id' in ev:
            existing_game_ids.add(ev['game_id'])
    
    print(f"   Existing games in cache: {cache.get('games_processed', 0)}")
    print(f"   Existing roster: {len(existing_roster)} players")
    
    team_id = get_team_id(team_name)
    if not team_id:
        print(f"Team not found: {team_name}")
        return None
    
    print("\nChecking for new games...")
    all_game_ids = get_team_games(team_id, season)
    if not all_game_ids:
        print("No games found")
        return None
    
    new_game_ids = [gid for gid in all_game_ids if gid not in existing_game_ids]
    
    if not new_game_ids:
        print(f"\nCache is up to date! ({len(all_game_ids)} games)")
        return cache_file
    
    print(f"   Found {len(new_game_ids)} new games to process")
    
    new_events = []
    games_ok = 0
    
    print(f"\nProcessing {len(new_game_ids)} new games...")
    print("-" * 70)
    
    for i, gid in enumerate(new_game_ids):
        pct = (i + 1) / len(new_game_ids) * 100
        print(f"[{i+1:3d}/{len(new_game_ids)}] {gid} ({pct:5.1f}%)", end="")
        
        game_events = process_game_raw(gid, team_id)
        
        if game_events:
            games_ok += 1
            for ev in game_events:
                ev['lineup'] = list(ev['lineup'])
                ev['game_id'] = gid
            new_events.extend(game_events)
            print(f" OK ({len(game_events)} events)")
        else:
            print(" -")
    
    print("-" * 70)
    print(f"Processed {games_ok}/{len(new_game_ids)} new games")
    print(f"New events: {len(new_events)}")
    
    all_events = existing_events + new_events
    total_games = cache.get('games_processed', 0) + games_ok
    
    print("\nRebuilding roster from all play-by-play data...")
    roster = build_roster_from_events(all_events)
    print(f"   Found {len(roster)} players who played this season")
    
    existing_ids = set(p['id'] for p in existing_roster)
    new_players = [p for p in roster if p['id'] not in existing_ids]
    if new_players:
        print(f"   New players added: {', '.join(p['name'] for p in new_players)}")
    
    cache_data = {
        'team': team_name,
        'team_id': team_id,
        'season': season,
        'games_processed': total_games,
        'built_at': datetime.now().isoformat(),
        'roster': roster,
        'events': all_events
    }
    
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f)
    
    print(f"\nCache updated: {cache_file}")
    print(f"   Total games: {total_games}")
    print(f"   Total events: {len(all_events)}")
    print(f"   Size: {cache_file.stat().st_size / 1024 / 1024:.1f} MB")
    
    return cache_file

# ============================================
# QUERY WITH FILTERS
# ============================================
def query_combo(players_on=None, players_off=None, team_name=TEAM_NAME, season=SEASON, debug=False):
    players_on = players_on or []
    players_off = players_off or []
    
    cache_file = CACHE_DIR / f"{team_name.replace(' ', '_')}_{season}_combo.json"
    
    if not cache_file.exists():
        print(f"Cache not found: {cache_file}")
        print(f"   Run with --build first")
        return
    
    print("Loading cache...", end=" ")
    with open(cache_file, 'r') as f:
        cache = json.load(f)
    print("done")
    
    if debug:
        print("\n[DEBUG] Calculating total minutes per player (no filter)...")
        total_time_per_player = defaultdict(float)
        for ev in cache['events']:
            if ev['time'] > 0:
                total_time_per_player[ev['player_id']] += ev['time']
        
        print("[DEBUG] Total minutes in cache:")
        for teammate in cache['roster']:
            pid = teammate['id']
            mins = total_time_per_player.get(pid, 0) / 60
            print(f"   {teammate['name']}: {mins:.0f} min")
        print()
    
    on_ids = set()
    off_ids = set()
    on_names = []
    off_names = []
    
    for name in players_on:
        pid = get_player_id(name)
        if pid:
            on_ids.add(pid)
            on_names.append(name.split()[-1])
        else:
            print(f"Player not found: {name}")
            return
    
    for name in players_off:
        pid = get_player_id(name)
        if pid:
            off_ids.add(pid)
            off_names.append(name.split()[-1])
        else:
            print(f"Player not found: {name}")
            return
    
    filter_desc = []
    if on_names:
        filter_desc.append(f"{', '.join(on_names)} ON")
    if off_names:
        filter_desc.append(f"{', '.join(off_names)} OFF")
    
    filter_text = ' + '.join(filter_desc) if filter_desc else "ALL PLAYERS (no filter)"
    
    short_team = team_name.split()[-1].upper()
    
    print("\n" + "=" * 130)
    print(f"  {short_team} STATS: {filter_text}")
    print(f"  {team_name} | {season} | {cache['games_processed']} games")
    print("=" * 130)
    
    events = cache['events']
    
    player_stats = defaultdict(lambda: defaultdict(float))
    player_time = defaultdict(float)
    player_team_stats = defaultdict(lambda: defaultdict(float))
    
    for ev in events:
        lineup = set(ev['lineup'])
        
        if not on_ids.issubset(lineup):
            continue
        if off_ids.intersection(lineup):
            continue
        
        pid = ev['player_id']
        player_time[pid] += ev['time']
        
        for stat, val in ev['stats'].items():
            player_stats[pid][stat] += val
        
        if ev.get('is_team_stat'):
            for stat in ['FGA', 'FTA', 'TOV']:
                if stat in ev['stats']:
                    for player_on_court in lineup:
                        player_team_stats[player_on_court][stat] += ev['stats'][stat]
    
    results = []
    
    for teammate in cache['roster']:
        pid = teammate['id']
        
        if pid in off_ids:
            continue
        
        mins = player_time.get(pid, 0) / 60
        
        if mins < 5:
            continue
        
        stats = player_stats.get(pid, {})
        mult = 36 / mins if mins > 0 else 0
        
        fgm = stats.get('FGM', 0)
        fga = stats.get('FGA', 0)
        fg3m = stats.get('FG3M', 0)
        fg3a = stats.get('FG3A', 0)
        fta = stats.get('FTA', 0)
        tov = stats.get('TOV', 0)
        
        fg_pct = (fgm / fga * 100) if fga > 0 else 0
        fg3_pct = (fg3m / fg3a * 100) if fg3a > 0 else 0
        
        usg = calculate_usg(fga, fta, tov, 
                           player_team_stats[pid]['FGA'], 
                           player_team_stats[pid]['FTA'], 
                           player_team_stats[pid]['TOV'])
        
        results.append({
            'name': teammate['name'],
            'min': mins,
            'usg': usg,
            'pts': stats.get('PTS', 0) * mult,
            'reb': stats.get('REB', 0) * mult,
            'ast': stats.get('AST', 0) * mult,
            'fg3m': fg3m * mult,
            'fg3a': fg3a * mult,
            'fg3_pct': fg3_pct,
            'fgm': fgm * mult,
            'fga': fga * mult,
            'fg_pct': fg_pct,
            'tov': tov * mult,
            'pra': (stats.get('PTS', 0) + stats.get('REB', 0) + stats.get('AST', 0)) * mult,
            'pr': (stats.get('PTS', 0) + stats.get('REB', 0)) * mult,
            'pa': (stats.get('PTS', 0) + stats.get('AST', 0)) * mult,
        })
    
    results.sort(key=lambda x: x['min'], reverse=True)
    
    print(f"\n{'PLAYER':<20} {'MIN':<7} {'USG%':<7} {'PTS':<7} {'REB':<7} {'AST':<7} {'3PM':<6} {'3PA':<6} {'3P%':<7} {'FGM':<6} {'FGA':<6} {'FG%':<7} {'TOV':<6} {'PRA':<7} {'PR':<7} {'PA':<7}")
    print("-" * 130)
    
    for r in results:
        print(f"{r['name']:<20} {r['min']:<7.0f} {r['usg']:<7.1f} {r['pts']:<7.1f} {r['reb']:<7.1f} {r['ast']:<7.1f} {r['fg3m']:<6.1f} {r['fg3a']:<6.1f} {r['fg3_pct']:<7.1f} {r['fgm']:<6.1f} {r['fga']:<6.1f} {r['fg_pct']:<7.1f} {r['tov']:<6.1f} {r['pra']:<7.1f} {r['pr']:<7.1f} {r['pa']:<7.1f}")
    
    print("=" * 130)
    print()

# ============================================
# MAIN
# ============================================
def main():
    parser = argparse.ArgumentParser(description='Team On/Off Stats - Unlimited Combos')
    parser.add_argument('--build', action='store_true', help='Build cache (full, ~30-45 min)')
    parser.add_argument('--update', action='store_true', help='Update cache (only new games, ~1-2 min)')
    parser.add_argument('--all', action='store_true', help='Show all team stats (no filter)')
    parser.add_argument('--on', action='append', default=[], help='Player(s) who must be ON court')
    parser.add_argument('--out', action='append', default=[], help='Player(s) who must be OFF court')
    parser.add_argument('--debug', action='store_true', help='Show debug info')
    parser.add_argument('--team', type=str, default=TEAM_NAME, help='Team name')
    parser.add_argument('--season', type=str, default=SEASON, help='Season')
    
    args = parser.parse_args()
    
    if args.build:
        build_cache(args.team, args.season)
    elif args.update:
        update_cache(args.team, args.season)
    elif args.all:
        query_combo(players_on=[], players_off=[], team_name=args.team, season=args.season, debug=args.debug)
    elif args.on or args.out:
        query_combo(players_on=args.on, players_off=args.out, team_name=args.team, season=args.season, debug=args.debug)
    else:
        print("\nTEAM ON/OFF STATS - UNLIMITED COMBOS")
        print("=" * 60)
        print("\nUsage:")
        print('  python3 "<team>.py" --build    # Build cache (first time)')
        print('  python3 "<team>.py" --update   # Update cache (daily)')
        print('  python3 "<team>.py" --all      # Show all stats')
        print('  python3 "<team>.py" --out "Player Name"  # Player OFF filter')

if __name__ == "__main__":
    main()
