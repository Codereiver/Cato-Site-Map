import csv
import json
import os
import random
from dotenv import load_dotenv

import gradio as gr
import pandas as pd
import plotly.express as px
from cato import API


#
# Load geolocation data
#
COUNTRIES = []
print("[*] Loading country geolocation data from cclatlong.csv")
with open("cclatlong.csv","r") as file:
    for row in csv.DictReader(file):
        COUNTRIES.append(row)


#
# Load cities data
#
CITIES = []
print("[*] Loading city geolocation data from worldcities.csv")
with open("worldcities.csv","r") as file:
    for row in csv.DictReader(file):
        CITIES.append(row)


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
            }
            }
        }
    }
}"""
success,snapshot = C.send("accountSnapshot", variables, query)
if not success:
    raise RuntimeError(f'ERROR calling accountSnapshot:{snapshot}')


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
    raise RuntimeError(f'ERROR calling popLocationList:{popLocationList}')


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


#
# Load snapshot and POP data into a Pandas dataframe
#
print("[*] Loading snapshot into dataframe")
lats = []
longs = []
names = []
sizes = []
colours = []
for pop in pop_cities:
    names.append(pop["name"])
    lats.append(float(pop["lat"]))
    longs.append(float(pop["long"]))
    sizes.append(12)
    colours.append("POP")
for site in snapshot["data"]["accountSnapshot"]["sites"]:
    if site["connectivityStatus"].lower() == "connected":
        names.append(site["info"]["name"])
        lats.append(site["devices"][0]["interfaces"][0]["tunnelRemoteIPInfo"]["latitude"])
        longs.append(site["devices"][0]["interfaces"][0]["tunnelRemoteIPInfo"]["longitude"])
        colours.append("Connected Site")
    else:
        names.append(site["info"]["name"])
        lat = 0
        longi = 0
        for row in COUNTRIES:
            if row["Alpha-2 code"] == site["info"]["countryCode"]:
                lat = float(row["Latitude (average)"])
                longi = float(row["Longitude (average)"])
                break
        #
        # Add some random noise to the co-ordinates to prevent multiple disconnected sites
        # in the same country from ending up on exactly the same spot. The amount of noise
        # is independent of the size of the country, which can result in disconnected dots
        # being outside a smaller country's borders.
        #
        lats.append(lat + (random.randint(-10,+10)/5))
        longs.append(longi + (random.randint(-10,+10)/5))
        colours.append("Disconnected Site")
    sizes.append(10)
dataframe = {
    "Latitude": lats,
    "Longitude": longs,
    "Site": names,
    "Size": sizes,
    "Colour": colours,
}


#
# Create a map with the given visibility settings
#
def create_map(show_pops=True, show_connected=True, show_disconnected=True):
    print("[*] Creating the map")
    
    # Filter the dataframe based on visibility settings
    df = pd.DataFrame(dataframe)
    visible_types = []
    if show_pops:
        visible_types.append("POP")
    if show_connected:
        visible_types.append("Connected Site")
    if show_disconnected:
        visible_types.append("Disconnected Site")
    
    # If no types are visible, create an empty map
    if not visible_types:
        filtered_df = pd.DataFrame({"Latitude": [], "Longitude": [], "Site": [], "Size": [], "Colour": []})
    else:
        filtered_df = df[df["Colour"].isin(visible_types)]
    
    world_map = px.scatter_mapbox(
        filtered_df,
        lat="Latitude",
        lon="Longitude",
        text="Site" if len(filtered_df) > 0 else None,
        zoom=2,
        height=700,
        color_discrete_map={"Connected Site":'blue',"Disconnected Site":'red', "POP": "green"},
        color="Colour" if len(filtered_df) > 0 else None,
        size="Size" if len(filtered_df) > 0 else None,
        size_max=10,
        hover_data={"Site":True, "Latitude":False, "Longitude":False, "Size":False, "Colour":False} if len(filtered_df) > 0 else None,
    )
    world_map.update_traces(hovertemplate='%{text}<extra></extra>')
    world_map.update_layout(mapbox_style="open-street-map")
    world_map.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    world_map.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        title=""
    ))
    return world_map


#
# Gradio app UI
#
print("[*] Creating the Gradio UI")
with gr.Blocks() as demo:
    with gr.Row():
        show_pops = gr.Checkbox(label="Show POPs", value=True)
        show_connected = gr.Checkbox(label="Show Connected Sites", value=True)
        show_disconnected = gr.Checkbox(label="Show Disconnected Sites", value=True)
    with gr.Column():
        plot = gr.Plot(value=create_map())
    
    # Update map when checkboxes change
    show_pops.change(create_map, inputs=[show_pops, show_connected, show_disconnected], outputs=plot)
    show_connected.change(create_map, inputs=[show_pops, show_connected, show_disconnected], outputs=plot)
    show_disconnected.change(create_map, inputs=[show_pops, show_connected, show_disconnected], outputs=plot)
print("[*] Launching Gradio")
demo.launch()       