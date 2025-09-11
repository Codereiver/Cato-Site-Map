import argparse
import csv
import json
import os
import random
import html
from pathlib import Path
from dotenv import load_dotenv

import folium
from folium import plugins
from cato import API

# Optional import for LLM functionality
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


#
# Load geolocation data
#
COUNTRIES = []
print("[*] Loading country geolocation data from cclatlong.csv")
cclatlong_path = Path(__file__).parent / "cclatlong.csv"
if not cclatlong_path.exists():
    raise FileNotFoundError(f"Required file not found: {cclatlong_path}")
with open(cclatlong_path, "r", encoding="utf-8") as file:
    for row in csv.DictReader(file):
        COUNTRIES.append(row)


#
# Load cities data
#
CITIES = []
print("[*] Loading city geolocation data from worldcities.csv")
worldcities_path = Path(__file__).parent / "worldcities.csv"
if not worldcities_path.exists():
    raise FileNotFoundError(f"Required file not found: {worldcities_path}")
with open(worldcities_path, "r", encoding="utf-8") as file:
    for row in csv.DictReader(file):
        CITIES.append(row)


#
# Parse command line arguments
#
parser = argparse.ArgumentParser(description='Generate Cato Site Map')
parser.add_argument('--example', action='store_true', help='Use mock data from JSON files instead of API calls')
parser.add_argument('--snapshot-file', type=str, default='mock_accountSnapshot.json', 
                    help='Path to custom accountSnapshot JSON file (only used with --example, default: mock_accountSnapshot.json)')
parser.add_argument('--llm-cities', action='store_true', 
                    help='Use LLM to estimate city locations for sites without configured cities (requires ANTHROPIC_API_KEY)')
args = parser.parse_args()

def load_real_data():
    """Load data from Cato API"""
    #
    # Get the Cato account ID and API key from environment variables
    # or a .env file.
    #
    load_dotenv()
    ID = os.getenv('CATO_ACCOUNT_ID')
    key = os.getenv('CATO_API_KEY')
    if not ID or not key:
        raise ValueError("CATO_ACCOUNT_ID and CATO_API_KEY environment variables must be set")

    #
    # Create the API connection
    #
    print("[*] Creating the API connection")
    C = API(key)    

    #
    # Get the accountSnapshot data from the Cato API
    #
    print("[*] Calling accountSnapshot")
    variables = {
        "accountID":ID
    }
    query = """query accountSnapshot($accountID:ID!) {
        accountSnapshot(accountID:$accountID) {
            sites {
                connectivityStatus
                info {
                    name
                    countryCode
                    cityName
                    countryName
                    countryStateName
                }
                devices {
                    interfaces {
                        tunnelRemoteIPInfo {
                            latitude
                            longitude
                        }
                        popName
                    }
                }
            }
        }
    }"""
    success,snapshot = C.send("accountSnapshot", variables, query)
    if not success:
        # Don't expose API response details in error message
        error_msg = snapshot.get('error', 'Unknown error')
        print(f"[!] API Error: {error_msg}")
        raise RuntimeError('Failed to retrieve account snapshot')

    #
    # Get the POP location list from the Cato API
    #
    print("[*] Calling popLocationList")
    variables = {
        "accountId":ID
    }
    query = """query popLocationList($accountId: ID!) {
    popLocations(accountId: $accountId) {
    popLocationList {
        items {
        id
        name
        displayName
        country {
            id
            name
        }
        isPrivate
        cloudInterconnect {
            taggingMethod
            providerName
        }
        }
    }
    }
    }"""
    success,popLocationList = C.send("popLocationList", variables, query)
    if not success:
        # Don't expose API response details in error message
        error_msg = popLocationList.get('error', 'Unknown error')
        print(f"[!] API Error: {error_msg}")
        raise RuntimeError('Failed to retrieve POP location list')

    #
    # Find a city for each POP. Some manual fixups required to accommodate POP names
    # which don't exactly match their city.
    #
    pop_cities = []
    fixups = {
        "beijingct": "beijing",
        "shanghaict": "shanghai", 
        "shenzhenct": "shenzhen",
        "kansas-city": "kansas city",
        "ho chi minh": "ho chi minh city",
        "tel aviv": "tel aviv-yafo",
        "hong kong equinix": "hong kong",
    }
    for pop in popLocationList["data"]["popLocations"]["popLocationList"]["items"]:
        keyname = ''.join([char for char in pop["name"] if not char.isdigit()]).lower()
        if "_aws" in keyname:
            keyname = keyname[:keyname.find("_")]
        for k,v in fixups.items():
            if keyname == k:
                keyname = v
        found = False
        for city in CITIES:
            if keyname == city["city_ascii"].lower() and pop["country"]["name"].lower() == city["country"].lower():
                found = True 
                pop_cities.append({
                    "name": pop["name"],
                    "displayName": pop.get("displayName", pop["name"]),
                    "lat": city["lat"],
                    "long": city["lng"]
                })
        if not found:
            raise ValueError(f"Unknown POP city {keyname}")
    
    return snapshot, pop_cities

