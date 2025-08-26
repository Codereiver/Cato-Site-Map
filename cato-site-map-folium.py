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
                    "lat": city["lat"],
                    "long": city["lng"]
                })
        if not found:
            raise ValueError(f"Unknown POP city {keyname}")
    
    return snapshot, pop_cities

def load_mock_data():
    """Load mock data from JSON files"""
    print("[*] Using mock data from JSON files")
    
    # Load mock accountSnapshot data
    mock_snapshot_path = Path(__file__).parent / "mock_accountSnapshot.json"
    if not mock_snapshot_path.exists():
        raise RuntimeError(f"Mock data file not found: {mock_snapshot_path}")
    try:
        with open(mock_snapshot_path, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in mock_accountSnapshot.json: {e}")
    
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
                    "lat": city["lat"],
                    "long": city["lng"]
                })
        if not found:
            print(f"[!] Warning: Unknown POP city {keyname}")
    
    return snapshot, pop_cities

# Load data based on command line argument
if args.example:
    snapshot, pop_cities = load_mock_data()
else:
    snapshot, pop_cities = load_real_data()


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
connectivity_lines_group = folium.FeatureGroup(name="POP Connections", show=False)
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
            
            lat = devices[0]["interfaces"][0]["tunnelRemoteIPInfo"]["latitude"]
            lon = devices[0]["interfaces"][0]["tunnelRemoteIPInfo"]["longitude"]
            pop_name = devices[0]["interfaces"][0]["popName"]
        except (KeyError, IndexError, TypeError) as e:
            print(f"[!] Warning: Skipping malformed site data: {e}")
            continue
        
        # Store connection info
        if pop_name in pop_locations:
            site_connections.append({
                "site_name": site["info"]["name"],
                "site_location": (lat, lon),
                "pop_name": pop_name,
                "pop_location": pop_locations[pop_name]
            })
        
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
        lat = 0
        lon = 0
        for row in COUNTRIES:
            if row["Alpha-2 code"] == site["info"]["countryCode"]:
                lat = float(row["Latitude (average)"])
                lon = float(row["Longitude (average)"])
                break
        
        # Add some random noise
        lat += (random.randint(-10,+10)/5)
        lon += (random.randint(-10,+10)/5)
        
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
title_html = '''
<div style="position: fixed; 
            top: 10px; left: 50%; transform: translateX(-50%);
            width: 300px; height: 40px; 
            background-color: white; border: 2px solid black; z-index:9999; 
            font-size: 18px; font-weight: bold; text-align: center; padding: 8px;">
    Cato Site Map
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