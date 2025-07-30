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
    # Create base map
    m = folium.Map(location=[-2.5, 117.5], zoom_start=5)
    
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
st.title("📥 Download GeoHash")


# Initialize session state for persistent data
if 'geohash_result' not in st.session_state:
    st.session_state.geohash_result = None
if 'boundary_geojson' not in st.session_state:
    st.session_state.boundary_geojson = None
if 'selected_region_name' not in st.session_state:
    st.session_state.selected_region_name = None
if 'selected_country_name' not in st.session_state:
    st.session_state.selected_country_name = None

# Debug mode toggle (hidden for better UX)
debug_mode = False  # Set to True for development debugging

# Check API health
try:
    health_response = requests.get(f"{API_BASE_URL}/geospatial/health", timeout=5)
    if health_response.status_code != 200:
        st.error("❌ API server is not running. Please start the API server.")
        st.stop()
    else:
        if debug_mode:
            st.success("✅ API server is healthy")
            health_data = health_response.json()
            st.json(health_data)
except Exception as e:
    st.error("❌ Cannot connect to API server. Please check if it's running.")
    if debug_mode:
        st.error(f"Connection error: {str(e)}")
    st.stop()

# Test section for debugging (hidden when debug_mode is False)
if debug_mode:
    st.subheader("🧪 API Test")
  
# Main UI Layout - Input Controls
# Load countries
countries = get_countries()
if not countries:
    st.error("❌ No countries available from API.")
    st.stop()

# Country Selection
st.subheader("🌍 Select Country")
country_options = ["-- Select Country --"] + [country['name'] for country in countries]
selected_country_option = st.selectbox("Choose a country:", country_options)

# Region Selection
st.subheader("🏞️ Select Region")

if selected_country_option != "-- Select Country --":
    # Find selected country by name
    selected_country = next((c for c in countries if c['name'] == selected_country_option), None)
    country_id = selected_country['id'] if selected_country else None
    
    # Get boundary data
    boundary_data = get_boundary_data(country_id)
    
    if boundary_data and boundary_data.get("rows"):
        regions = boundary_data["rows"]
        
        # Create region options
        region_options = []
        for i, region in enumerate(regions):
            name = None
            for field in ['NAME']:
                if region.get(field) and str(region.get(field)).strip():
                    name = str(region.get(field)).strip()
                    break
            
            if not name:
                name = f"Region {i+1}"
            region_options.append(name)
        
        selected_region_name = st.selectbox("Choose a region:", ["-- Select Region --"] + region_options)
        
        if selected_region_name != "-- Select Region --":
            # Get selected region data
            selected_region_index = region_options.index(selected_region_name)
            selected_region_data = regions[selected_region_index]
            
            # Extract GeoJSON
            boundary_geojson = extract_geojson_from_boundary_data({"rows": [selected_region_data]})
            
            if boundary_geojson:
                # Store in session state
                st.session_state.boundary_geojson = boundary_geojson
                st.session_state.selected_region_name = selected_region_name
                st.session_state.selected_country_name = selected_country['name']
            else:
                st.error("❌ Could not extract valid geometry from selected region.")
    else:
        st.selectbox("Choose a region:", ["-- No regions available --"], disabled=True)
else:
    st.selectbox("Choose a region:", ["-- Select Country first --"], disabled=True)

if st.button("🚀 Generate GeoHash6", type="primary", disabled=not st.session_state.boundary_geojson):
    if st.session_state.boundary_geojson:
        # Convert to geohash6
        with st.spinner("Converting boundary to GeoHash6..."):
            geohash_result = convert_boundary_to_geohash6(st.session_state.boundary_geojson, debug_mode)
            
            if geohash_result and geohash_result.get("success"):
                st.session_state.geohash_result = geohash_result
                st.success(f"✅ Generated {geohash_result['geohash_count']} GeoHash6 cells")
                st.rerun()
            else:
                st.error("❌ Failed to generate GeoHash6. Please try again.")
    else:
        st.warning("⚠️ Please select a region or upload a boundary file first.")

# Map Display (Full Width)
if st.session_state.boundary_geojson or st.session_state.geohash_result:
    st.markdown("---")
    st.subheader("🗺️ Map Preview")
    
    # Create map with current data
    map_obj = create_map_with_data(
        boundary_geojson=st.session_state.boundary_geojson,
        geohash_geojson=st.session_state.geohash_result.get("geohashes_geojson") if st.session_state.geohash_result else None
    )
    
    # Display map with full width
    st_data = st_folium(map_obj, width=None, height=500)

# Download Section (always visible if data exists)
if st.session_state.geohash_result:
    st.markdown("---")
    st.subheader("📥 Download Results")
    
    geohash_result = st.session_state.geohash_result
    region_name = st.session_state.selected_region_name
    country_name = st.session_state.selected_country_name

    # Download buttons
    col1, col2 = st.columns(2)
    
    with col1:
        # Download GeoJSON
        geohash_geojson = geohash_result["geohashes_geojson"]
        geohash_str = json.dumps(geohash_geojson, ensure_ascii=False, indent=2)
        filename = f"{country_name.lower().replace(' ', '_')}_{region_name.lower().replace(' ', '_')}_geohash6.geojson"
        
        st.download_button(
            label="📄 Download GeoHash6 GeoJSON",
            data=geohash_str,
            file_name=filename,
            mime="application/geo+json",
            key="download_geojson"
        )
    
    with col2:
        # Download CSV
        csv_data = geohash_result_to_csv(geohash_result)
        if csv_data:
            filename_csv = f"{country_name.lower().replace(' ', '_')}_{region_name.lower().replace(' ', '_')}_geohash6.csv"
            
            st.download_button(
                label="📊 Download GeoHash6 CSV",
                data=csv_data,
                file_name=filename_csv,
                mime="text/csv",
                key="download_csv"
            )

st.markdown("""
---
<div style='text-align: center; color: grey; font-size: 0.9rem;'>
© 2025 ID Karta IoT Team 
</div>
""", unsafe_allow_html=True)