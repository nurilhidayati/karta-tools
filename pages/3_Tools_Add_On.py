# Geohash Converter
import streamlit as st
import pandas as pd
import geohash2
from shapely.geometry import Polygon, box, shape
import geopandas as gpd
from io import StringIO
import tempfile
import zipfile
import os
import json
import requests
import folium
from streamlit_folium import st_folium

# API Configuration
API_BASE_URL = "http://localhost:8000/api/v1"

# CSS for styling
st.markdown("""
    <style>
    /* Main app background */
    .stApp {
        background-color: #F3F6FB;
    }
    
    /* Navbar/header */
    .css-1rs6os, .css-17ziqus, header[data-testid="stHeader"] {
        background-color: #F3F6FB !important;
    }
    
    /* Sidebar */
    .css-1d391kg, .css-1lcbmhc, section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
    }
    
    /* Text color */
    .stApp, .stApp p, .stApp div, .stApp span, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        color: #000000 !important;
    }
    
    /* File uploader comprehensive styling */
    .stFileUploader {
        background-color: #FFFFFF !important;
    }
    
    .stFileUploader > div {
        background-color: #FFFFFF !important;
    }
    
    .stFileUploader > div > div {
        background-color: #FFFFFF !important;
    }
    
    .stFileUploader > div > div > div {
        background-color: #FFFFFF !important;
    }
    
    .stFileUploader > div > div > div > div {
        background-color: #FFFFFF !important;
    }
    
    /* File uploader drag and drop zone */
    div[data-testid="stFileUploader"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    div[data-testid="stFileUploader"] > div {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    div[data-testid="stFileUploader"] > div > div {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    div[data-testid="stFileUploader"] > div > div > div {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* File uploader section */
    section[data-testid="stFileUploader"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Upload area specific CSS classes */
    .css-1cpxqw2, .css-1erivf3, .css-1v0mbdj, .css-1kyxreq, .css-1d391kg {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Additional file uploader selectors */
    [data-testid="stFileUploader"] [data-testid="stMarkdownContainer"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* File uploader text styling */
    [data-testid="stFileUploader"] p, [data-testid="stFileUploader"] span, [data-testid="stFileUploader"] div {
        color: #000000 !important;
    }
    
    /* Drag and drop area */
    .uploadedFile {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* File drop zone */
    .css-1adrfps {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Additional comprehensive upload area styling */
    .stFileUploader div[role="button"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    .stFileUploader label {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Force all file uploader backgrounds to match sidebar */
    div[data-testid="stFileUploader"] * {
        background-color: #FFFFFF !important;
    }
    
    /* Ensure text is black in upload areas */
    div[data-testid="stFileUploader"] *:not(button) {
        color: #000000 !important;
    }
    
    /* Upload drag area specific styling */
    .css-1cpxqw2 > div, .css-1erivf3 > div {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Upload button styling */
    .stFileUploader button {
        background-color: #085A3E !important;
        color: white !important;
        border: none !important;
    }
    
    .stFileUploader button:hover {
        background-color: #0a6b47 !important;
        color: white !important;
    }
    
    /* Browse files button */
    div[data-testid="stFileUploader"] button {
        background-color: #085A3E !important;
        color: white !important;
        border: none !important;
    }
    
    div[data-testid="stFileUploader"] button:hover {
        background-color: #0a6b47 !important;
        color: white !important;
    }
    
    /* Selectbox styling */
    .stSelectbox > div > div {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    .stSelectbox > div > div > div {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Selectbox dropdown */
    .stSelectbox select {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Selectbox options */
    .stSelectbox option {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Selectbox input field */
    div[data-testid="stSelectbox"] > div {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    div[data-testid="stSelectbox"] > div > div {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Selectbox dropdown container */
    div[data-testid="stSelectbox"] ul {
        background-color: #FFFFFF !important;
    }
    
    div[data-testid="stSelectbox"] li {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Additional dropdown styling */
    .stSelectbox [data-baseweb="popover"] {
        background-color: #FFFFFF !important;
    }
    
    .stSelectbox [data-baseweb="menu"] {
        background-color: #FFFFFF !important;
    }
    
    .stSelectbox [role="listbox"] {
        background-color: #FFFFFF !important;
    }
    
    .stSelectbox [role="option"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Force dropdown menu background */
    div[data-testid="stSelectbox"] [data-baseweb="select"] > div > div:last-child {
        background-color: #FFFFFF !important;
    }
    
    /* Dropdown menu items */
    div[data-testid="stSelectbox"] [data-baseweb="select"] [role="option"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Hover effect for dropdown items */
    div[data-testid="stSelectbox"] [role="option"]:hover {
        background-color: #F0F0F0 !important;
        color: #000000 !important;
    }
    
    /* Aggressive dropdown styling - target all possible elements */
    div[data-testid="stSelectbox"] * {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Override any dark styling */
    .stSelectbox *, [data-testid="stSelectbox"] * {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Target BaseWeb components directly */
    [data-baseweb="select"] {
        background-color: #FFFFFF !important;
    }
    
    [data-baseweb="select"] * {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Force all dropdown related elements */
    .css-1cpxqw2 select, .css-1erivf3 select {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Override any inherited dark theme */
    .stSelectbox, .stSelectbox * {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* FORCE ALL DROPDOWNS TO BE WHITE - NUCLEAR OPTION */
    select, select * {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        background: #FFFFFF !important;
    }
    
    /* Force all dropdown menus */
    [role="listbox"], [role="listbox"] * {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        background: #FFFFFF !important;
    }
    
    [role="menu"], [role="menu"] * {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        background: #FFFFFF !important;
    }
    
    [role="option"], [role="option"] * {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        background: #FFFFFF !important;
    }
    
    /* Force all popover/overlay elements */
    [data-baseweb="popover"], [data-baseweb="popover"] * {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        background: #FFFFFF !important;
    }
    
    [data-baseweb="menu"], [data-baseweb="menu"] * {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        background: #FFFFFF !important;
    }
    
    /* Force all BaseWeb select components */
    [data-baseweb="select"], [data-baseweb="select"] * {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        background: #FFFFFF !important;
    }
    
    /* Override any CSS classes that might create dark dropdowns */
    div[class*="select"], div[class*="dropdown"], div[class*="menu"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        background: #FFFFFF !important;
    }
    
    div[class*="select"] *, div[class*="dropdown"] *, div[class*="menu"] * {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        background: #FFFFFF !important;
    }
    
    /* Force any element with dark background in dropdown context */
    .stApp [style*="background-color: rgb(38, 39, 48)"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    .stApp [style*="background: rgb(38, 39, 48)"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Primary button styling */
    .stButton > button[kind="primary"] {
        background-color: #085A3E !important;
        color: white !important;
        border: none !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #0a6b47 !important;
        color: white !important;
    }
    
    /* Alternative button targeting */
    button[data-testid="baseButton-primary"] {
        background-color: #085A3E !important;
        color: white !important;
        border: none !important;
    }
    
    button[data-testid="baseButton-primary"]:hover {
        background-color: #0a6b47 !important;
        color: white !important;
    }
    
    /* Force all primary buttons */
    .stApp button[kind="primary"] {
        background-color: #085A3E !important;
        color: white !important;
        border: none !important;
    }
    
    .stApp button[kind="primary"]:hover {
        background-color: #0a6b47 !important;
        color: white !important;
    }
    
    /* Force button text to be white */
    .stButton > button[kind="primary"] * {
        color: white !important;
    }
    
    button[data-testid="baseButton-primary"] * {
        color: white !important;
    }
    
    .stApp button[kind="primary"] * {
        color: white !important;
    }
    
    /* Additional button text styling */
    .stButton button[kind="primary"] span {
        color: white !important;
    }
    
    .stButton button[kind="primary"] div {
        color: white !important;
    }
    
    .stButton button[kind="primary"] p {
        color: white !important;
    }
    
    /* Map container optimization - Force white background */
    .streamlit-folium {
        width: 100% !important;
        background-color: #FFFFFF !important;
    }
    
    /* Map iframe styling - Remove black background */
    iframe[title="streamlit_folium.st_folium"] {
        width: 100% !important;
        height: 500px !important;
        border-radius: 8px !important;
        border: 1px solid #E0E0E0 !important;
        background-color: #FFFFFF !important;
    }
    
    /* Force map container backgrounds to white */
    div[data-testid="stIFrame"] {
        background-color: #FFFFFF !important;
    }
    
    /* Remove any black backgrounds from map containers */
    .stApp iframe,
    .stApp iframe body,
    .stApp .leaflet-container {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
    }
    
    /* Force all map related elements to white background */
    .leaflet-container {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
        width: 100% !important;
        min-height: 500px !important;
    }
    
    .leaflet-tile-pane,
    .leaflet-map-pane {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
    }
    
    /* Remove any dark backgrounds from folium map */
    .folium-map {
        background-color: #FFFFFF !important;
        width: 100% !important;
    }
    
    /* CRITICAL: Fix black space below map */
    /* Force iframe height to match content exactly */
    iframe[title="streamlit_folium.st_folium"] {
        height: 500px !important;
        max-height: 500px !important;
        min-height: 500px !important;
        overflow: hidden !important;
        background-color: #FFFFFF !important;
    }
    
    /* Remove any extra space below iframe */
    div[data-testid="stIFrame"] {
        height: auto !important;
        max-height: 520px !important;
        overflow: hidden !important;
        background-color: #FFFFFF !important;
    }
    
    /* Force container to not expand beyond content */
    .streamlit-folium {
        height: auto !important;
        max-height: 520px !important;
        overflow: hidden !important;
        background-color: #FFFFFF !important;
    }
    
    /* Remove margin/padding that might cause black space */
    .stApp iframe[title="streamlit_folium.st_folium"] {
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
        background-color: #FFFFFF !important;
    }
    
    /* Target any black backgrounds specifically */
    .stApp [style*="background: black"],
    .stApp [style*="background-color: black"], 
    .stApp [style*="background: #000"],
    .stApp [style*="background-color: #000000"] {
        background: #FFFFFF !important;
        background-color: #FFFFFF !important;
    }
    
    /* Download button styling - GREEN THEME */
    .stDownloadButton > button {
        background-color: #085A3E !important;
        color: #FFFFFF !important;
        border: 1px solid #085A3E !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
    }
    
    .stDownloadButton > button:hover {
        background-color: #064229 !important;
        color: #FFFFFF !important;
        border: 1px solid #064229 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(8, 90, 62, 0.3) !important;
    }
    
    .stDownloadButton > button:active {
        background-color: #053822 !important;
        border: 1px solid #053822 !important;
    }
    
    /* Force download button text to be white */
    .stDownloadButton > button * {
        color: #FFFFFF !important;
    }
    
    .stDownloadButton > button span {
        color: #FFFFFF !important;
    }
    
    .stDownloadButton > button div {
        color: #FFFFFF !important;
    }
    
    .stDownloadButton > button p {
        color: #FFFFFF !important;
    }
    
    /* Alternative download button selectors */
    button[data-testid="baseButton-secondary"] {
        background-color: #085A3E !important;
        color: #FFFFFF !important;
        border: 1px solid #085A3E !important;
        font-weight: 600 !important;
    }
    
    button[data-testid="baseButton-secondary"]:hover {
        background-color: #064229 !important;
        color: #FFFFFF !important;
        border: 1px solid #064229 !important;
    }
    
    button[data-testid="baseButton-secondary"] * {
        color: #FFFFFF !important;
    }
    
    /* Force all download-related buttons */
    .stApp button[kind="secondary"] {
        background-color: #085A3E !important;
        color: #FFFFFF !important;
        border: 1px solid #085A3E !important;
    }
    
    .stApp button[kind="secondary"]:hover {
        background-color: #064229 !important;
        color: #FFFFFF !important;
    }
    
    .stApp button[kind="secondary"] * {
        color: #FFFFFF !important;
    }
    
    /* Close/X button styling - GREEN BACKGROUND */
    /* File uploader close button */
    .stFileUploader button[title="Remove file"] {
        background-color: #085A3E !important;
        color: #FFFFFF !important;
        border: 1px solid #085A3E !important;
        border-radius: 50% !important;
        width: 24px !important;
        height: 24px !important;
    }
    
    .stFileUploader button[title="Remove file"]:hover {
        background-color: #064229 !important;
        color: #FFFFFF !important;
        border: 1px solid #064229 !important;
    }
    
    /* Close button in file uploader */
    div[data-testid="stFileUploader"] button[kind="tertiary"] {
        background-color: #085A3E !important;
        color: #FFFFFF !important;
        border: 1px solid #085A3E !important;
        border-radius: 50% !important;
    }
    
    div[data-testid="stFileUploader"] button[kind="tertiary"]:hover {
        background-color: #064229 !important;
        color: #FFFFFF !important;
    }
    
    /* Generic close/X button styling */
    button[aria-label="Close"] {
        background-color: #085A3E !important;
        color: #FFFFFF !important;
        border: 1px solid #085A3E !important;
        border-radius: 50% !important;
    }
    
    button[aria-label="Close"]:hover {
        background-color: #064229 !important;
        color: #FFFFFF !important;
    }
    
    /* Alternative close button selectors */
    button[data-testid="baseButton-tertiary"] {
        background-color: #085A3E !important;
        color: #FFFFFF !important;
        border: 1px solid #085A3E !important;
    }
    
    button[data-testid="baseButton-tertiary"]:hover {
        background-color: #064229 !important;
        color: #FFFFFF !important;
    }
    
    /* Force all tertiary buttons (typically close buttons) */
    .stApp button[kind="tertiary"] {
        background-color: #085A3E !important;
        color: #FFFFFF !important;
        border: 1px solid #085A3E !important;
    }
    
    .stApp button[kind="tertiary"]:hover {
        background-color: #064229 !important;
        color: #FFFFFF !important;
    }
    
    /* X symbol styling */
    .stApp button[kind="tertiary"] * {
        color: #FFFFFF !important;
    }
    
    button[data-testid="baseButton-tertiary"] * {
        color: #FFFFFF !important;
    }
    
    /* File uploader X button text/icon */
    .stFileUploader button * {
        color: #FFFFFF !important;
    }
    
    /* Ensure X or close icons are white */
    button[title="Remove file"] * {
        color: #FFFFFF !important;
    }
    
    button[aria-label="Close"] * {
        color: #FFFFFF !important;
    }
    
    /* Override any specific X or close icon styling */
    .stApp [data-testid*="close"] {
        background-color: #085A3E !important;
        color: #FFFFFF !important;
    }
    
    .stApp [title*="close" i], 
    .stApp [title*="remove" i],
    .stApp [title*="delete" i] {
        background-color: #085A3E !important;
        color: #FFFFFF !important;
        border: 1px solid #085A3E !important;
    }
    
    .stApp [title*="close" i]:hover, 
    .stApp [title*="remove" i]:hover,
    .stApp [title*="delete" i]:hover {
        background-color: #064229 !important;
        color: #FFFFFF !important;
    }
    </style>
""", unsafe_allow_html=True)

