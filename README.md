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

1. Start the application:
```bash
python cato-site-map.py
```

2. The map will automatically load when the application starts
3. Open your browser to the URL shown in the terminal (typically http://127.0.0.1:7860)

## Features

- **Interactive Map**: View all your Cato sites and POP locations on a world map
- **Color Coding**: 
  - Blue dots: Connected sites
  - Red dots: Disconnected sites
  - Green dots: POP locations
- **Toggle Visibility**: Use the checkboxes to show/hide different types of locations
- **Hover Information**: Hover over any dot to see the site/POP name

## Required Files

The following CSV files must be present in the project directory:
- `cclatlong.csv` - Country geolocation data
- `worldcities.csv` - City geolocation data
- `cato.py` - Cato API helper module

## Troubleshooting

If you encounter errors:
1. Verify your API credentials are correct
2. Ensure all required CSV files are present
3. Check that you have network connectivity to the Cato API
4. Make sure all Python dependencies are installed