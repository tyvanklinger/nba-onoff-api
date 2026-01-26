"""
NBA Injury Report Scraper for On/Off Page Display
Scrapes official.nba.com injury report PDF
Captures OUT, DOUBTFUL, and QUESTIONABLE players by team
Runs every 15 minutes via GitHub Actions
"""

import requests
from bs4 import BeautifulSoup
import pdfplumber
from io import BytesIO
import json
import re
from datetime import datetime
import pytz

# Team name mappings - PDF uses no-space names like "MinnesotaTimberwolves"
TEAM_NAMES_NOSPACE = {
    "AtlantaHawks": "Atlanta Hawks",
    "BostonCeltics": "Boston Celtics",
    "BrooklynNets": "Brooklyn Nets",
    "CharlotteHornets": "Charlotte Hornets",
    "ChicagoBulls": "Chicago Bulls",
    "ClevelandCavaliers": "Cleveland Cavaliers",
    "DallasMavericks": "Dallas Mavericks",
    "DenverNuggets": "Denver Nuggets",
    "DetroitPistons": "Detroit Pistons",
    "GoldenStateWarriors": "Golden State Warriors",
    "HoustonRockets": "Houston Rockets",
    "IndianaPacers": "Indiana Pacers",
    "LosAngelesClippers": "Los Angeles Clippers",
    "LAClippers": "Los Angeles Clippers",
    "LosAngelesLakers": "Los Angeles Lakers",
    "LALakers": "Los Angeles Lakers",
    "MemphisGrizzlies": "Memphis Grizzlies",
    "MiamiHeat": "Miami Heat",
    "MilwaukeeBucks": "Milwaukee Bucks",
    "MinnesotaTimberwolves": "Minnesota Timberwolves",
    "NewOrleansPelicans": "New Orleans Pelicans",
    "NewYorkKnicks": "New York Knicks",
    "OklahomaCityThunder": "Oklahoma City Thunder",
    "OrlandoMagic": "Orlando Magic",
    "Philadelphia76ers": "Philadelphia 76ers",
    "PhoenixSuns": "Phoenix Suns",
    "PortlandTrailBlazers": "Portland Trail Blazers",
    "SacramentoKings": "Sacramento Kings",
    "SanAntonioSpurs": "San Antonio Spurs",
    "TorontoRaptors": "Toronto Raptors",
    "UtahJazz": "Utah Jazz",
    "WashingtonWizards": "Washington Wizards",
}