# Convert geohash to polygon
def geohash_to_polygon(gh):
    lat, lon, lat_err, lon_err = geohash2.decode_exactly(gh)
    lat_min, lat_max = lat - lat_err, lat + lat_err
    lon_min, lon_max = lon - lon_err, lon + lon_err
    return Polygon([
        (lon_min, lat_min),
        (lon_min, lat_max),
        (lon_max, lat_max),
        (lon_max, lat_min),
        (lon_min, lat_min)
    ])

# Local Helper Functions for Boundary to GeoHash conversion
def convert_boundary_to_geohash(boundary_geojson, precision_level):
    """Convert boundary to geohash with specified precision level (local implementation)"""
    try:
        # Prepare the geometry - extract first feature's geometry if it's a FeatureCollection
        if boundary_geojson.get("type") == "FeatureCollection" and boundary_geojson.get("features"):
            geometry_data = boundary_geojson["features"][0]["geometry"]
        elif boundary_geojson.get("type") == "Feature":
            geometry_data = boundary_geojson["geometry"]
        else:
            geometry_data = boundary_geojson
        
        # Convert to shapely geometry
        boundary_geom = shape(geometry_data)
        
        # Get bounding box
        minx, miny, maxx, maxy = boundary_geom.bounds
        
        # Generate geohash grid
        # Use set to track unique geohashes and avoid duplicates
        unique_geohashes = set()
        geohash_features = []
        
        # Calculate step size based on precision (more conservative to ensure coverage)
        lat_step = 0.008 if precision_level == 5 else 0.003 if precision_level == 6 else 0.001
        lon_step = 0.008 if precision_level == 5 else 0.003 if precision_level == 6 else 0.001
        
        # Generate grid points
        current_lat = miny
        while current_lat <= maxy:
            current_lon = minx
            while current_lon <= maxx:
                # Create point and get geohash
                point_geohash = geohash2.encode(current_lat, current_lon, precision_level)
                
                # Skip if this geohash already processed
                if point_geohash in unique_geohashes:
                    current_lon += lon_step
                    continue
                
                # Decode back to get the geohash polygon bounds
                decoded_lat, decoded_lon, lat_err, lon_err = geohash2.decode_exactly(point_geohash)
                
                # Create geohash bounding box
                geohash_box = box(
                    decoded_lon - lon_err, decoded_lat - lat_err,
                    decoded_lon + lon_err, decoded_lat + lat_err
                )
                
                # Check if geohash intersects with boundary
                if boundary_geom.intersects(geohash_box):
                    # Add to unique set
                    unique_geohashes.add(point_geohash)
                    
                    # Calculate center point
                    center_lat = decoded_lat
                    center_lon = decoded_lon
                    
                    geohash_features.append({
                        "type": "Feature",
                        "properties": {
                            "geoHash": point_geohash,
                            "center_lat": center_lat,
                            "center_lon": center_lon
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [decoded_lon - lon_err, decoded_lat - lat_err],
                                [decoded_lon + lon_err, decoded_lat - lat_err],
                                [decoded_lon + lon_err, decoded_lat + lat_err],
                                [decoded_lon - lon_err, decoded_lat + lat_err],
                                [decoded_lon - lon_err, decoded_lat - lat_err]
                            ]]
                        }
                    })
                
                current_lon += lon_step
            current_lat += lat_step
        
        # Create GeoJSON FeatureCollection
        result = {
            "type": "FeatureCollection",
            "features": geohash_features
        }
        
        return {
            "success": True,
            "geohash_count": len(unique_geohashes),
            "precision": precision_level,
            "geohashes_geojson": result
        }
        
    except Exception as e:
        st.error(f"Error converting to geohash: {str(e)}")
        return None