def load_mock_data(snapshot_file='mock_accountSnapshot.json'):
    """Load mock data from JSON files"""
    print("[*] Using mock data from JSON files")
    
    # Load mock accountSnapshot data
    # Support both absolute and relative paths
    if Path(snapshot_file).is_absolute():
        mock_snapshot_path = Path(snapshot_file)
    else:
        mock_snapshot_path = Path(__file__).parent / snapshot_file
    
    if not mock_snapshot_path.exists():
        raise RuntimeError(f"Mock data file not found: {mock_snapshot_path}")
    
    print(f"[*] Loading accountSnapshot from: {mock_snapshot_path}")
    try:
        with open(mock_snapshot_path, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in {snapshot_file}: {e}")
    
    # Load mock popLocationList data
    mock_pop_path = Path(__file__).parent / "mock_popLocationList.json"
    if not mock_pop_path.exists():
        raise RuntimeError(f"Mock data file not found: {mock_pop_path}")
    try:
        with open(mock_pop_path, "r", encoding="utf-8") as f:
            popLocationList = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in mock_popLocationList.json: {e}")

    #
    # Find a city for each POP using the same logic as real data
    #
    pop_cities = []
    fixups = {
        "beijingct": "beijing",
        "shanghaict": "shanghai", 
        "shenzhenct": "shenzhen",
        "kansas-city": "kansas city",
        "ho chi minh": "ho chi minh city",
        "tel aviv": "tel aviv-yafo",
        "hong kong equinix": "hong kong",
    }
    for pop in popLocationList["data"]["popLocations"]["popLocationList"]["items"]:
        keyname = ''.join([char for char in pop["name"] if not char.isdigit()]).lower()
        if "_aws" in keyname:
            keyname = keyname[:keyname.find("_")]
        for k,v in fixups.items():
            if keyname == k:
                keyname = v
        found = False
        for city in CITIES:
            if keyname == city["city_ascii"].lower() and pop["country"]["name"].lower() == city["country"].lower():
                found = True 
                pop_cities.append({
                    "name": pop["name"],
                    "displayName": pop.get("displayName", pop["name"]),
                    "lat": city["lat"],
                    "long": city["lng"]
                })
        if not found:
            print(f"[!] Warning: Unknown POP city {keyname}")
    
    return snapshot, pop_cities

def estimate_cities_with_llm(sites_without_cities):
    """
    Use LLM to estimate city names for sites without configured cities.
    
    Args:
        sites_without_cities: List of dicts with 'name' and 'country_code' keys
    
    Returns:
        Dict mapping site names to estimated city names
    """
    if not ANTHROPIC_AVAILABLE:
        print("[!] Warning: anthropic library not installed. Install with: pip install anthropic")
        return {}
    
    if not sites_without_cities:
        return {}
    
    # Get API key from environment
    load_dotenv()
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("[!] Warning: ANTHROPIC_API_KEY not found in environment. Skipping LLM city estimation.")
        return {}
    
    print(f"[*] Using LLM to estimate cities for {len(sites_without_cities)} sites without configured cities")
    
    # Process in batches to avoid token limits and improve reliability
    batch_size = 50
    all_estimates = {}
    
    for i in range(0, len(sites_without_cities), batch_size):
        batch = sites_without_cities[i:i+batch_size]
        print(f"[*] Processing batch {i//batch_size + 1} of {(len(sites_without_cities) + batch_size - 1)//batch_size}")
        
        try:
            client = anthropic.Anthropic(api_key=api_key)
            
            # Prepare the prompt
            sites_list = "\n".join([f"- Site: '{site['name']}', Country Code: {site['country_code']}" 
                                    for site in batch])
            
            prompt = f"""Given the following list of site names and their country codes, please estimate the most likely city name for each site.
Site names often contain location hints (city names, airport codes, office names, etc.).

For each site, return a JSON object with the site name as key and the estimated city name as value.
If you cannot determine a city, use null as the value.
Important: Return ONLY valid JSON without any markdown formatting, code blocks, or explanations.

Sites:
{sites_list}

Return only the JSON object."""

            message = client.messages.create(
                model="claude-3-haiku-20240307",  # Using a fast, cost-effective model
                max_tokens=2000,
                temperature=0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse the response
            response_text = message.content[0].text.strip()
            
            # Clean up the response - remove any markdown or code block formatting
            if "```" in response_text:
                # Extract content between code blocks
                parts = response_text.split("```")
                for part in parts:
                    if part.strip().startswith("{"):
                        response_text = part
                        break
                    elif part.strip().startswith("json"):
                        response_text = part[4:].strip()
                        break
            
            # Remove any leading/trailing whitespace or newlines
            response_text = response_text.strip()
            
            # Ensure it starts with { and ends with }
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}")
            if start_idx != -1 and end_idx != -1:
                response_text = response_text[start_idx:end_idx+1]
            
            try:
                estimated_cities = json.loads(response_text)
                
                # Log the estimations
                for site_name, city_name in estimated_cities.items():
                    if city_name:
                        print(f"[*] LLM estimated: '{site_name}' -> '{city_name}'")
                
                all_estimates.update(estimated_cities)
                
            except json.JSONDecodeError as je:
                print(f"[!] JSON parsing error in batch {i//batch_size + 1}: {je}")
                print(f"[!] Response text (first 200 chars): {response_text[:200]}")
                # Continue with next batch
                
        except Exception as e:
            print(f"[!] Error processing batch {i//batch_size + 1}: {e}")
            # Continue with next batch
    
    return all_estimates

def get_coordinates_for_cities(unknown_cities):
    """
    Use LLM to get latitude/longitude coordinates for cities not in the database.
    
    Args:
        unknown_cities: List of dicts with 'city_name' and 'country_name' keys
    
    Returns:
        Dict mapping "city_name, country_name" to {"lat": float, "lng": float}
    """
    if not ANTHROPIC_AVAILABLE:
        return {}
    
    if not unknown_cities:
        return {}
    
    # Get API key from environment
    load_dotenv()
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        return {}
    
    # Remove duplicates
    unique_cities = {}
    for city_info in unknown_cities:
        key = f"{city_info['city_name']}, {city_info['country_name']}"
        unique_cities[key] = city_info
    
    if not unique_cities:
        return {}
    
    print(f"[*] Using LLM to get coordinates for {len(unique_cities)} cities not in database")
    
    # Process in batches
    batch_size = 30
    all_coordinates = {}
    city_list = list(unique_cities.items())
    
    for i in range(0, len(city_list), batch_size):
        batch = city_list[i:i+batch_size]
        print(f"[*] Processing coordinates batch {i//batch_size + 1} of {(len(city_list) + batch_size - 1)//batch_size}")
        
        try:
            client = anthropic.Anthropic(api_key=api_key)
            
            # Prepare the prompt
            cities_text = "\n".join([f"- {city_key}" for city_key, _ in batch])
            
            prompt = f"""For each of the following cities, provide the latitude and longitude coordinates.
Return a JSON object where each key is the city name exactly as provided, and the value is an object with "lat" and "lng" fields.

Cities:
{cities_text}

Example format:
{{
  "City Name, Country": {{"lat": 12.345, "lng": -67.890}},
  ...
}}

Return only valid JSON without any markdown formatting or explanations."""

            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2000,
                temperature=0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse the response
            response_text = message.content[0].text.strip()
            
            # Clean up the response
            if "```" in response_text:
                parts = response_text.split("```")
                for part in parts:
                    if part.strip().startswith("{"):
                        response_text = part
                        break
                    elif part.strip().startswith("json"):
                        response_text = part[4:].strip()
                        break
            
            response_text = response_text.strip()
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}")
            if start_idx != -1 and end_idx != -1:
                response_text = response_text[start_idx:end_idx+1]
            
            try:
                coordinates = json.loads(response_text)
                
                # Validate and log the coordinates
                for city_key, coords in coordinates.items():
                    if isinstance(coords, dict) and "lat" in coords and "lng" in coords:
                        try:
                            lat = float(coords["lat"])
                            lng = float(coords["lng"])
                            if -90 <= lat <= 90 and -180 <= lng <= 180:
                                all_coordinates[city_key] = {"lat": lat, "lng": lng}
                                print(f"[*] LLM coordinates: {city_key} -> ({lat:.4f}, {lng:.4f})")
                            else:
                                print(f"[!] Invalid coordinates for {city_key}: {coords}")
                        except (ValueError, TypeError):
                            print(f"[!] Invalid coordinate format for {city_key}: {coords}")
                
            except json.JSONDecodeError as je:
                print(f"[!] JSON parsing error in coordinates batch {i//batch_size + 1}: {je}")
                
        except Exception as e:
            print(f"[!] Error processing coordinates batch {i//batch_size + 1}: {e}")
    
    return all_coordinates