def scrape_injuries():
    """
    Scrape the NBA injury report and return structured data by team
    """
    print("Fetching injury report from official.nba.com...")
    
    url = "https://official.nba.com/nba-injury-report-2024-25-season/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching injury page: {e}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find injury report PDFs (filter out brochures)
    all_pdf_links = soup.find_all('a', href=lambda x: x and x.endswith('.pdf'))
    injury_pdf_links = [
        link for link in all_pdf_links 
        if 'injury' in link['href'].lower() or 'report' in link.get_text().lower() or 'ET' in link.get_text()
    ]
    
    if not injury_pdf_links:
        print("No injury report PDF found")
        return None
    
    # Get the last (most recent) PDF
    latest_pdf_url = injury_pdf_links[-1]['href']
    print(f"Found PDF: {latest_pdf_url.split('/')[-1]}")
    
    try:
        pdf_response = requests.get(latest_pdf_url, headers=headers, timeout=60)
        pdf_response.raise_for_status()
    except Exception as e:
        print(f"Error downloading PDF: {e}")
        return None
    
    pdf_file = BytesIO(pdf_response.content)
    
    # Get today's date in ET
    et = pytz.timezone('America/New_York')
    today = datetime.now(et).strftime('%m/%d/%Y')
    print(f"Today's date: {today}")
    
    # Extract data from PDF
    injuries_by_team = {}
    not_yet_submitted = set()
    teams_playing_today = set()  # Track all teams playing today
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text() or ""
                full_text += text + "\n"
            
            # Process the text
            current_team = None
            current_date = None
            lines = full_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Skip header/footer lines
                if 'GameDate' in line and 'GameTime' in line:
                    continue
                if line.startswith('Injury Report:'):
                    continue
                if re.match(r'^Page\s*\d+\s*of\s*\d+$', line):
                    continue
                
                # Check for date change (format: 01/26/2026 or MM/DD/YYYY at start of line)
                date_match = re.match(r'^(\d{2}/\d{2}/\d{4})', line)
                if date_match:
                    current_date = date_match.group(1)
                    print(f"  Found date: {current_date}")
                
                # Check for team name (no-space format) ANYWHERE in the line
                found_team = None
                for nospace_name, proper_name in TEAM_NAMES_NOSPACE.items():
                    if nospace_name in line:
                        found_team = proper_name
                        break
                
                if found_team:
                    current_team = found_team
                    
                    # Check if this is today's game
                    is_today = (current_date == today) if current_date else True
                    
                    if is_today:
                        teams_playing_today.add(current_team)
                    
                    # Check if NOTYETSUBMITTED (no spaces) or NOT YET SUBMITTED on same line
                    if 'NOTYETSUBMITTED' in line.replace(' ', '').upper():
                        if is_today:
                            not_yet_submitted.add(current_team)
                            print(f"  Not yet submitted (today): {current_team}")
                        continue
                    
                    # Initialize team in injuries dict if not exists
                    if current_team not in injuries_by_team:
                        injuries_by_team[current_team] = []
                
                # Skip if no current team yet
                if not current_team:
                    continue
                
                # Find player entries in the line
                # Pattern handles: Last,First Status (with Jr., Sr., III, etc. and apostrophes)
                player_pattern = r"([A-Za-z\-\'\.]+(?:(?:\s*Jr\.|Sr\.|III|II|IV|V))?),\s*([A-Za-z\-\'\.]+(?:\s*[A-Za-z\-\'\.]+)?)\s+(Out|Doubtful|Questionable|Probable|Available)"
                
                matches = re.findall(player_pattern, line, re.IGNORECASE)
                
                for last_name, first_name, status in matches:
                    status = status.title()
                    player_name = f"{first_name.strip()} {last_name.strip()}"
                    
                    # Only include Out, Doubtful, Questionable
                    if status in ['Out', 'Doubtful', 'Questionable']:
                        if current_team not in injuries_by_team:
                            injuries_by_team[current_team] = []
                        
                        # Avoid duplicates
                        existing_names = [p['name'] for p in injuries_by_team[current_team]]
                        if player_name not in existing_names:
                            injuries_by_team[current_team].append({
                                'name': player_name,
                                'status': status
                            })
                            
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Sort players: Out first, then Doubtful, then Questionable
    status_order = {'Out': 0, 'Doubtful': 1, 'Questionable': 2}
    for team in injuries_by_team:
        injuries_by_team[team].sort(key=lambda x: status_order.get(x['status'], 3))
    
    total_players = sum(len(players) for players in injuries_by_team.values())
    print(f"\nLoaded {total_players} injured players across {len(injuries_by_team)} teams")
    print(f"Teams playing today: {len(teams_playing_today)}")
    print(f"Teams not yet submitted: {len(not_yet_submitted)}")
    if not_yet_submitted:
        print(f"  {', '.join(sorted(not_yet_submitted))}")
    
    return {
        'injuries': injuries_by_team,
        'not_yet_submitted': list(not_yet_submitted)
    }


def build_injuries_data():
    """Build the complete injuries data structure"""
    result = scrape_injuries()
    
    et = pytz.timezone('America/New_York')
    now = datetime.now(et)
    
    if not result:
        return {
            'injuries': {},
            'not_yet_submitted': [],
            'updated': now.strftime('%Y-%m-%d %I:%M %p ET'),
            'error': 'Failed to fetch injury report'
        }
    
    result['updated'] = now.strftime('%Y-%m-%d %I:%M %p ET')
    return result


def main():
    """Main function - scrape injuries and save to JSON"""
    print("=" * 50)
    print("NBA Injury Report Scraper")
    print("=" * 50)
    
    data = build_injuries_data()
    
    output_path = "injuries_data.json"
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\nSaved to {output_path}")
    print(f"Updated: {data.get('updated')}")
    
    if 'error' not in data:
        print(f"Teams with injuries: {len(data['injuries'])}")
        print(f"Teams not yet submitted: {len(data['not_yet_submitted'])}")
        if data['not_yet_submitted']:
            print(f"  {', '.join(data['not_yet_submitted'])}")


if __name__ == "__main__":
    main()
