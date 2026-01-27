"""
FastAPI Backend for NBA On/Off Stats
Deploy to Railway for production use
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import json
import os
from pathlib import Path
from collections import defaultdict

app = FastAPI(title="NBA On/Off API", version="1.0.0")

# CORS - allow your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://straight-bettin.vercel.app",
        "http://localhost:5173",
	"https://straightbettin.com",
	"https://www.straightbettin.com",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache directory
CACHE_DIR = Path(__file__).parent / "onoff_cache"

# In-memory cache for faster responses
_team_cache = {}

def load_team_cache(team_name: str, season: str = "2025-26"):
    """Load team cache into memory"""
    cache_key = f"{team_name}_{season}"
    
    if cache_key in _team_cache:
        return _team_cache[cache_key]
    
    cache_file = CACHE_DIR / f"{team_name.replace(' ', '_')}_{season}_combo.json"
    
    if not cache_file.exists():
        return None
    
    with open(cache_file, 'r') as f:
        data = json.load(f)
    
    _team_cache[cache_key] = data
    return data

def calculate_usg(fga, fta, tov, team_fga, team_fta, team_tov):
    """Calculate usage rate"""
    player_poss = fga + 0.44 * fta + tov
    team_poss = team_fga + 0.44 * team_fta + team_tov
    if team_poss == 0:
        return 0
    return 100 * player_poss / team_poss

def get_player_id(name: str, roster: list) -> Optional[int]:
    """Find player ID by name (partial match)"""
    name_lower = name.lower()
    for player in roster:
        if name_lower in player['name'].lower():
            return player['id']
    return None

def calculate_player_stats(events, roster, on_ids, off_ids, min_minutes=5):
    """Calculate stats for players given filter conditions"""
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
        player_time[pid] += ev.get('time', 0)
        
        for stat, val in ev.get('stats', {}).items():
            player_stats[pid][stat] += val
        
        if ev.get('is_team_stat'):
            for stat in ['FGA', 'FTA', 'TOV']:
                if stat in ev.get('stats', {}):
                    for player_on_court in lineup:
                        player_team_stats[player_on_court][stat] += ev['stats'][stat]
    
    # Build results
    results = {}
    for teammate in roster:
        pid = teammate['id']
        mins = player_time.get(pid, 0) / 60
        
        if mins < min_minutes:
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
        
        results[pid] = {
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
        }
    
    return results

def query_stats(team_name: str, players_on: List[str] = None, players_off: List[str] = None, season: str = "2025-26"):
    """Query on/off stats with filters."""
    players_on = players_on or []
    players_off = players_off or []
    
    cache = load_team_cache(team_name, season)
    if not cache:
        return None
    
    events = cache.get('events', [])
    roster = cache.get('roster', [])
    
    # Convert player names to IDs
    on_ids = set()
    off_ids = set()
    on_names = []
    off_names = []
    
    for name in players_on:
        pid = get_player_id(name, roster)
        if pid:
            on_ids.add(pid)
            for p in roster:
                if p['id'] == pid:
                    on_names.append(p['name'])
                    break
    
    for name in players_off:
        pid = get_player_id(name, roster)
        if pid:
            off_ids.add(pid)
            for p in roster:
                if p['id'] == pid:
                    off_names.append(p['name'])
                    break
    
    # Calculate main stats (with current filters)
    main_stats = calculate_player_stats(events, roster, on_ids, off_ids)
    
    # Convert to sorted list
    results = list(main_stats.values())
    results.sort(key=lambda x: x['min'], reverse=True)
    
    # Calculate comparison if there are OFF players
    comparison = []
    if off_ids:
        # Get stats when OFF players are ON (baseline)
        baseline_stats = calculate_player_stats(events, roster, on_ids | off_ids, set())
        
        # Build comparison for players who appear in both
        for pid, off_stat in main_stats.items():
            if pid in baseline_stats and pid not in off_ids:
                on_stat = baseline_stats[pid]
                
                # Calculate differences
                diff = {
                    'id': pid,
                    'name': off_stat['name'],
                    'min_with': round(on_stat['min'], 1),
                    'usg_diff': round(off_stat['usg'] - on_stat['usg'], 1),
                    'pts_diff': round(off_stat['pts'] - on_stat['pts'], 1),
                    'reb_diff': round(off_stat['reb'] - on_stat['reb'], 1),
                    'ast_diff': round(off_stat['ast'] - on_stat['ast'], 1),
                    'fg3a_diff': round(off_stat['fg3a'] - on_stat['fg3a'], 1),
                    'fga_diff': round(off_stat['fga'] - on_stat['fga'], 1),
                    'pra_diff': round(off_stat['pra'] - on_stat['pra'], 1),
                    'pr_diff': round(off_stat['pr'] - on_stat['pr'], 1),
                    'pa_diff': round(off_stat['pa'] - on_stat['pa'], 1),
                }
                comparison.append(diff)
        
        # Sort by minutes with the OFF player(s) ON
        comparison.sort(key=lambda x: x['min_with'], reverse=True)
        comparison = comparison[:10]  # Top 10
    
    return {
        'team': team_name,
        'season': season,
        'games': cache.get('games_processed', 0),
        'filter': {'on': on_names, 'off': off_names},
        'roster': [{'id': p['id'], 'name': p['name']} for p in roster],
        'players': results,
        'comparison': comparison,
    }


# ============================================
# API ENDPOINTS
# ============================================

@app.get("/")
def root():
    return {"status": "ok", "message": "NBA On/Off API"}

@app.get("/api/teams")
def get_teams():
    """Get list of all available teams"""
    teams = [
        "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets",
        "Chicago Bulls", "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets",
        "Detroit Pistons", "Golden State Warriors", "Houston Rockets", "Indiana Pacers",
        "Los Angeles Clippers", "Los Angeles Lakers", "Memphis Grizzlies", "Miami Heat",
        "Milwaukee Bucks", "Minnesota Timberwolves", "New Orleans Pelicans", "New York Knicks",
        "Oklahoma City Thunder", "Orlando Magic", "Philadelphia 76ers", "Phoenix Suns",
        "Portland Trail Blazers", "Sacramento Kings", "San Antonio Spurs", "Toronto Raptors",
        "Utah Jazz", "Washington Wizards"
    ]
    return {"teams": teams}

@app.get("/api/roster/{team}")
def get_roster(team: str):
    """Get roster for a team"""
    cache = load_team_cache(team)
    if not cache:
        raise HTTPException(status_code=404, detail=f"Team not found: {team}")
    
    return {
        "team": team,
        "roster": cache.get('roster', []),
        "games": cache.get('games_processed', 0),
    }

@app.get("/api/onoff/{team}")
def get_onoff_stats(
    team: str,
    on: List[str] = Query(default=[]),
    off: List[str] = Query(default=[]),
):
    """
    Get on/off stats for a team with optional player filters.
    
    Examples:
    - /api/onoff/Utah Jazz
    - /api/onoff/Utah Jazz?off=Lauri Markkanen
    - /api/onoff/Utah Jazz?on=Keyonte George&off=Lauri Markkanen
    """
    result = query_stats(team, players_on=on, players_off=off)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Team not found: {team}")
    
    return result


@app.get("/api/funnels")
def get_funnels():
    """Return the latest funnels data"""
    try:
        # Check multiple possible locations for funnels data
        possible_paths = [
            "funnels_data.json",
            "funnels_cache/funnels.json",
            Path(__file__).parent / "funnels_data.json",
            Path(__file__).parent / "funnels_cache" / "funnels.json",
        ]
        
        for fpath in possible_paths:
            if os.path.exists(fpath):
                with open(fpath, "r") as f:
                    return json.load(f)
        
        return {"error": "Funnels data not available", "overs": [], "unders": []}
    except Exception as e:
        return {"error": str(e), "overs": [], "unders": []}


@app.post("/api/funnels/refresh")
def refresh_funnels():
    """Regenerate funnels data - called by GitHub Action at 11 PM ET"""
    try:
        from funnels_api import build_funnels_data, save_funnels_data
        
        print("Starting funnels refresh...")
        data = build_funnels_data()
        save_funnels_data(data, 'funnels_data.json')
        
        return {
            "success": True,
            "games": data.get('games_today', 0),
            "overs": len(data.get('overs', [])),
            "unders": len(data.get('unders', [])),
            "updated": data.get('updated')
        }
    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


@app.get("/api/injuries")
def get_injuries():
    """Return the latest injuries data"""
    try:
        # Check multiple possible locations for injuries data
        possible_paths = [
            "injuries_data.json",
            Path(__file__).parent / "injuries_data.json",
        ]
        
        for fpath in possible_paths:
            if os.path.exists(fpath):
                with open(fpath, "r") as f:
                    return json.load(f)
        
        return {"error": "Injuries data not available", "injuries": {}, "not_yet_submitted": []}
    except Exception as e:
        return {"error": str(e), "injuries": {}, "not_yet_submitted": []}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# ============================================
# GAME LOGS / MINUTES PROJECTION ENDPOINT
# ============================================

from gamelogs_api import fetch_and_process_team, get_filtered_stats, get_player_stats

# Cache for game logs data (expensive to fetch)
_gamelogs_cache = {}

@app.get("/api/minutes/{team_name}")
def get_minutes(
    team_name: str,
    player: Optional[str] = None,
    with_players: Optional[str] = Query(None, alias="with"),
    without_players: Optional[str] = Query(None, alias="without")
):
    """
    Get player minute stats with optional teammate filters
    
    Args:
        team_name: Team name (e.g., "Atlanta Hawks")
        player: (optional) Specific player to get filtered stats for
        with: (optional) Comma-separated list of teammates who must have played
        without: (optional) Comma-separated list of teammates who must NOT have played
    
    Example:
        /api/minutes/Atlanta%20Hawks
        /api/minutes/Atlanta%20Hawks?player=Dyson%20Daniels&with=Jalen%20Johnson&without=Trae%20Young
    """
    import urllib.parse
    team_name = urllib.parse.unquote(team_name)
    
    # Check cache first (cache for 6 hours)
    import time
    cache_key = team_name
    if cache_key in _gamelogs_cache:
        cached_time, cached_data = _gamelogs_cache[cache_key]
        if time.time() - cached_time < 21600:  # 6 hours
            data = cached_data
        else:
            data = None
    else:
        data = None
    
    # Fetch if not cached
    if data is None:
        data = fetch_and_process_team(team_name)
        if 'error' in data:
            raise HTTPException(status_code=404, detail=data['error'])
        _gamelogs_cache[cache_key] = (time.time(), data)
    
    response = {
        'team': team_name,
        'players': data['players'],
    }
    
    # If specific player requested with filters
    if player:
        player = urllib.parse.unquote(player)
        with_list = [p.strip() for p in with_players.split(',')] if with_players else None
        without_list = [p.strip() for p in without_players.split(',')] if without_players else None
        
        # URL decode the player names in lists
        if with_list:
            with_list = [urllib.parse.unquote(p) for p in with_list if p]
        if without_list:
            without_list = [urllib.parse.unquote(p) for p in without_list if p]
        
        filtered = get_filtered_stats(
            data['games'],
            data['player_logs'],
            player,
            with_list,
            without_list
        )
        
        response['filtered'] = {
            'player': player,
            'with': with_list,
            'without': without_list,
            'stats': filtered,
        }
    
    return response