def geohash_result_to_csv(geohash_result):
    """Convert geohash result to CSV format (local implementation)"""
    try:
        if not geohash_result or not geohash_result.get("geohashes_geojson"):
            return ""
        
        geohashes_geojson = geohash_result["geohashes_geojson"]
        
        if not geohashes_geojson or not geohashes_geojson.get("features"):
            return ""
        
        rows = []
        for feature in geohashes_geojson["features"]:
            props = feature.get("properties", {})
            rows.append({
                "geohash": props.get("geoHash", ""),
                "lat": props.get("center_lat", ""),
                "lon": props.get("center_lon", "")
            })
        
        if rows:
            df = pd.DataFrame(rows)
            return df.to_csv(index=False)
        else:
            return ""
            
    except Exception as e:
        st.error(f"Error converting to CSV: {str(e)}")
        return ""

def get_bounds_from_geojson(geojson):
    """Calculate bounds from GeoJSON for map fitting (local implementation)"""
    try:
        if not geojson:
            return None
        
        # Handle different GeoJSON types
        if geojson.get('type') == 'FeatureCollection' and geojson.get('features'):
            features = geojson['features']
        elif geojson.get('type') == 'Feature':
            features = [geojson]
        else:
            # Assume it's a geometry object
            features = [{"type": "Feature", "geometry": geojson, "properties": {}}]
        
        if not features:
            return None
        
        # Initialize bounds with first feature
        min_lon = float('inf')
        min_lat = float('inf')
        max_lon = float('-inf')
        max_lat = float('-inf')
        
        # Calculate bounds from all features
        for feature in features:
            geometry = feature.get('geometry')
            if not geometry:
                continue
            
            # Use shapely to get bounds
            geom = shape(geometry)
            bounds = geom.bounds  # (minx, miny, maxx, maxy)
            
            min_lon = min(min_lon, bounds[0])
            min_lat = min(min_lat, bounds[1])
            max_lon = max(max_lon, bounds[2])
            max_lat = max(max_lat, bounds[3])
        
        # Check if we found valid bounds
        if min_lon == float('inf') or min_lat == float('inf'):
            return None
        
        # Return bounds in the format expected by the map
        # [[min_lat, min_lon], [max_lat, max_lon]]
        return [[min_lat, min_lon], [max_lat, max_lon]]
        
    except Exception as e:
        st.error(f"Error calculating bounds: {str(e)}")
        return None

