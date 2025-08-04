import streamlit as st
import json
import folium
from streamlit_folium import st_folium
import os
import numpy as np
from shapely.geometry import shape, GeometryCollection, box, Polygon
from shapely.validation import make_valid
import geohash2
import pandas as pd
import requests



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
    
    /* File uploader drag and drop area */
    .stFileUploader > div > div > div > div {
        background-color: #FFFFFF !important;
    }
    
    /* File uploader drag and drop zone */
    div[data-testid="stFileUploader"] > div > div > div {
        background-color: #FFFFFF !important;
    }
    
    /* File uploader section */
    section[data-testid="stFileUploader"] {
        background-color: #FFFFFF !important;
    }
    
    /* Upload area styling */
    .css-1cpxqw2, .css-1erivf3, .css-1v0mbdj {
        background-color: #FFFFFF !important;
    }
    
    /* Map container optimization - Force white background */
    .streamlit-folium {
        width: 100% !important;
        background-color: #FFFFFF !important;
    }
    
    /* Map iframe styling - Remove black background */
    iframe[title="streamlit_folium.st_folium"] {
        width: 100% !important;
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
    .leaflet-container,
    .leaflet-tile-pane,
    .leaflet-map-pane {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
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
    </style>
""", unsafe_allow_html=True)

# API Helper Functions
def get_countries():
    """Get list of available countries from API"""
    try:
        response = requests.get(f"{API_BASE_URL}/boundary/all")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to load countries: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error connecting to API: {str(e)}")
        return []

def get_boundary_data(country_id):
    """Get boundary data for a specific country from API"""
    try:
        payload = {"country_id": country_id}
        response = requests.post(f"{API_BASE_URL}/boundary/", json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to load boundary data: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error getting boundary data: {str(e)}")
        return None

def convert_boundary_to_geohash6(boundary_geojson, debug_mode=False):
    """Convert boundary to geohash6 using API (not cached for real-time updates)"""
    try:
        # Prepare the geometry for API - extract first feature's geometry if it's a FeatureCollection
        if boundary_geojson.get("type") == "FeatureCollection" and boundary_geojson.get("features"):
            geometry_to_send = boundary_geojson["features"][0]["geometry"]
        elif boundary_geojson.get("type") == "Feature":
            geometry_to_send = boundary_geojson["geometry"]
        else:
            geometry_to_send = boundary_geojson
        
        payload = {
            "boundary_geojson": geometry_to_send,
            "precision": 6
        }
        
        if debug_mode:
            st.write("**Debug: Payload being sent to API:**")
            st.json(payload)
        
        response = requests.post(f"{API_BASE_URL}/geospatial/boundary-to-geohash", json=payload)
        
        if debug_mode:
            st.write(f"**Debug: Response status code:** {response.status_code}")
            st.write(f"**Debug: Response headers:** {dict(response.headers)}")
        
        if response.status_code == 200:
            return response.json()
        else:
            # Try to get error details
            try:
                error_detail = response.json()
                st.error(f"Failed to convert to geohash: {response.status_code}")
                st.error(f"Error details: {error_detail}")
            except:
                st.error(f"Failed to convert to geohash: {response.status_code}")
                st.error(f"Raw response: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error converting to geohash: {str(e)}")
        return None

def extract_geojson_from_boundary_data(boundary_data):
    """Extract GeoJSON from boundary data response using API"""
    try:
        payload = {"boundary_data": boundary_data}
        response = requests.post(f"{API_BASE_URL}/geospatial/extract-geojson", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return result.get("geojson")
        return None
    except Exception as e:
        st.error(f"Error extracting GeoJSON: {str(e)}")
        return None

def geohash_result_to_csv(geohash_result):
    """Convert geohash API result to CSV format using API"""
    try:
        if not geohash_result or not geohash_result.get("geohashes_geojson"):
            return ""
        
        payload = {"geohashes_geojson": geohash_result["geohashes_geojson"]}
        response = requests.post(f"{API_BASE_URL}/geospatial/geohash-to-csv", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return result.get("csv_data", "")
        return ""
    except Exception as e:
        st.error(f"Error converting to CSV: {str(e)}")
        return ""

def get_bounds_from_geojson(geojson):
    """Calculate bounds from GeoJSON for map fitting using API"""
    try:
        if not geojson or not geojson.get('features'):
            return None
        
        payload = {"geojson": geojson}
        response = requests.post(f"{API_BASE_URL}/geospatial/get-bounds", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return result.get("bounds")
        return None
    except Exception as e:
        st.error(f"Error calculating bounds: {str(e)}")
        return None

def create_map_with_data(boundary_geojson=None, geohash_geojson=None):
    """Create folium map with boundary and geohash data"""
    # Create base map with white background
    m = folium.Map(
        location=[-2.5, 117.5], 
        zoom_start=5,
        tiles='OpenStreetMap',
        prefer_canvas=True
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
            m.fit_bounds(bounds)
        
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
            name="GeoHash6",
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

# Setup
st.set_page_config(layout="wide")

# Navigation header
st.markdown("<h1 style='text-align: center; color: #000000;'>Campaign Evaluation</h1>", unsafe_allow_html=True)


