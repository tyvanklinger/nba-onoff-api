"""
NBA Injury Report Scraper for On/Off Page Display
Scrapes official.nba.com injury report PDF
Captures OUT, DOUBTFUL, and QUESTIONABLE players by team
Runs every 30 minutes via GitHub Actions
"""

import requests
from bs4 import BeautifulSoup
import pdfplumber
from io import BytesIO
import json
import re
from datetime import datetime
import pytz

# Team name mappings - PDF uses no-space names like "NewYorkKnicks"
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

def convert_player_name(name_str):
    """Convert 'Last,First' to 'First Last'"""
    if not name_str or ',' not in name_str:
        return name_str
    
    parts = name_str.split(',', 1)
    if len(parts) == 2:
        last = parts[0].strip()
        first = parts[1].strip()
        return f"{first} {last}"
    return name_str

def scrape_injuries():
    """
    Scrape the NBA injury report and return structured data by team
    """
    print("Fetching injury report from official.nba.com...")
    
    url = "https://official.nba.com/nba-injury-report-2024-25-season/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching injury page: {e}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find injury report PDFs
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
    pdf_filename = latest_pdf_url.split('/')[-1]
    print(f"Found PDF: {pdf_filename}")
    
    try:
        pdf_response = requests.get(latest_pdf_url, headers=headers, timeout=60)
        pdf_response.raise_for_status()
    except Exception as e:
        print(f"Error downloading PDF: {e}")
        return None
    
    pdf_file = BytesIO(pdf_response.content)
    
    # Extract data from PDF
    injuries_by_team = {}
    not_yet_submitted = set()
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text() or ""
                full_text += text + "\n"
            
            # Process the text - don't skip any lines with game times!
            # Just extract team names and player info from each line
            
            current_team = None
            
            # Split by lines
            lines = full_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Skip only true header/footer lines
                if 'GameDate' in line and 'GameTime' in line:
                    continue
                if line.startswith('Injury Report:'):
                    continue
                if re.match(r'^Page\s*\d+\s*of\s*\d+$', line):
                    continue
                
                # Check for team name (no-space format) ANYWHERE in the line
                for nospace_name, proper_name in TEAM_NAMES_NOSPACE.items():
                    if nospace_name in line:
                        current_team = proper_name
                        # Don't remove team name - just note it and continue processing
                        break
                
                # Check for NOT YET SUBMITTED
                if 'NOT YET SUBMITTED' in line.upper() and current_team:
                    not_yet_submitted.add(current_team)
                    continue
                
                # Skip if no current team yet
                if not current_team:
                    continue
                
                # Find all player entries in the line
                # Pattern handles: Name,Name Status (with optional Jr., Sr., III, etc.)
                # Also handles names with apostrophes like De'Andre
                player_pattern = r"([A-Za-z\-\'\.]+(?:(?:Jr\.|Sr\.|III|II|IV|V))?),\s*([A-Za-z\-\'\.]+(?:\s*[A-Za-z\-\'\.]+)?)\s+(Out|Doubtful|Questionable|Probable|Available)"
                
                matches = re.findall(player_pattern, line, re.IGNORECASE)
                
                for last_name, first_name, status in matches:
                    status = status.title()
                    
                    # Build full name
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
    
    # Sort players within each team: Out first, then Doubtful, then Questionable
    status_order = {'Out': 0, 'Doubtful': 1, 'Questionable': 2}
    for team in injuries_by_team:
        injuries_by_team[team].sort(key=lambda x: status_order.get(x['status'], 3))
    
    # Count totals
    total_players = sum(len(players) for players in injuries_by_team.values())
    print(f"Loaded {total_players} injured players across {len(injuries_by_team)} teams")
    
    if total_players > 0:
        print("\nSample injuries found:")
        count = 0
        for team, players in injuries_by_team.items():
            if count >= 3:
                break
            print(f"  {team}:")
            for p in players[:3]:
                print(f"    - {p['name']} ({p['status']})")
            count += 1
    
    return {
        'injuries': injuries_by_team,
        'not_yet_submitted': list(not_yet_submitted)
    }

def build_injuries_data():
    """
    Build the complete injuries data structure
    """
    result = scrape_injuries()
    
    et = pytz.timezone('America/New_York')
    now = datetime.now(et)
    
    if not result:
        # Return empty structure on failure
        return {
            'injuries': {},
            'not_yet_submitted': [],
            'updated': now.strftime('%Y-%m-%d %I:%M %p ET'),
            'error': 'Failed to fetch injury report'
        }
    
    # Add timestamp
    result['updated'] = now.strftime('%Y-%m-%d %I:%M %p ET')
    
    return result

def main():
    """
    Main function - scrape injuries and save to JSON
    """
    print("=" * 50)
    print("NBA Injury Report Scraper")
    print("=" * 50)
    
    data = build_injuries_data()
    
    # Save to file
    output_path = "injuries_data.json"
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\nSaved to {output_path}")
    print(f"Updated: {data.get('updated')}")
    
    # Print summary
    if 'error' not in data:
        print(f"\nTeams with injuries: {len(data['injuries'])}")
        print(f"Teams not yet submitted: {len(data['not_yet_submitted'])}")
    else:
        print(f"\nError: {data.get('error')}")

if __name__ == "__main__":
    main()