def create_map_with_boundary_and_geohash(boundary_geojson=None, geohash_geojson=None):
    """Create folium map with boundary and geohash data"""
    # Create base map with white background
    m = folium.Map(
        location=[-2.5, 117.5], 
        zoom_start=5,
        tiles='OpenStreetMap',
        prefer_canvas=True,
        zoom_control=True,
        scrollWheelZoom=True
    )
    
    # Add custom CSS to force white background
    map_css = """
    <style>
    .leaflet-container {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
    }
    .leaflet-tile-pane {
        background-color: #FFFFFF !important;
    }
    .leaflet-map-pane {
        background-color: #FFFFFF !important;
    }
    </style>
    """
    m.get_root().html.add_child(folium.Element(map_css))
    
    # Add boundary layer if available
    if boundary_geojson:
        bounds = get_bounds_from_geojson(boundary_geojson)
        if bounds:
            # Add padding to bounds for better view
            padding = 0.01  # Adjust this value as needed
            padded_bounds = [
                [bounds[0][0] - padding, bounds[0][1] - padding],
                [bounds[1][0] + padding, bounds[1][1] + padding]
            ]
            m.fit_bounds(padded_bounds, padding=[20, 20])
        
        folium.GeoJson(
            boundary_geojson,
            name="Boundary",
            style_function=lambda x: {
                "color": "#3388ff", 
                "weight": 2, 
                "fillOpacity": 0.1,
                "fillColor": "#3388ff"
            }
        ).add_to(m)
    
    # Add geohash layer if available
    if geohash_geojson:
        folium.GeoJson(
            geohash_geojson,
            name="GeoHash",
            style_function=lambda x: {
                "color": "#ff6b35", 
                "weight": 1, 
                "fillOpacity": 0.3,
                "fillColor": "#ff6b35"
            }
        ).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    return m