# Load data based on command line argument
if args.example:
    snapshot, pop_cities = load_mock_data(args.snapshot_file)
    # Extract filename for title (remove path and extension)
    snapshot_filename = Path(args.snapshot_file).stem
else:
    snapshot, pop_cities = load_real_data()
    snapshot_filename = None

# Prepare LLM city estimations if requested
llm_city_estimates = {}
llm_city_coordinates = {}  # Store LLM-provided coordinates for unknown cities

if args.llm_cities:
    # First pass: Collect sites without configured cities
    sites_without_cities = []
    for site in snapshot["data"]["accountSnapshot"]["sites"]:
        site_info = site.get("info", {})
        if not site_info.get("cityName"):
            sites_without_cities.append({
                "name": site_info.get("name", "Unknown"),
                "country_code": site_info.get("countryCode", "")
            })
    
    # Get LLM estimates for city names
    llm_city_estimates = estimate_cities_with_llm(sites_without_cities)
    
    # Second pass: Identify which cities (configured or estimated) are not in database
    unknown_cities_list = []
    for site in snapshot["data"]["accountSnapshot"]["sites"]:
        site_info = site.get("info", {})
        site_name = site_info.get("name", "Unknown")
        city_name = site_info.get("cityName")
        country_name = site_info.get("countryName")
        
        # Use LLM-estimated city if no configured city
        if not city_name and site_name in llm_city_estimates:
            city_name = llm_city_estimates[site_name]
        
        if city_name and country_name:
            # Check if city exists in database
            found_city = False
            for city in CITIES:
                city_match = city["city_ascii"].lower() == city_name.lower() or city["city"].lower() == city_name.lower()
                country_match = city["country"].lower() == country_name.lower()
                if city_match and country_match:
                    found_city = True
                    break
            
            if not found_city:
                unknown_cities_list.append({
                    "city_name": city_name,
                    "country_name": country_name
                })
    
    # Get coordinates for unknown cities from LLM
    llm_city_coordinates = get_coordinates_for_cities(unknown_cities_list)


