import requests
import json
from datetime import datetime, timezone
import matplotlib.pyplot as plt
import pandas as pd
import argparse
from shapely.geometry import Point, shape

# ---------------------------
# Fetch Public Fire Incident Data from API
# ---------------------------
def fetch_fire_data(polygon):
    """
    Fetches public fire incident data from the ArcGIS REST API.
    Filters include:
      - A polygon bounding box covering the desired area
      - The fire detection timeframe: June 1 2024 to September 30 2024
      - Incidents with a size >= 1 acre
    """
    url = "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/WFIGS_Incident_Locations/FeatureServer/0/query"

    # Convert the polygon dictionary to a JSON string
    polygon_str = json.dumps(polygon)
    
    # Set up parameters for the API call.
    params = {
        "f": "geojson",  
        "geometry": polygon_str, 
        "geometryType": "esriGeometryPolygon", # Interpret polygon_str as a bounding polygon
        "where": "IncidentSize >= 1 AND FireDiscoveryDateTime >= timestamp '2024-06-01 00:00:00' AND FireDiscoveryDateTime <= timestamp '2024-09-30 23:59:59'",
        "outFields": "*" 
    }
    
    try:
        print("Fetching public fire incident data from API...")
        response = requests.get(url, params=params)
        response.raise_for_status() # Catch HTTP errors
        geojson_data = response.json()

        # Noticed that if the query is wrong, response.status_code will be 200 but geojson_data will contain a 400 error
        if "error" in geojson_data:
            raise ValueError(f"API error: {geojson_data['error']['message']}")

        print(f"Public data fetched successfully. Retrieved {len(geojson_data["features"])} records.")
        return geojson_data
    except requests.RequestException as e:
        print("Error fetching public data:", e)
        return None
    except ValueError as ve:
        print("Error in API response:", ve)
        return None

# ---------------------------
# Parse the Public Fire Incident Data
# ---------------------------
def parse_fire_data(geojson_data):
    """
    Parses the public fire incident GeoJSON data.
    For each feature, the following fields are extracted:
      - Coordinates (from "geometry")
      - Official discovery time ("FireDiscoveryDateTime" in Unix epoch milliseconds)
      - Incident size ("IncidentSize")
    """
    fire_records = []
    
    if not geojson_data or "features" not in geojson_data:
        print("No valid public fire data to parse.")
        return fire_records

    for feature in geojson_data["features"]:
        try:
            # Get coordinates 
            coords = feature["geometry"]["coordinates"]
            properties = feature["properties"]

            # Convert the Unix timestamp (milliseconds) to a datetime object
            # Include UTC timezone to compare with WFS records (can't compare offset naive to offset aware)
            discovery_ts = properties.get("FireDiscoveryDateTime")
            if discovery_ts is None:
                continue
            detection_time = datetime.fromtimestamp(discovery_ts / 1000, tz=timezone.utc)

            # Get the incident size (in acres)
            incident_size = properties.get("IncidentSize")
            if incident_size is None:
                continue

            fire_records.append({
                "coordinates": tuple(coords),
                "detection_time": detection_time,
                "incident_size": float(incident_size)
            })
        except Exception as e:
            print("Error parsing a public record:", e)
            continue

    print(f"Parsed {len(fire_records)} public fire records.")
    return fire_records

# ---------------------------
# Parse the OroraTech WFS Data
# ---------------------------
def parse_wfs_data(geojson_data):
    """
    Parses the OroraTech WFS GeoJSON data.
    For each feature, it extracts:
      - The (multi)polygon geometry with a shapely shape
      - Earliest detection time
    """
    wfs_records = []
    
    if not geojson_data or "features" not in geojson_data:
        print("No valid WFS data to parse.")
        return wfs_records

    for feature in geojson_data["features"]:
        try:
            geometry = feature["geometry"]
            properties = feature["properties"]

            # Get the (multi)polygon with a shapely shape
            # Handles both polygon and multipolgon cases
            poly = shape(geometry)
            
            # Parse the detection time (ISO 8601 format).
            # Convert to UTC for ease of "visual" comparison
            detection_str = properties.get("oldest_detection")
            if detection_str is None:
                continue
            detection_time = datetime.fromisoformat(detection_str).astimezone(timezone.utc)

            wfs_records.append({
                "polygon": poly,  # shapely shape
                "detection_time": detection_time
            })
        except Exception as e:
            print("Error parsing a WFS record:", e)
            continue

    print(f"Parsed {len(wfs_records)} WFS records.")
    return wfs_records

# ---------------------------
# Analyze the Public Fire Data
# ---------------------------
def analyze_data(fire_records):
    """
    Analyzes public fire records:
      - Extracts the hour (0-23) from the official discovery time.
      - BUilds a DataFrame to analyze the distribution of discovery hours and incident sizes.
      - Finds the hour (UTC) that most fires occur at
      - Finds the number of fires larger than 1000 acres 
      - Computes the correlation between discovery hour and incident size.
    """
    hours = [record["detection_time"].hour for record in fire_records]
    sizes = [record["incident_size"] for record in fire_records]

    df = pd.DataFrame({
        "hour": hours,
        "size": sizes
    })

    # Determine the hour (UTC) when most fires occur
    if not df.empty:
        most_common_hour = df["hour"].value_counts().idxmax()  
        print(f"Most fires occur at UTC hour: {most_common_hour}")
    else:
        most_common_hour = None
        print("No data available to determine the most common hour.")

    # Determine number of fires larger then 1000 acres
    large_fire_count = (df["size"] > 1000).sum()
    print(f"Number of fires larger than 1000 acres: {large_fire_count}")

    # Determine correlation
    if len(df) > 1:
        correlation = df["hour"].corr(df["size"])
        print(f"Correlation between discovery hour and incident size: {correlation:.3f}")
    else:
        correlation = None
        print("Not enough data to compute correlation.")

    return {
        "dataframe": df,
        "most_common_hour": most_common_hour,
        "large_fire_count": large_fire_count,
        "correlation": correlation
    }

