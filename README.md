# Geospatial API Integration Challenge

## Overview

This project analyzes fire incident data from a public Fire Incidents **ArcGIS API**, extracts useful information and compares the data with fire detections from **OroraTech's WFS system**.  The script performs:

-   **Fetching Fire Data**: Retrieves fire incident data for a specified time frame and location.
    
-   **Processing GeoJSON Data**: Extracts relevant fire details.
    
-   **Data Analysis**: Computes discovery hour statistics, fire size distributions, and correlations.
    
-   **Comparison with WFS**: Checks if WFS detected fires earlier than official sources.
    
-   **Visualization**: Generates histograms and scatter plots for insights.
    

## Setup Instructions

### Running the Script

```
python lamprinidis_api_challenge.py --bpoly_file bounding_polygon.json --wfs wfs.geojson
```

-   `--bpoly_file` : Path to the **bounding polygon file** (Esri JSON format). Default value is "bounding_polygon.json"
    
-   `--wfs` : Path to the **OroraTech WFS GeoJSON file**. Default value is "wfs.geojson"
    

## Project Structure

```
.
├── lamrpinidis_api_challenge.py # Main script for data fetching, processing, and analysis
├── bounding_polygon.json        # JSON file specifying the region of interest (Esri JSON format)
├── wfs.geojson                  # OroraTech WFS dataset containing detected fire incidents
└──  README.md                    # Project documentation
```

## Key Functions

### 1. Fetching Fire Data

-   **fetch_fire_data(polygon)**: Queries public ArcGIS API for fire incidents within a user defined bounding polygon.
    
-   Uses **GeoJSON format** and retrieves fires **>= 1 acre** detected between **June 1, 2024 – Sept 30, 2024**.
    

### 2. Parsing Data

-   **parse_fire_data(geojson_data)**: Extracts coordinates, fire discovery time, and size for the public data.
    
-   **parse_wfs_data(geojson_data)**: Extracts coordinates and fire discovery time for the WFS data. Handles both **Polygon and MultiPolygon** geometries using **Shapely**.
    

### 3. Analysis & Comparison

-   **analyze_data(fire_records)**: Determines the most common discovery hour, number of incidents larger than 1000 acres and calculates correlations for the public data.
    
-    **compare_detection_times(public_records, wfs_records)**: Checks if WFS detected fires earlier than public reports.
    

### 4. Visualization

-   **visualize_data(analysis_results)**: Generates:
    
    -   Histogram of fire discovery times.
        
    -   Histogram of incident sizes.
        
    -   Scatter plot of **discovery hour vs. fire size**.