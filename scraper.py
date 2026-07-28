import urllib.request
from bs4 import BeautifulSoup
import json
import time
import re
import sys

# Configure stdout for UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Headers to mimic a real browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

# Dictionary of Primera & Segunda División clubs and their slugs in fichajes.com
SLUG_TO_NAME = {
    # Primera División
    "real-madrid-cf": "Real Madrid",
    "fc-barcelona": "FC Barcelona",
    "club-atletico-de-madrid": "Atlético de Madrid",
    "real-sociedad-de-futbol": "Real Sociedad",
    "real-club-celta-de-vigo": "Celta de Vigo",
    "athletic-club-de-bilbao": "Athletic Bilbao",
    "sevilla-fc": "Sevilla",
    "real-betis-balompie": "Real Betis",
    "villarreal-cf": "Villarreal",
    "valencia-cf": "Valencia",
    "deportivo-alaves": "Alavés",
    "ca-osasuna": "Osasuna",
    "getafe-cf": "Getafe",
    "rayo-vallecano": "Rayo Vallecano",
    "rcd-espanyol": "Espanyol",
    "girona-fc": "Girona",
    "real-club-deportivo-mallorca": "Mallorca",
    "real-valladolid-cf": "Real Valladolid",
    "deportivo-de-la-coruna": "Deportivo de la Coruña",
    "elche-cf": "Elche",
    "levante-ud": "Levante",
    "malaga-cf": "Málaga",
    "real-racing-club-de-santander": "Racing de Santander",
    "real-oviedo": "Real Oviedo",
    
    # Segunda División & historical
    "albacete-balompie": "Albacete",
    "ud-almeria": "Almería",
    "burgos-cf": "Burgos",
    "cadiz-cf": "Cádiz",
    "cd-castellon": "Castellón",
    "cd-eldense": "Eldense",
    "cd-leganes": "CD Leganés",
    "cd-tenerife": "Tenerife",
    "ce-sabadell-fc": "Sabadell",
    "cordoba-cf": "Córdoba",
    "fc-andorra": "FC Andorra",
    "granada-cf": "Granada",
    "real-club-celta-de-vigo-ii": "Celta de Vigo B",
    "real-sociedad-de-futbol-b": "Real Sociedad B",
    "real-sporting-de-gijon": "Sporting de Gijón",
    "sd-eibar": "Eibar",
    "ud-las-palmas": "Las Palmas",
    "ad-ceuta-fc": "Ceuta",
    "cultural-leonesa": "Cultural Leonesa",
    "sd-huesca": "Huesca",
    "cd-mirandes": "Mirandés",
    "real-zaragoza": "Real Zaragoza",
}

# Filial naming patterns (special B team mappings)
FILIAL_PATTERNS = {
    r"castilla": "Real Madrid B",
    r"real madrid b": "Real Madrid B",
    r"barcelona b": "FC Barcelona B",
    r"barça atlètic": "FC Barcelona B",
    r"atlético madrid b": "Atlético de Madrid B",
    r"atlético de madrid b": "Atlético de Madrid B",
    r"celta de vigo b": "Celta de Vigo B",
    r"celta de vigo ii": "Celta de Vigo B",
    r"real sociedad b": "Real Sociedad B",
    r"sanse": "Real Sociedad B",
    r"villarreal b": "Villarreal B",
    r"sevilla atlético": "Sevilla B",
    r"betis deportivo": "Real Betis B",
    r"bilbao athletic": "Athletic Bilbao B",
    r"alavés b": "Alavés B",
    r"osasuna b": "Osasuna B",
    r"valencia mestalla": "Valencia B",
    r"real valladolid b": "Real Valladolid B",
    r"promesas": "Real Valladolid B",
}

# External leagues keyword matching
LEAGUE_KEYWORDS = {
    "Premier League": [
        "chelsea", "manchester", "united", "city", "arsenal", "liverpool", "tottenham", 
        "spurs", "bournemouth", "newcastle", "aston villa", "everton", "west ham", 
        "leicester", "wolverhampton", "wolves", "brighton", "brentford", "fulham", 
        "crystal palace", "nottingham", "sheffield", "burnley", "luton", "leeds", 
        "southampton", "ipswich"
    ],
    "Bundesliga": [
        "bayern", "borussia", "dortmund", "leverkusen", "leipzig", "frankfurt", 
        "eintracht", "schalke", "stuttgart", "wolfsburgo", "wolfsburg", "mönchengladbach", 
        "gladbach", "werder", "bremen", "köln", "colonia", "hoffenheim", "friburgo", 
        "freiburg", "mainz", "maguncia", "augsburgo", "augsburg", "union berlin", 
        "bochum", "heidenheim", "darmstadt", "st. pauli", "holstein kiel"
    ],
    "Ligue 1": [
        "paris", "psg", "monaco", "mónaco", "lyon", "olympique", "marseille", "marsella", 
        "lille", "nice", "niza", "rennes", "lens", "reims", "nantes", "brest", 
        "montpellier", "toulouse", "strasbourg", "estrasburgo", "metz", "lorient", "auxerre",
        "saint-étienne"
    ],
    "Serie A": [
        "juventus", "inter", "milan", "roma", "napoli", "nápoles", "lazio", "atalanta", 
        "fiorentina", "bologna", "bolonia", "torino", "monza", "genoa", "udinese", 
        "sassuolo", "empoli", "salernitana", "cagliari", "lecce", "frosinone", "verona", 
        "palermo", "sampdoria", "como", "parma", "venezia"
    ]
}