# ============================================================================
# BOUNDARY TO GEOHASH CONVERTER SECTION
# ============================================================================

# Navigation header
st.markdown("<h1 style='text-align: center; color: #000000;'>Tools Add-On</h1>", unsafe_allow_html=True)


st.markdown("---")
st.title("Area to Geohash Converter")
st.markdown("Upload a area file (GeoJSON, KML, SHP) and convert it to GeoHash with selectable precision levels.")

# Initialize session state for boundary to geohash conversion
if 'uploaded_boundary' not in st.session_state:
    st.session_state.uploaded_boundary = None
if 'boundary_geojson' not in st.session_state:
    st.session_state.boundary_geojson = None
if 'generated_geohash' not in st.session_state:
    st.session_state.generated_geohash = None
if 'precision_level' not in st.session_state:
    st.session_state.precision_level = 6

# No API needed - all functions work locally
api_available = True

# File upload section
uploaded_boundary_file = st.file_uploader(
    "📁 Upload Area File", 
    type=["geojson"],
    help="Upload a area file in GeoJSON format"
)

if uploaded_boundary_file:
    try:
        # Process uploaded file
        file_extension = uploaded_boundary_file.name.split('.')[-1].lower()
        
        if file_extension in ['geojson', 'json']:
            # Read GeoJSON directly
            geojson_data = json.loads(uploaded_boundary_file.read().decode('utf-8'))
            st.session_state.boundary_geojson = geojson_data
            
        elif file_extension in ['kml', 'kmz']:
            # Read KML/KMZ using geopandas
            gdf = gpd.read_file(uploaded_boundary_file)
            # Convert to GeoJSON
            geojson_str = gdf.to_json()
            st.session_state.boundary_geojson = json.loads(geojson_str)
            
        elif file_extension in ['shp', 'zip']:
            # Read Shapefile
            gdf = gpd.read_file(uploaded_boundary_file)
            # Convert to GeoJSON
            geojson_str = gdf.to_json()
            st.session_state.boundary_geojson = json.loads(geojson_str)
        
        st.success(f"✅ Successfully loaded boundary file: {uploaded_boundary_file.name}")
        st.session_state.uploaded_boundary = uploaded_boundary_file.name
        
    except Exception as e:
        st.error(f"❌ Error reading boundary file: {str(e)}")
        st.session_state.boundary_geojson = None