#
# Create the Folium map
#
print("[*] Creating the map")
m = folium.Map(
    location=[20, 0],  # Center of the world
    zoom_start=2,
    tiles='OpenStreetMap'
)

# Create feature groups for different layers
pops_group = folium.FeatureGroup(name="POPs", show=True)
connected_sites_group = folium.FeatureGroup(name="Connected Sites", show=True)
disconnected_sites_group = folium.FeatureGroup(name="Disconnected Sites", show=True)
connectivity_lines_group = folium.FeatureGroup(name="POP Connections", show=True)
pop_labels_group = folium.FeatureGroup(name="POP Labels", show=False)
site_labels_group = folium.FeatureGroup(name="Site Labels", show=False)

# First pass: collect connected POPs
connected_pops = set()
for site in snapshot["data"]["accountSnapshot"]["sites"]:
    if site["connectivityStatus"].lower() == "connected":
        pop_name = site["devices"][0]["interfaces"][0]["popName"]
        if pop_name:
            connected_pops.add(pop_name)

# Add POPs to the map
pop_locations = {}  # Store POP locations for connecting lines
for pop in pop_cities:
    lat = float(pop["lat"]) + (random.randint(-1,+1)/50 + 0.05)
    lon = float(pop["long"]) + (random.randint(-1,+1)/50 + 0.05)
    pop_locations[pop["name"]] = (lat, lon)
    # Also store by displayName if different
    if pop.get("displayName") and pop["displayName"] != pop["name"]:
        pop_locations[pop["displayName"]] = (lat, lon)
    
    # Check if this POP has connected sites
    has_connected_sites = pop["name"] in connected_pops
    
    folium.CircleMarker(
        location=[lat, lon],
        radius=8,
        popup=folium.Popup(html.escape(pop["name"]), parse_html=False),
        tooltip=html.escape(pop["name"]),
        color='darkgreen',
        fill=has_connected_sites,
        fillColor='green' if has_connected_sites else None,
        fillOpacity=0.8 if has_connected_sites else 0
    ).add_to(pops_group)
    
    # Add label next to the marker
    folium.Marker(
        location=[lat, lon],
        icon=folium.DivIcon(
            html=f'<div style="font-size: 12px; color: black; font-weight: bold; margin-left: 15px; margin-top: -6px; white-space: nowrap; text-shadow: 1px 1px 1px white;">{html.escape(pop["name"])}</div>',
            icon_size=(0, 0),
            icon_anchor=(0, 0)
        )
    ).add_to(pop_labels_group)

