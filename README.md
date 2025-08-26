# Cato Site Map

Interactive map visualization for Cato Networks sites and POP locations.

## Prerequisites

- Python 3.7+
- Cato Networks API credentials (Account ID and API Key)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your Cato API credentials:

Create a `.env` file in the project root:
```
CATO_ACCOUNT_ID=your_account_id_here
CATO_API_KEY=your_api_key_here
```

Alternatively, set environment variables:
```bash
export CATO_ACCOUNT_ID=your_account_id_here
export CATO_API_KEY=your_api_key_here
```

## Running the Application

### Quick Start - Try the Example

To quickly see the map with sample data (no API credentials needed):

```bash
python cato-site-map-folium.py --example
```

This will:
- Use the included mock data files with 160+ sites worldwide
- Generate an interactive HTML map
- Automatically open the map in your default browser

### With Real Cato Data

If you have Cato API credentials, generate the map with your actual network data:

```bash
python cato-site-map-folium.py
```

### Output

The script generates `cato_site_map.html` which:
- Opens automatically in your default browser
- Can be shared as a standalone HTML file
- Works offline without any server requirements
- Can be opened by double-clicking the file

## Features

- **Static HTML Map**: Generates a standalone HTML file that works offline
- **Layer Control**: Toggle visibility of:
  - Connected sites
  - Disconnected sites
  - POPs (Points of Presence)
  - POP connections (purple dashed lines)
  - POP labels
  - Site labels
- **Visual Indicators**:
  - Blue dots: Connected sites
  - Red dots: Disconnected sites  
  - Filled green circles: POPs with connected sites
  - Unfilled green circles: POPs without connected sites
  - Purple dashed lines: Site-to-POP connections
- **Interactive Elements**:
  - Hover over markers for quick tooltips
  - Click markers for detailed information
  - Pan and zoom to explore your network
  - Toggle layers on/off with the control panel
- **No Server Required**: Double-click the HTML file to open in any browser

## Example Data

The `--example` option uses comprehensive mock data that includes:
- **160+ sites** across all continents
- Sites from major cities worldwide including:
  - North America: US, Canada, Mexico
  - Europe: UK, France, Germany, Italy, Spain, Netherlands, Belgium, Poland, and more
  - Asia: China, Japan, India, Southeast Asia
  - Africa: Egypt, Kenya, South Africa, Nigeria, Morocco, and others
  - South America: Brazil, Argentina, Colombia
  - Oceania: Australia, New Zealand, Pacific Islands
- **94 global POPs** (Points of Presence)
- Realistic network connections between sites and their nearest POPs

## Required Files

The following files must be present in the project directory:
- `cclatlong.csv` - Country geolocation data
- `worldcities.csv` - City geolocation data
- `cato.py` - Cato API helper module (only needed for real data)
- `mock_accountSnapshot.json` - Mock site data (only needed for --example option)
- `mock_popLocationList.json` - Mock POP data (only needed for --example option)

## Troubleshooting

If you encounter errors:
1. Verify your API credentials are correct
2. Ensure all required CSV files are present
3. Check that you have network connectivity to the Cato API
4. Make sure all Python dependencies are installed