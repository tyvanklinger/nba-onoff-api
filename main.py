"""
FastAPI Backend for NBA On/Off Stats
Deploy to Railway for production use
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import json
from pathlib import Path
from collections import defaultdict

app = FastAPI(title="NBA On/Off API", version="1.0.0")

# CORS - allow your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://straight-bettin.vercel.app",
        "http://localhost:5173",
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
    
    # Filter events
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
    
    results.sort(key=lambda x: x['min'], reverse=True)
    
    return {
        'team': team_name,
        'season': season,
        'games': cache.get('games_processed', 0),
        'filter': {'on': on_names, 'off': off_names},
        'roster': [{'id': p['id'], 'name': p['name']} for p in roster],
        'players': results,
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

@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