# Add sites to the map
site_connections = []  # Store connections for drawing lines
for site in snapshot["data"]["accountSnapshot"]["sites"]:
    if site["connectivityStatus"].lower() == "connected":
        # Validate data structure before accessing
        try:
            devices = site.get("devices", [])
            if not devices or not devices[0].get("interfaces"):
                print(f"[!] Warning: Site {site.get('info', {}).get('name', 'Unknown')} has no interfaces")
                continue
            
            # Primary method: Use configured cityName if available
            site_info = site.get("info", {})
            site_name = site_info.get("name", "Unknown")
            city_name = site_info.get("cityName")
            country_name = site_info.get("countryName")
            state_name = site_info.get("countryStateName")
            
            # Check for LLM-estimated city if no configured city
            if not city_name and site_name in llm_city_estimates:
                city_name = llm_city_estimates[site_name]
                if city_name:
                    print(f"[*] Using LLM-estimated city '{city_name}' for site '{site_name}'")
            
            lat = None
            lon = None
            
            if city_name:
                # Try to find the city in our cities database
                found_city = False
                for city in CITIES:
                    # Match by city name and country (state if available)
                    city_match = city["city_ascii"].lower() == city_name.lower() or city["city"].lower() == city_name.lower()
                    country_match = country_name and city["country"].lower() == country_name.lower()
                    state_match = not state_name or city.get("admin_name", "").lower() == state_name.lower()
                    
                    if city_match and country_match and state_match:
                        lat = float(city["lat"])
                        lon = float(city["lng"])
                        found_city = True
                        break
                
                if not found_city and state_name:
                    # Try again without state matching if state was provided but didn't match
                    for city in CITIES:
                        city_match = city["city_ascii"].lower() == city_name.lower() or city["city"].lower() == city_name.lower()
                        country_match = country_name and city["country"].lower() == country_name.lower()
                        
                        if city_match and country_match:
                            lat = float(city["lat"])
                            lon = float(city["lng"])
                            found_city = True
                            print(f"[!] Warning: Site {site_info.get('name', 'Unknown')}: Using city {city_name}, {country_name} (state {state_name} not found)")
                            break
                
                if not found_city:
                    # Check if we have LLM coordinates for this city
                    city_key = f"{city_name}, {country_name}"
                    if city_key in llm_city_coordinates:
                        coords = llm_city_coordinates[city_key]
                        lat = coords["lat"]
                        lon = coords["lng"]
                        found_city = True
                        print(f"[*] Using LLM coordinates for site {site_info.get('name', 'Unknown')}: {city_name} ({lat:.4f}, {lon:.4f})")
                    else:
                        print(f"[!] Warning: Site {site_info.get('name', 'Unknown')}: City '{city_name}' not found in database, using tunnel coordinates")
            
            # Fallback: Use tunnel endpoint coordinates if city not found or not configured
            if lat is None or lon is None:
                lat = devices[0]["interfaces"][0]["tunnelRemoteIPInfo"]["latitude"]
                lon = devices[0]["interfaces"][0]["tunnelRemoteIPInfo"]["longitude"]
            else:
                # Add small random offset to prevent overlapping markers
                lat += (random.randint(-1, 1) / 100)
                lon += (random.randint(-1, 1) / 100)
            
            pop_name = devices[0]["interfaces"][0]["popName"]
        except (KeyError, IndexError, TypeError) as e:
            print(f"[!] Warning: Skipping malformed site data: {e}")
            continue
        
        # Store connection info - simplified since pop_locations now has both name and displayName
        matched_pop_name = None
        if pop_name in pop_locations:
            matched_pop_name = pop_name
        else:
            # Try case-insensitive matching as fallback
            for key in pop_locations.keys():
                if key.lower() == pop_name.lower():
                    matched_pop_name = key
                    break
        
        if matched_pop_name:
            site_connections.append({
                "site_name": site["info"]["name"],
                "site_location": (lat, lon),
                "pop_name": matched_pop_name,
                "pop_location": pop_locations[matched_pop_name]
            })
        else:
            # Raise exception for connected sites with unmatched POPs
            raise ValueError(
                f"Connected site '{site['info']['name']}' has POP '{pop_name}' "
                f"which cannot be matched to any POP in the location list. "
                f"Available POPs: {', '.join(sorted(set(p.split()[0] for p in pop_locations.keys())))[:10]}..."
            )
        
        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            popup=folium.Popup(html.escape(site["info"]["name"]), parse_html=False),
            tooltip=html.escape(site["info"]["name"]),
            color='darkblue',
            fill=True,
            fillColor='blue',
            fillOpacity=0.8
        ).add_to(connected_sites_group)
        
        # Add label next to the marker
        folium.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 12px; color: black; font-weight: bold; margin-left: 15px; margin-top: -6px; white-space: nowrap; text-shadow: 1px 1px 1px white;">{html.escape(site["info"]["name"])}</div>',
                icon_size=(0, 0),
                icon_anchor=(0, 0)
            )
        ).add_to(site_labels_group)
    else:
        # Handle disconnected sites
        site_info = site.get("info", {})
        site_name = site_info.get("name", "Unknown")
        city_name = site_info.get("cityName")
        country_name = site_info.get("countryName")
        state_name = site_info.get("countryStateName")
        country_code = site_info.get("countryCode")
        
        # Check for LLM-estimated city if no configured city
        if not city_name and site_name in llm_city_estimates:
            city_name = llm_city_estimates[site_name]
            if city_name:
                print(f"[*] Using LLM-estimated city '{city_name}' for site '{site_name}'")
        
        lat = None
        lon = None
        
        # Primary method: Use configured cityName if available
        if city_name:
            found_city = False
            for city in CITIES:
                # Match by city name and country (state if available)
                city_match = city["city_ascii"].lower() == city_name.lower() or city["city"].lower() == city_name.lower()
                country_match = country_name and city["country"].lower() == country_name.lower()
                state_match = not state_name or city.get("admin_name", "").lower() == state_name.lower()
                
                if city_match and country_match and state_match:
                    lat = float(city["lat"])
                    lon = float(city["lng"])
                    found_city = True
                    break
            
            if not found_city and state_name:
                # Try again without state matching if state was provided but didn't match
                for city in CITIES:
                    city_match = city["city_ascii"].lower() == city_name.lower() or city["city"].lower() == city_name.lower()
                    country_match = country_name and city["country"].lower() == country_name.lower()
                    
                    if city_match and country_match:
                        lat = float(city["lat"])
                        lon = float(city["lng"])
                        found_city = True
                        print(f"[!] Warning: Site {site_info.get('name', 'Unknown')}: Using city {city_name}, {country_name} (state {state_name} not found)")
                        break
            
            if not found_city:
                # Check if we have LLM coordinates for this city
                city_key = f"{city_name}, {country_name}"
                if city_key in llm_city_coordinates:
                    coords = llm_city_coordinates[city_key]
                    lat = coords["lat"]
                    lon = coords["lng"]
                    found_city = True
                    print(f"[*] Using LLM coordinates for site {site_info.get('name', 'Unknown')}: {city_name} ({lat:.4f}, {lon:.4f})")
                else:
                    print(f"[!] Warning: Site {site_info.get('name', 'Unknown')}: City '{city_name}' not found in database, using country center")
        
        # Fallback: Use country center if city not found or not configured
        if lat is None or lon is None:
            lat = 0
            lon = 0
            for row in COUNTRIES:
                if row["Alpha-2 code"] == country_code:
                    lat = float(row["Latitude (average)"])
                    lon = float(row["Longitude (average)"])
                    break
            
            # Add larger random noise for country-center placement
            lat += (random.randint(-10, 10) / 5)
            lon += (random.randint(-10, 10) / 5)
        else:
            # Add smaller random offset for city-based placement
            lat += (random.randint(-1, 1) / 100)
            lon += (random.randint(-1, 1) / 100)
        
        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            popup=folium.Popup(html.escape(site["info"]["name"]), parse_html=False),
            tooltip=html.escape(site["info"]["name"]),
            color='darkred',
            fill=True,
            fillColor='red',
            fillOpacity=0.8
        ).add_to(disconnected_sites_group)
        
        # Add label next to the marker
        folium.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 12px; color: black; font-weight: bold; margin-left: 15px; margin-top: -6px; white-space: nowrap; text-shadow: 1px 1px 1px white;">{html.escape(site["info"]["name"])}</div>',
                icon_size=(0, 0),
                icon_anchor=(0, 0)
            )
        ).add_to(site_labels_group)

