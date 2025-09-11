# Cato Site Map

Interactive map visualization for Cato Networks sites and POP locations.

## Prerequisites

- Python 3.7+
- Cato Networks API credentials (Account ID and API Key)
- (Optional) Anthropic API key for enhanced city geolocation

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your API credentials:

Create a `.env` file in the project root:
```
CATO_ACCOUNT_ID=your_account_id_here
CATO_API_KEY=your_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here  # Optional, for LLM features
```

Alternatively, set environment variables:
```bash
export CATO_ACCOUNT_ID=your_account_id_here
export CATO_API_KEY=your_api_key_here
export ANTHROPIC_API_KEY=your_anthropic_api_key_here  # Optional
```

## Running the Application

### Quick Start - Try the Example

To quickly see the map with sample data (no API credentials needed):

```bash
python cato-site-map-folium.py --example
```

You can also use a custom mock data file:
```bash
python cato-site-map-folium.py --example --snapshot-file custom_data.json
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

### Enhanced City Geolocation with LLM

For improved accuracy in site placement, enable LLM-based city geolocation:

```bash
# With example data
python cato-site-map-folium.py --example --llm-cities

# With real data
python cato-site-map-folium.py --llm-cities
```

This feature:
- **Estimates city names** for sites without configured cities based on site names
- **Provides coordinates** for cities not in the local database
- **Improves map accuracy** by reducing reliance on tunnel endpoints or country centers
- Requires an Anthropic API key in your `.env` file

### Output

The script generates `cato_site_map.html` which:
- Opens automatically in your default browser
- Can be shared as a standalone HTML file
- Works offline without any server requirements
- Can be opened by double-clicking the file

## Technology

This project uses [Folium](https://python-visualization.github.io/folium/latest/), a powerful Python library that creates interactive maps using Leaflet.js. Folium makes it easy to:
- Generate interactive web maps from Python data
- Add custom markers, popups, and layers
- Create standalone HTML files that work offline
- Integrate with popular mapping providers like OpenStreetMap

Learn more about Folium:
- [Documentation](https://python-visualization.github.io/folium/latest/)
- [GitHub Repository](https://github.com/python-visualization/folium)
- [Examples Gallery](https://python-visualization.github.io/folium/latest/gallery.html)

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
- **LLM-Enhanced Geolocation** (Optional):
  - Automatically estimates city names from site descriptions
  - Provides accurate coordinates for cities not in the database
  - Processes large datasets in efficient batches
  - Gracefully handles errors and continues processing

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

## Command Line Options

```bash
python cato-site-map-folium.py [options]
```

| Option | Description |
|--------|-------------|
| `--example` | Use mock data instead of API calls |
| `--snapshot-file FILE` | Custom accountSnapshot JSON file (with --example) |
| `--llm-cities` | Enable LLM-based city estimation and geolocation |

## Site Location Priority

The script determines site locations using the following priority:

1. **Configured city name** from site configuration
2. **LLM-estimated city** (if --llm-cities enabled and no configured city)
3. **LLM coordinates** for cities not in database (if --llm-cities enabled)
4. **Tunnel endpoint coordinates** (for connected sites)
5. **Country center** (for disconnected sites without city data)

## Troubleshooting

If you encounter errors:
1. Verify your API credentials are correct
2. Ensure all required CSV files are present
3. Check that you have network connectivity to the Cato API
4. Make sure all Python dependencies are installed
5. For LLM features, ensure your Anthropic API key is configured
6. If LLM requests fail, the script continues with fallback methods