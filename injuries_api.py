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

# Team name mappings (PDF uses full names, need to match frontend)
TEAM_NAMES = {
    "Atlanta Hawks": "Atlanta Hawks",
    "Boston Celtics": "Boston Celtics",
    "Brooklyn Nets": "Brooklyn Nets",
    "Charlotte Hornets": "Charlotte Hornets",
    "Chicago Bulls": "Chicago Bulls",
    "Cleveland Cavaliers": "Cleveland Cavaliers",
    "Dallas Mavericks": "Dallas Mavericks",
    "Denver Nuggets": "Denver Nuggets",
    "Detroit Pistons": "Detroit Pistons",
    "Golden State Warriors": "Golden State Warriors",
    "Houston Rockets": "Houston Rockets",
    "Indiana Pacers": "Indiana Pacers",
    "Los Angeles Clippers": "Los Angeles Clippers",
    "LA Clippers": "Los Angeles Clippers",
    "Los Angeles Lakers": "Los Angeles Lakers",
    "LA Lakers": "Los Angeles Lakers",
    "Memphis Grizzlies": "Memphis Grizzlies",
    "Miami Heat": "Miami Heat",
    "Milwaukee Bucks": "Milwaukee Bucks",
    "Minnesota Timberwolves": "Minnesota Timberwolves",
    "New Orleans Pelicans": "New Orleans Pelicans",
    "New York Knicks": "New York Knicks",
    "Oklahoma City Thunder": "Oklahoma City Thunder",
    "Orlando Magic": "Orlando Magic",
    "Philadelphia 76ers": "Philadelphia 76ers",
    "Phoenix Suns": "Phoenix Suns",
    "Portland Trail Blazers": "Portland Trail Blazers",
    "Sacramento Kings": "Sacramento Kings",
    "San Antonio Spurs": "San Antonio Spurs",
    "Toronto Raptors": "Toronto Raptors",
    "Utah Jazz": "Utah Jazz",
    "Washington Wizards": "Washington Wizards",
}

def normalize_team_name(team_name):
    """Normalize team name to match frontend format"""
    team_name = team_name.strip()
    return TEAM_NAMES.get(team_name, team_name)

def scrape_injuries():
    """
    Scrape the NBA injury report and return structured data by team
    """
    print("Fetching injury report from official.nba.com...")
    
    url = "https://official.nba.com/nba-injury-report-2024-25-season/"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching injury page: {e}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all PDF links
    pdf_links = soup.find_all('a', href=lambda x: x and x.endswith('.pdf'))
    
    if not pdf_links:
        print("No injury report PDF found")
        return None
    
    # Get the last (most recent) PDF
    latest_pdf_url = pdf_links[-1]['href']
    print(f"Found PDF: {latest_pdf_url.split('/')[-1]}")
    
    try:
        pdf_response = requests.get(latest_pdf_url, timeout=30)
        pdf_response.raise_for_status()
    except Exception as e:
        print(f"Error downloading PDF: {e}")
        return None
    
    pdf_file = BytesIO(pdf_response.content)
    
    # Extract text from PDF
    try:
        full_text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                full_text += (page.extract_text() or "") + "\n"
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        return None
    
    # Parse the injury report
    injuries_by_team = {}
    not_yet_submitted = set()
    
    # Split into lines for processing
    lines = full_text.split('\n')
    
    current_team = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if this line is a team name
        for team_key in TEAM_NAMES.keys():
            if team_key in line and len(line) < 50:  # Team names are short lines
                current_team = normalize_team_name(team_key)
                if current_team not in injuries_by_team:
                    injuries_by_team[current_team] = []
                break
        
        # Check for "NOT YET SUBMITTED"
        if current_team and "NOT YET SUBMITTED" in line.upper():
            not_yet_submitted.add(current_team)
            continue
        
        # Match player entries: "Last, First Status Reason"
        # Pattern for Out, Doubtful, or Questionable
        pattern = r"([A-Za-z\-\'\.]+(?:\s+(?:Jr\.|Sr\.|III|II|IV))?),\s*([A-Za-z\-\'\.]+)\s+(Out|Doubtful|Questionable)"
        match = re.search(pattern, line, re.IGNORECASE)
        
        if match and current_team:
            last_name = match.group(1).strip()
            first_name = match.group(2).strip()
            status = match.group(3).strip().title()  # Normalize to Title Case
            
            full_name = f"{first_name} {last_name}"
            
            # Avoid duplicates
            existing_names = [p['name'] for p in injuries_by_team.get(current_team, [])]
            if full_name not in existing_names:
                injuries_by_team[current_team].append({
                    'name': full_name,
                    'status': status
                })
    
    # Sort players within each team: Out first, then Doubtful, then Questionable
    status_order = {'Out': 0, 'Doubtful': 1, 'Questionable': 2}
    for team in injuries_by_team:
        injuries_by_team[team].sort(key=lambda x: status_order.get(x['status'], 3))
    
    # Count totals
    total_players = sum(len(players) for players in injuries_by_team.values())
    print(f"Loaded {total_players} injured players across {len(injuries_by_team)} teams")
    
    return {
        'injuries': injuries_by_team,
        'not_yet_submitted': list(not_yet_submitted)
    }

def build_injuries_data():
    """
    Build the complete injuries data structure
    """
    result = scrape_injuries()
    
    if not result:
        # Return empty structure on failure
        et = pytz.timezone('America/New_York')
        now = datetime.now(et)
        return {
            'injuries': {},
            'not_yet_submitted': [],
            'updated': now.strftime('%Y-%m-%d %I:%M %p ET'),
            'error': 'Failed to fetch injury report'
        }
    
    # Add timestamp
    et = pytz.timezone('America/New_York')
    now = datetime.now(et)
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
        
        # Show sample
        print("\nSample injuries:")
        count = 0
        for team, players in data['injuries'].items():
            if count >= 3:
                break
            print(f"  {team}:")
            for p in players[:3]:
                print(f"    - {p['name']} ({p['status']})")
            count += 1

if __name__ == "__main__":
    main()