def clean_club_name(name):
    # Remove leading/trailing whitespaces and clean newlines
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def get_node_for_club(club_name, club_slug=None):
    if not club_name:
        return "Resto del mundo"
        
    club_name_cleaned = clean_club_name(club_name)
    club_name_lower = club_name_cleaned.lower()
    
    # 1. Match from our slug dictionary
    if club_slug and club_slug in SLUG_TO_NAME:
        return SLUG_TO_NAME[club_slug]
        
    # 2. Check for filiales/B teams (prioritized)
    for pattern, normalized_name in FILIAL_PATTERNS.items():
        if re.search(pattern, club_name_lower):
            return normalized_name
            
    # 3. Check if it's a known Spanish club by name matching
    for slug, name in SLUG_TO_NAME.items():
        if club_name_lower == name.lower() or club_name_lower == slug.replace('-', ' '):
            return name
            
    # 4. Check external leagues
    for league, keywords in LEAGUE_KEYWORDS.items():
        for kw in keywords:
            if kw in club_name_lower:
                return league
                
    # 5. Default to Resto del mundo
    return "Resto del mundo"

def fetch_club_transfers(club_slug, club_name, season):
    url = f"https://www.fichajes.com/equipo/{club_slug}/altas-bajas/{season}?partial=1"
    req = urllib.request.Request(url, headers=HEADERS)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
        soup = BeautifulSoup(html, 'html.parser')
        transfers = soup.find_all('div', class_='transfer')
        parsed_transfers = []
        
        for div in transfers:
            # Skip if inside blockVertical with "mayores" title (just in case)
            parent_block = div.find_parent('div', class_='blockVertical')
            if parent_block:
                title_el = parent_block.find(class_='blockVertical__title')
                if title_el and ("mayores" in title_el.text.lower() or "ventas" in title_el.text.lower()):
                    continue
            
            player_el = div.find(class_='transfer__name')
            player = player_el.text.strip() if player_el else 'Unknown Player'
            
            age_el = div.find(class_='transfer__age')
            age = age_el.text.strip() if age_el else ''
            # Normalize age (e.g. "25 años" -> "25")
            age_match = re.search(r'\d+', age)
            age_val = int(age_match.group(0)) if age_match else None
            
            cost_el = div.find(class_=lambda c: c and 'transfer__tag' in c)
            cost = cost_el.text.strip() if cost_el else 'Gratis/Cesión'
            
            prev_club_el = div.find(class_='transfer__previousClubName')
            prev_club_name = prev_club_el.text.strip() if prev_club_el else 'Unknown'
            # Extract previous club slug if link exists
            prev_club_slug = None
            if prev_club_el and prev_club_el.find('a'):
                prev_href = prev_club_el.find('a').get('href', '')
                slug_match = re.search(r'/equipo/([^/]+)/?', prev_href)
                if slug_match:
                    prev_club_slug = slug_match.group(1)
            
            next_club_el = div.find(class_='transfer__nextClubName')
            next_club_name = next_club_el.text.strip() if next_club_el else 'Unknown'
            # Extract next club slug if link exists
            next_club_slug = None
            if next_club_el and next_club_el.find('a'):
                next_href = next_club_el.find('a').get('href', '')
                slug_match = re.search(r'/equipo/([^/]+)/?', next_href)
                if slug_match:
                    next_club_slug = slug_match.group(1)
            
            # Identify source and target nodes
            source_node = get_node_for_club(prev_club_name, prev_club_slug)
            target_node = get_node_for_club(next_club_name, next_club_slug)
            
            # Since we're scraping from the perspective of club_name, one of the nodes should map to club_name
            # Let's override to ensure exact match if they represent our scraped club
            scraped_club_node = SLUG_TO_NAME[club_slug]
            if prev_club_slug == club_slug or get_node_for_club(prev_club_name, prev_club_slug) == scraped_club_node:
                source_node = scraped_club_node
            if next_club_slug == club_slug or get_node_for_club(next_club_name, next_club_slug) == scraped_club_node:
                target_node = scraped_club_node
                
            parsed_transfers.append({
                "player": player,
                "age": age_val,
                "cost": cost,
                "from_club_raw": prev_club_name,
                "to_club_raw": next_club_name,
                "source_node": source_node,
                "target_node": target_node,
                "season": season
            })
            
        return parsed_transfers
    except Exception as e:
        print(f"Error fetching transfers for {club_name} ({season}): {e}")
        return []

def main():
    print("Starting Web Scraper for La Liga transfers...")
    seasons = ["2025-2026", "2026-2027"]
    all_transfers = []
    
    total_clubs = len(SLUG_TO_NAME)
    club_idx = 0
    
    # Track unique transfers using a set of tuples (player, from_club, to_club, season)
    seen_transfers = set()
    
    for slug, name in SLUG_TO_NAME.items():
        club_idx += 1
        print(f"[{club_idx}/{total_clubs}] Processing {name} ({slug})...")
        
        for season in seasons:
            transfers = fetch_club_transfers(slug, name, season)
            print(f"  Season {season}: Found {len(transfers)} transfers.")
            
            for t in transfers:
                key = (t["player"].lower(), t["source_node"].lower(), t["target_node"].lower(), t["season"])
                if key not in seen_transfers:
                    seen_transfers.add(key)
                    all_transfers.append(t)
            
            # Polite scraping sleep delay
            time.sleep(0.5)
            
    print(f"\nScraping complete! Total unique transfers extracted: {len(all_transfers)}")
    
    # Save dataset to JSON
    output_file = "transfers_dataset.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_transfers, f, ensure_ascii=False, indent=2)
    print(f"Dataset successfully saved to {output_file}")

if __name__ == "__main__":
    main()