# Precision level selection
if st.session_state.boundary_geojson:
    st.subheader("⚙️ Conversion Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        precision_level = st.selectbox(
            "🎯 Select GeoHash Precision Level",
            options=[5, 6, 7],
            index=1,  # Default to level 6
            help="Higher precision levels create more detailed (smaller) geohash cells"
        )
        # Store in session state
        st.session_state.precision_level = precision_level
    
        if st.button("Convert to GeoHash", type="primary"):
                with st.spinner(f"Converting boundary to GeoHash Level {precision_level}..."):
                    geohash_result = convert_boundary_to_geohash(st.session_state.boundary_geojson, precision_level)
                    
                    if geohash_result and geohash_result.get("success"):
                        st.session_state.generated_geohash = geohash_result
                        st.success(f"✅ Generated {geohash_result['geohash_count']} GeoHash Level {precision_level} cells")
                    else:
                        st.error("❌ Failed to generate GeoHash. Please try again.")
    
    with col2:
        st.info(f"""
        **Precision Level {precision_level}:**
        """)



# Map display
if st.session_state.boundary_geojson or st.session_state.generated_geohash:
    st.subheader("🗺️ Map Preview")
    
    # Create map with boundary and geohash data
    map_obj = create_map_with_boundary_and_geohash(
        boundary_geojson=st.session_state.boundary_geojson,
        geohash_geojson=st.session_state.generated_geohash.get("geohashes_geojson") if st.session_state.generated_geohash else None
    )
    
    # Display map with white background - NO BLACK SPACE
    st.markdown("""
        <div style="background-color: #FFFFFF !important; 
                   padding: 15px; 
                   margin: 10px 0;
                   border-radius: 8px; 
                   border: 1px solid #E0E0E0;
                   overflow: hidden;
                   height: auto;">
    """, unsafe_allow_html=True)
    
    st_folium(map_obj, width=None, height=500)
    
    st.markdown("</div>", unsafe_allow_html=True)