# Add connectivity lines (dashed purple)
for connection in site_connections:
    line = folium.PolyLine(
        locations=[connection["site_location"], connection["pop_location"]],
        color='purple',
        weight=3,
        opacity=0.8,
        dash_array='10, 5',  # Dashed line pattern
        popup=folium.Popup(f"{html.escape(connection['site_name'])} → {html.escape(connection['pop_name'])}", parse_html=False)
    )
    connectivity_lines_group.add_child(line)

# Add all groups to the map in the desired order
m.add_child(pops_group)
m.add_child(connected_sites_group)
m.add_child(disconnected_sites_group)
m.add_child(connectivity_lines_group)
m.add_child(pop_labels_group)
m.add_child(site_labels_group)

# Add layer control
folium.LayerControl(collapsed=False).add_to(m)

# Add a title
if snapshot_filename:
    title_text = f"Cato Site Map - {snapshot_filename}"
    # Adjust width for longer titles
    title_width = max(300, len(title_text) * 12)
else:
    title_text = "Cato Site Map"
    title_width = 300

title_html = f'''
<div style="position: fixed; 
            top: 10px; left: 50%; transform: translateX(-50%);
            width: {title_width}px; height: 40px; 
            background-color: white; border: 2px solid black; z-index:9999; 
            font-size: 18px; font-weight: bold; text-align: center; padding: 8px;">
    {html.escape(title_text)}
</div>
'''
m.get_root().html.add_child(folium.Element(title_html))

# Save the map
output_file = Path("cato_site_map.html").resolve()
try:
    m.save(str(output_file))
    # Set secure file permissions (read for all, write for owner only)
    os.chmod(output_file, 0o644)
    print(f"[*] Map saved as {output_file}")
    print(f"[*] Open {output_file} in your browser to view the interactive map")
except Exception as e:
    print(f"[!] Error saving map file: {e}")
    raise

# Automatically open the map in the default browser
import webbrowser
webbrowser.open(f"file://{output_file}")
print(f"[*] Opening map in your default browser...")