# ---------------------------
# Visualize the Public Fire Data
# ---------------------------
def visualize_data(analysis_results):
    """
    Creates visualizations based on the analysis:
      - Histogram of fire discovery hours.
      - Histogram of incident sizes.
      - Scatter plot of discovery hour vs. incident size with correlation annotation.
    """
    df = analysis_results["dataframe"]
    hours = df["hour"]
    sizes = df["size"]

    fig, axs = plt.subplots(1, 3, figsize=(18, 5))

    # Histogram of discovery hours
    axs[0].hist(hours, bins=range(0, 25), edgecolor="black", align="mid")
    axs[0].set_title("Distribution of Fire Discovery Hours")
    axs[0].set_xlabel("Hour of Day")
    axs[0].set_ylabel("Number of Fires")
    axs[0].set_xticks(range(0, 25))

    # Histogram of incident sizes
    axs[1].hist(sizes, bins=20, edgecolor="black")
    axs[1].set_title("Distribution of Incident Sizes")
    axs[1].set_xlabel("Incident Size (acres)")
    axs[1].set_ylabel("Number of Fires")

    # Scatter plot: Discovery Hour vs. Incident Size
    axs[2].scatter(hours, sizes, alpha=0.7)
    axs[2].set_title("Discovery Hour vs. Incident Size")
    axs[2].set_xlabel("Discovery Hour")
    axs[2].set_ylabel("Incident Size (acres)")
    if analysis_results["correlation"] is not None:
        axs[2].text(0.05, 0.95, f"Correlation: {analysis_results['correlation']:.3f}",
                    transform=axs[2].transAxes, fontsize=12,
                    verticalalignment="top", bbox=dict(boxstyle="round", facecolor="bisque", alpha=0.5))

    plt.tight_layout()
    plt.show()

# ---------------------------
# Compare Detection Times
# ---------------------------
def compare_detection_times(public_records, wfs_records):
    """
    For each public fire record (point), checks if it lies within any WFS (multi)polygon.
    If so, compares the official discovery time with the WFS detection time.
    If the WFS detection time is earlier, the fire is considered first detected by WFS.
    """
    # Create a dictionary for quick lookup of WFS records by unique_id
    early_detected = []

    for record in public_records:
        # Convert the public fire's coordinates to a shapely Point.
        fire_point = Point(record["coordinates"])
        official_time = record["detection_time"]
        
        # Check if the point is contained in any WFS (multi)polygon.
        for wfs in wfs_records:
            poly = wfs["polygon"]
            wfs_detection_time = wfs["detection_time"]
            if poly.contains(fire_point) and wfs_detection_time < official_time:
                early_detected.append({
                    "coordinates": record["coordinates"],
                    "wfs_detection_time": wfs_detection_time,
                    "official_time": official_time,
                    "incident_size": record["incident_size"]
                })
                break  # Found a polygon that contains the point.

    print(f"Found {len(early_detected)} fires first detected by WFS.")
    return early_detected

# ---------------------------
# Main Execution Flow
# ---------------------------
def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Fetch and analyze fire incident data for a specified region.")
    parser.add_argument('--bpoly_file', type=str, default="bounding_polygon.json",
                        help="Path to the file containing the polygon geometry in JSON format.")
    parser.add_argument('--wfs', type=str, default="wfs.geojson", 
                        help="Path to the OroraTech WFS GeoJSON file")
    args = parser.parse_args()

    # Read bouding polygon from file
    try:
        with open(args.bpoly_file, 'r') as f:
            polygon = json.load(f)
    except Exception as e:
        print("Error reading the polygon file:", e)
        exit(1)

    if "rings" not in polygon:
        print("The polygon file does not appear to have a 'rings' key. Check the file format.")
        exit(2)

    # Fetch public fire incident data from the API
    public_geojson = fetch_fire_data(polygon)
    
    if public_geojson is None:
        print("Failed to retrieve public fire data.")
        exit(0)

    # Parse the fetched public data
    public_records = parse_fire_data(public_geojson)
    
    # Analyze and visualize the public data
    if public_records:
        analysis_results = analyze_data(public_records)
        visualize_data(analysis_results)
    else:
        print("No valid public fire records found.")

    # Compare with OroraTech WFS data
    try:
        with open(args.wfs, 'r') as f:
            wfs_geojson = json.load(f)
    except Exception as e:
        print("Error loading WFS data file:", e)
        wfs_geojson = None

    print(len(wfs_geojson["features"]))

    if wfs_geojson:
        wfs_records = parse_wfs_data(wfs_geojson)
        if public_records and wfs_records:
            early_detected = compare_detection_times(public_records, wfs_records)
            if early_detected:
                print("\nFires first detected by WFS (detection time is earlier than official discovery time):")
                for fire in early_detected:
                    print(f"- Fire at {fire['coordinates']} with official discovery at {fire['official_time']} was detected by WFS at {fire['wfs_detection_time']}")
                    print(f"  Incident size was {fire["incident_size"]} acres.")
            else:
                print("No fires were detected earlier by the WFS system.")
        else:
            print("Insufficient data to perform WFS intersection.")
    else:
        print("No WFS data available.")

if __name__ == '__main__':
    main()