# Download section
if st.session_state.generated_geohash:
    st.subheader("📥 Download Results")
    
    geohash_result = st.session_state.generated_geohash
    boundary_filename = st.session_state.uploaded_boundary.replace('.', '_') if st.session_state.uploaded_boundary else "boundary"
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Download GeoJSON
        geohash_geojson = geohash_result["geohashes_geojson"]
        geohash_str = json.dumps(geohash_geojson, ensure_ascii=False, indent=2)
        filename_geojson = f"{boundary_filename}_geohash_level_{st.session_state.precision_level}.geojson"
        
        st.download_button(
            label="📄 Download GeoHash GeoJSON",
            data=geohash_str,
            file_name=filename_geojson,
            mime="application/geo+json",
            key="download_boundary_geojson"
        )
    
    with col2:
        # Download CSV
            csv_data = geohash_result_to_csv(geohash_result)
            if csv_data:
                filename_csv = f"{boundary_filename}_geohash_level_{st.session_state.precision_level}.csv"
                
                st.download_button(
                    label="📊 Download GeoHash CSV",
                    data=csv_data,
                    file_name=filename_csv,
                    mime="text/csv",
                    key="download_boundary_csv"
                )
            else:
                st.error("❌ Failed to generate CSV data")

st.markdown("---")

# ============================================================================
# GEOJSON TO CSV CONVERTER SECTION
# ============================================================================

st.title("Geohash to CSV Converter")
st.markdown("Upload your GeoJSON files containing geohash polygons. Each file will be converted to a CSV with geometry coordinates.")

uploaded_files = st.file_uploader("📄 Upload GeoJSON files", type="geojson", accept_multiple_files=True, key="geojson_to_csv_uploader")

if uploaded_files:
    output_dir = tempfile.mkdtemp()
    csv_paths = []

    for file in uploaded_files:
        st.write(f"Processing: **{file.name}**")
        try:
            gdf = gpd.read_file(file)

            # Flatten geometry to WKT or GeoJSON string
            gdf['geometry'] = gdf['geometry'].apply(lambda geom: geom.wkt)

            csv_name = file.name.replace(".geojson", ".csv")
            csv_path = os.path.join(output_dir, csv_name)
            gdf.to_csv(csv_path, index=False)

            csv_paths.append(csv_path)
            st.success(f"✅ Converted: {csv_name}")
        except Exception as e:
            st.error(f"Error processing `{file.name}`: {e}")

    if len(csv_paths) == 1:
        # Single file: Download directly
        csv_path = csv_paths[0]
        with open(csv_path, "rb") as f:
            st.download_button(
                label="⬇️ Download CSV",
                data=f,
                file_name=os.path.basename(csv_path),
                mime="text/csv",
                key="download_single_csv"
            )

    elif len(csv_paths) > 1:
        # Multiple files: Zip and download
        zip_path = os.path.join(output_dir, "converted_csvs.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for csv_file in csv_paths:
                zipf.write(csv_file, os.path.basename(csv_file))

        with open(zip_path, "rb") as f:
            st.download_button(
                label="📦 Download All CSVs as ZIP",
                data=f,
                file_name="csv_output.zip",
                mime="application/zip",
                key="download_zip_csv"
            )

st.markdown("---")

# ============================================================================
# CSV TO GEOJSON CONVERTER SECTION
# ============================================================================

st.title("CSV to Geohash Converter")
st.markdown("Upload CSV files containing a 'geoHash' column. Each file will be converted to a GeoJSON with polygons.")

uploaded_files = st.file_uploader("📄 Upload CSV files", type="csv", accept_multiple_files=True, key="csv_to_geojson_uploader")

if uploaded_files:
    output_dir = tempfile.mkdtemp()
    geojson_paths = []

    for file in uploaded_files:
        st.write(f"Processing: **{file.name}**")
        df = pd.read_csv(file)

        if 'geoHash' not in df.columns:
            st.warning(f"Skipped `{file.name}` — missing 'geoHash' column.")
            continue

        try:
            df['geometry'] = df['geoHash'].apply(geohash_to_polygon)
            gdf = gpd.GeoDataFrame(df, geometry='geometry')
            gdf.set_crs(epsg=4326, inplace=True)

            geojson_name = file.name.replace(".csv", ".geojson")
            geojson_path = os.path.join(output_dir, geojson_name)
            gdf.to_file(geojson_path, driver='GeoJSON')

            geojson_paths.append(geojson_path)
            st.success(f"✅ Converted: {geojson_name}")

        except Exception as e:
            st.error(f"Error processing `{file.name}`: {e}")

    if len(geojson_paths) == 1:
        # Single file: Download directly
        geojson_path = geojson_paths[0]
        with open(geojson_path, "rb") as f:
            st.download_button(
                label="⬇️ Download GeoJSON",
                data=f,
                file_name=os.path.basename(geojson_path),
                mime="application/geo+json",
                key="download_single_geojson"
            )

    elif len(geojson_paths) > 1:
        # Multiple files: Zip and download
        zip_path = os.path.join(output_dir, "converted_geojsons.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for geojson_file in geojson_paths:
                zipf.write(geojson_file, os.path.basename(geojson_file))

        with open(zip_path, "rb") as f:
            st.download_button(
                label="📦 Download All GeoJSONs as ZIP",
                data=f,
                file_name="geojson_output.zip",
                mime="application/zip",
                key="download_zip_geojson"
            )

# Footer
st.markdown(
    """
    <hr style="margin-top: 2rem; margin-bottom: 1rem;">
    <div style='text-align: center; color: grey; font-size: 0.9rem;'>
        © 2025 ID Karta IoT Team
    </div>
    """,
    unsafe_allow_html=True
)
