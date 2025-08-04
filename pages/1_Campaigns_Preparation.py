import streamlit as st
import json
import requests
import pandas as pd
import geopandas as gpd
from io import BytesIO
from config import settings
import folium
from streamlit_folium import st_folium
import math

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
        background-color: #F3F6FB !important;
    }
    
    .stFileUploader > div {
        background-color: #F3F6FB !important;
    }
    
    .stFileUploader > div > div {
        background-color: #F3F6FB !important;
    }
    
    .stFileUploader > div > div > div {
        background-color: #F3F6FB !important;
    }
    
    .stFileUploader > div > div > div > div {
        background-color: #F3F6FB !important;
    }
    
    /* File uploader drag and drop zone */
    div[data-testid="stFileUploader"] {
        background-color: #F3F6FB !important;
    }
    
    div[data-testid="stFileUploader"] > div {
        background-color: #F3F6FB !important;
    }
    
    div[data-testid="stFileUploader"] > div > div {
        background-color: #F3F6FB !important;
    }
    
    div[data-testid="stFileUploader"] > div > div > div {
        background-color: #F3F6FB !important;
    }
    
    /* File uploader section */
    section[data-testid="stFileUploader"] {
        background-color: #F3F6FB !important;
    }
    
    /* Upload area specific CSS classes */
    .css-1cpxqw2, .css-1erivf3, .css-1v0mbdj, .css-1kyxreq, .css-1d391kg {
        background-color: #F3F6FB !important;
    }
    
    /* Additional file uploader selectors */
    [data-testid="stFileUploader"] [data-testid="stMarkdownContainer"] {
        background-color: #F3F6FB !important;
    }
    
    /* Drag and drop area */
    .uploadedFile {
        background-color: #F3F6FB !important;
    }
    
    /* File drop zone */
    .css-1adrfps {
        background-color: #F3F6FB !important;
    }
    </style>
""", unsafe_allow_html=True)

def process_complete_geohash_workflow(
    country_id, 
    region_data,
    tag_filters=None,
    top_percent=0.5,
    precision=6,
    chunk_size=15,
    max_workers=10,
    use_cache=False,
    return_geojson=True
):
    """
    Complete workflow function that combines:
    1. Download Geohash - Convert boundary to geohash6
    2. Selected Geohash - Filter dense geohash cells
    3. Calculate Target UKM - Get road segments for dense areas
    
    Parameters:
    - country_id: ID of the selected country
    - region_data: Selected region boundary data
    - tag_filters: List of OSM tags for density filtering
    - top_percent: Percentage of top dense geohash to select (default: 0.5)
    - precision: Geohash precision level (default: 6)
    - chunk_size: Chunk size for UKM calculation (default: 15)
    - max_workers: Number of workers for parallel processing (default: 10)
    - use_cache: Whether to use cache for API calls (default: False)
    - return_geojson: Whether to return GeoJSON format (default: True)
    
    Returns:
    - Dictionary containing all results from the three steps
    """
    
    # Set default tag filters if not provided
    if tag_filters is None:
        tag_filters = [
            'shop', 'restaurant', 'fast_food', 'cafe', 'food_court',
            'bakery', 'convenience', 'supermarket', 'marketplace',
            'residential', 'building', 'commercial', 'retail',
            'bank', 'atm', 'clinic', 'pharmacy', 'hospital',
            'school', 'college', 'university',
            'parking', 'taxi', 'car_rental',
            'bus_station', 'bus_stop'
        ]
    
    result = {
        'success': False,
        'step1_geohash': None,
        'step2_dense_geohash': None,
        'step3_ukm_result': None,
        'errors': []
    }
    
    try:
        # STEP 1: Download Geohash - Convert boundary to geohash6        
        # Extract GeoJSON from region data
        boundary_geojson = extract_geojson_from_boundary_data({"rows": [region_data]})
        
        if not boundary_geojson:
            result['errors'].append("Failed to extract GeoJSON from boundary data")
            return result
        
        # Convert to geohash6
        geohash_result = convert_boundary_to_geohash6(boundary_geojson, precision)
        
        if not geohash_result or not geohash_result.get("success"):
            result['errors'].append("Failed to convert boundary to geohash6")
            return result
        
        result['step1_geohash'] = geohash_result
       
        # STEP 2: Selected Geohash - Filter dense geohash cells   
        # Use the generated geohash GeoJSON as boundary for dense selection
        dense_geohash_gdf = call_select_dense_geohash_api(
            boundary_data=geohash_result["geohashes_geojson"],
            tag_filters=tag_filters,
            top_percent=top_percent,
            precision=precision
        )
        
        if dense_geohash_gdf is None or dense_geohash_gdf.empty:
            result['errors'].append("Failed to filter dense geohash cells")
            return result
        
        result['step2_dense_geohash'] = dense_geohash_gdf
        
        # STEP 3: Calculate Target UKM - Get road segments
        # Extract geohash list from dense geohash result
        geohash_list = dense_geohash_gdf['geoHash'].dropna().astype(str).str.strip().unique().tolist()
        
        if not geohash_list:
            result['errors'].append("No valid geohashes found for UKM calculation")
            return result
        
        # Call UKM calculation API
        ukm_result = call_backend_calculate_ukm_advanced(
            geohashes=geohash_list,
            chunk_size=chunk_size,
            max_workers=max_workers,
            use_cache=use_cache,
            return_geojson=return_geojson
        )
        
        if not ukm_result or not ukm_result.get('success'):
            result['errors'].append("Failed to calculate UKM")
            return result
        
        result['step3_ukm_result'] = ukm_result
       
        result['success'] = True
        return result
        
    except Exception as e:
        result['errors'].append(f"Unexpected error in workflow: {str(e)}")
        return result

# Helper functions from the original files

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

def convert_boundary_to_geohash6(boundary_geojson, precision=6):
    """Convert boundary to geohash6 using API"""
    try:
        # Prepare the geometry for API
        if boundary_geojson.get("type") == "FeatureCollection" and boundary_geojson.get("features"):
            geometry_to_send = boundary_geojson["features"][0]["geometry"]
        elif boundary_geojson.get("type") == "Feature":
            geometry_to_send = boundary_geojson["geometry"]
        else:
            geometry_to_send = boundary_geojson
        
        payload = {
            "boundary_geojson": geometry_to_send,
            "precision": precision
        }
        
        response = requests.post(f"{API_BASE_URL}/geospatial/boundary-to-geohash", json=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            try:
                error_detail = response.json()
                st.error(f"Failed to convert to geohash: {response.status_code}")
                st.error(f"Error details: {error_detail}")
            except:
                st.error(f"Failed to convert to geohash: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error converting to geohash: {str(e)}")
        return None

def call_select_dense_geohash_api(boundary_data, tag_filters, top_percent=0.5, precision=6):
    """Call the API endpoint for dense geohash selection"""
    try:
        payload = {
            "boundary_geojson": boundary_data,
            "tag_filters": tag_filters,
            "top_percent": top_percent,
            "precision": precision
        }
        
        response = requests.post(
            f"{API_BASE_URL}/geospatial/select-dense-geohash",
            json=payload,
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                geojson_result = result["dense_geohash_geojson"]
                dense_gdf = gpd.GeoDataFrame.from_features(
                    geojson_result["features"], 
                    crs='EPSG:4326'
                )
                return dense_gdf
            else:
                st.error(f"❌ API returned error: {result}")
                return None
        else:
            error_detail = response.json().get("detail", "Unknown error") if response.content else "No response"
            st.error(f"❌ API call failed: {response.status_code} - {error_detail}")
            return None
            
    except requests.exceptions.Timeout:
        st.error("❌ Request timeout. The analysis is taking too long.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API. Make sure the API server is running on localhost:8000")
        return None
    except Exception as e:
        st.error(f"❌ Error calling API: {str(e)}")
        return None

def call_backend_calculate_ukm_advanced(geohashes, chunk_size=15, max_workers=10, use_cache=False, return_geojson=True):
    """Call FastAPI backend to calculate UKM with advanced options"""
    try:
        api_url = f"http://{settings.API_HOST}:{settings.API_PORT}/api/v1/geospatial/calculate-target-ukm-advanced"
        
        payload = {
            "geohashes": geohashes,
            "chunk_size": chunk_size,
            "max_workers": max_workers,
            "use_cache": use_cache,
            "return_geojson": return_geojson,
            "background_task": False
        }
        
        response = requests.post(api_url, json=payload, timeout=300)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"❌ API Error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        st.error("❌ Request timeout. The calculation is taking too long.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to the backend API. Please ensure the FastAPI server is running.")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error calling backend: {e}")
        return None

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

def create_workflow_map(boundary_geojson=None, dense_geohash_gdf=None, roads_geojson=None):
    """Create folium map with boundary, dense geohash, and roads data"""
    # Create base map centered on Indonesia with white background
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
    
    # Collect all bounds to fit the map properly
    all_bounds = []
    
    # Add boundary layer if available
    if boundary_geojson:
        bounds = get_bounds_from_geojson(boundary_geojson)
        if bounds:
            all_bounds.append(bounds)
        
        folium.GeoJson(
            boundary_geojson,
            name="Boundary Geohash Areas",
            style_function=lambda x: {
                "color": "#2E86AB", 
                "weight": 3, 
                "fillOpacity": 0.1,
                "fillColor": "#2E86AB",
                "dashArray": "5, 5"
            }
        ).add_to(m)
    
    # Add dense geohash layer if available
    if dense_geohash_gdf is not None and not dense_geohash_gdf.empty:
        # Convert GeoDataFrame to GeoJSON
        dense_geojson = json.loads(dense_geohash_gdf.to_json())
        
        # Get bounds from dense geohash
        dense_bounds = get_bounds_from_geojson(dense_geojson)
        if dense_bounds:
            all_bounds.append(dense_bounds)
        
        folium.GeoJson(
            dense_geojson,
            name="Selected Geohash Areas",
            style_function=lambda x: {
                "color": "#A23B72", 
                "weight": 2, 
                "fillOpacity": 0.6,
                "fillColor": "#A23B72"
            },
            popup=folium.GeoJsonPopup(
                fields=['geoHash', 'count'],
                aliases=['Geohash:', 'OSM Count:'],
                localize=True,
                labels=True
            )
        ).add_to(m)
    
    # Add roads layer if available
    if roads_geojson:
        # Get bounds from roads
        roads_bounds = get_bounds_from_geojson(roads_geojson)
        if roads_bounds:
            all_bounds.append(roads_bounds)
            
        folium.GeoJson(
            roads_geojson,
            name="Road Plan",
            style_function=lambda x: {
                "color": "#F18F01", 
                "weight": 2, 
                "opacity": 0.8
            },
            popup=folium.GeoJsonPopup(
                fields=['highway', 'name'],
                aliases=['Road Type:', 'Road Name:'],
                localize=True,
                labels=True
            )
        ).add_to(m)
    
    # Fit map to all data with proper padding
    if all_bounds:
        # Calculate combined bounds
        min_lat = min(bound[0][0] for bound in all_bounds)
        min_lon = min(bound[0][1] for bound in all_bounds)
        max_lat = max(bound[1][0] for bound in all_bounds)
        max_lon = max(bound[1][1] for bound in all_bounds)
        
        # Calculate margins - ensure minimum margin for very small areas
        lat_range = max_lat - min_lat
        lon_range = max_lon - min_lon
        
        # Use larger margin for very small areas, smaller for large areas
        if lat_range < 0.01 and lon_range < 0.01:  # Very small area
            lat_margin = 0.01
            lon_margin = 0.01
        elif lat_range < 0.1 and lon_range < 0.1:  # Small area
            lat_margin = max(lat_range * 0.2, 0.005)
            lon_margin = max(lon_range * 0.2, 0.005)
        else:  # Normal or large area
            lat_margin = lat_range * 0.05
            lon_margin = lon_range * 0.05
        
        padded_bounds = [
            [min_lat - lat_margin, min_lon - lon_margin],
            [max_lat + lat_margin, max_lon + lon_margin]
        ]
        
        m.fit_bounds(padded_bounds)
    
    # Add layer control (can be collapsed/expanded)
    folium.LayerControl(collapsed=True).add_to(m)
    
    # Add a mini map (optional - if plugins available)
    try:
        minimap = folium.plugins.MiniMap(toggle_display=True)
        m.add_child(minimap)
    except:
        pass  # Skip minimap if not available
    
    return m



# Forecast Budget Functions
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_countries_pricing():
    """Get all countries with their pricing information from API"""
    try:
        api_url = f"http://{settings.API_HOST}:{settings.API_PORT}/api/v1/country/pricing"
        response = requests.get(api_url, timeout=30)
        
        if response.status_code == 200:
            countries = response.json()
            if countries and len(countries) > 0:
                # Map API field names to simplified names
                mapped_countries = []
                for country in countries:
                    mapped_country = {
                        "id": country.get("id"),
                        "name": country.get("name"),
                        "currency": country.get("currency"),
                        "currency_symbol": country.get("currency_symbol"),
                        "ukm_price": country.get("ukm_price"),
                        "insurance": country.get("insurance_per_dax_per_month", country.get("insurance", 0)),
                        "dataplan": country.get("dataplan_per_dax_per_month", country.get("dataplan", 0)),
                        "exchange_rate_to_usd": country.get("exchange_rate_to_usd")
                    }
                    mapped_countries.append(mapped_country)
                return mapped_countries
            else:
                return get_fallback_countries()
        else:
            return get_fallback_countries()
            
    except:
        return get_fallback_countries()

def get_fallback_countries():
    """Fallback country data when API is unavailable"""
    return [
        {
            "id": 1,
            "name": "Indonesia",
            "currency": "IDR",
            "currency_symbol": "Rp",
            "ukm_price": 8000.0,
            "insurance": 132200.0,
            "dataplan": 450000.0,
            "exchange_rate_to_usd": 0.000063
        },
        {
            "id": 2,
            "name": "Malaysia", 
            "currency": "MYR",
            "currency_symbol": "RM",
            "ukm_price": 2.0,
            "insurance": 35.0,
            "dataplan": 120.0,
            "exchange_rate_to_usd": 0.22
        },
        {
            "id": 3,
            "name": "Thailand",
            "currency": "THB", 
            "currency_symbol": "฿",
            "ukm_price": 90.0,
            "insurance": 1200.0,
            "dataplan": 4000.0,
            "exchange_rate_to_usd": 0.029
        },
        {
            "id": 4,
            "name": "United States",
            "currency": "USD",
            "currency_symbol": "$", 
            "ukm_price": 0.25,
            "insurance": 8.5,
            "dataplan": 30.0,
            "exchange_rate_to_usd": 1.0
        }
    ]

def format_currency(amount, currency="USD", symbol="$"):
    """Format currency with proper symbol and decimal places"""
    if currency in ["IDR"]:
        return f"{symbol} {amount:,.0f}"
    else:
        return f"{symbol} {amount:,.2f}"

def forecast_budget_simple(target_km, dax_number, country_data):
    """Calculate forecast budget using country pricing with automatic week to month calculation"""
    # First calculate week estimation using formula: target_km / (dax_count * 100)
    week_estimation = target_km / (dax_number * 100)
    
    # Then convert to months using ceiling (always round up any fraction)
    month_estimation = math.ceil(week_estimation / 4)
    
    # Ensure minimum 1 month
    if month_estimation < 1:
        month_estimation = 1
    
    ukm_price = country_data['ukm_price']
    insurance_rate = country_data['insurance']
    dataplan_rate = country_data['dataplan']
    currency = country_data['currency']
    currency_symbol = country_data['currency_symbol']
    exchange_rate = country_data['exchange_rate_to_usd']
    
    basic_incentive = target_km * ukm_price
    bonus_coverage = basic_incentive
    insurance = insurance_rate * dax_number * month_estimation
    dataplan = dataplan_rate * dax_number * month_estimation
    
    total_before_misc = basic_incentive + bonus_coverage + insurance + dataplan
    miscellaneous = total_before_misc * 0.05
    total_forecast = total_before_misc + miscellaneous
    total_forecast_usd = total_forecast * exchange_rate
    
    return {
        "Week Estimation": round(week_estimation, 2),
        "Month Estimation": month_estimation,
        "Basic Incentive": round(basic_incentive),
        ">95% Bonus Coverage": round(bonus_coverage),
        "Insurance": round(insurance),
        "Dataplan": round(dataplan),
        "Miscellaneous (5%)": round(miscellaneous),
        "Total Forecast Budget": round(total_forecast),
        "Total Forecast Budget (USD)": round(total_forecast_usd, 2),
        "Currency": currency,
        "Symbol": currency_symbol,
        "Country": country_data['name']
    }

# Initialize session state for persistent results (must be at module level)
if 'workflow_result' not in st.session_state:
    st.session_state.workflow_result = None
if 'selected_country_info' not in st.session_state:
    st.session_state.selected_country_info = None
if 'selected_region_info' not in st.session_state:
    st.session_state.selected_region_info = None
if 'budget_result' not in st.session_state:
    st.session_state.budget_result = None
if 'is_processing' not in st.session_state:
    st.session_state.is_processing = False

# Example usage function for Streamlit UI
def streamlit_complete_workflow_ui():
    # Custom CSS for background color and text
    st.markdown("""
    <style>
    .stApp {
        background-color: #F3F6FB;
        color: #000000;
    }
    .main .block-container {
        background-color: #F3F6FB;
        color: #000000;
    }
    .css-1d391kg {
        background-color: #F3F6FB;
        color: #000000;
    }
    .css-1y4p8pa {
        background-color: #F3F6FB;
        color: #000000;
    }
    .sidebar .sidebar-content {
        background-color: #F3F6FB;
        color: #000000;
    }
    .css-17eq0hr {
        background-color: #F3F6FB;
        color: #000000;
    }
    section[data-testid="stSidebar"] {
        background-color: #F3F6FB;
        color: #000000;
    }
    /* Text elements */
    .stMarkdown, .stText, p, span, div, h1, h2, h3, h4, h5, h6 {
        color: #000000 !important;
    }
    /* Selectbox and input text */
    .stSelectbox label, .stNumberInput label, .stTextInput label {
        color: #000000 !important;
    }
    /* Button text - keep default styling for contrast */
    .stButton button {
        color: inherit;
    }
    /* Metric labels and values */
    .metric-container {
        color: #000000 !important;
    }
    [data-testid="metric-container"] {
        color: #000000 !important;
    }
    /* Navbar/Header styling */
    .css-18e3th9 {
        background-color: #F3F6FB !important;
    }
    .css-1d391kg {
        background-color: #F3F6FB !important;
    }
    header[data-testid="stHeader"] {
        background-color: #F3F6FB !important;
    }
    .css-1rs6os {
        background-color: #F3F6FB !important;
    }
    .css-10trblm {
        background-color: #F3F6FB !important;
    }
    /* Streamlit header */
    .css-1y0tads {
        background-color: #F3F6FB !important;
    }
    /* Dropdown/Selectbox styling */
    .stSelectbox > div > div {
        background-color: #FFFFFF !important;
    }
    .css-1wa3eu0-placeholder {
        background-color: #FFFFFF !important;
    }
    .css-26l3qy-menu {
        background-color: #FFFFFF !important;
    }
    .css-1uccc91-singleValue {
        color: #000000 !important;
    }
    .css-1n7v3ny-option {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    .css-1n7v3ny-option:hover {
        background-color: #F0F0F0 !important;
    }
    /* Dropdown when opened/focused */
    .css-1pahdxg-control--is-focused {
        background-color: #FFFFFF !important;
        border-color: #2196F3 !important;
    }
    .css-1hwfws3 {
        background-color: #FFFFFF !important;
    }
    .css-1pahdxg-control {
        background-color: #FFFFFF !important;
    }
    .css-1s2u09g-control {
        background-color: #FFFFFF !important;
    }
    .css-1s2u09g-control--is-focused {
        background-color: #FFFFFF !important;
        border-color: #2196F3 !important;
        box-shadow: 0 0 0 1px #2196F3 !important;
    }
    /* Dropdown menu list */
    .css-26l3qy-menu-list {
        background-color: #FFFFFF !important;
    }
    .css-1n7v3ny-option--is-focused {
        background-color: #E3F2FD !important;
        color: #000000 !important;
    }
    .css-1n7v3ny-option--is-selected {
        background-color: #2196F3 !important;
        color: #FFFFFF !important;
    }
    /* Dropdown container background */
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
    }
    div[data-testid="stSelectbox"] > div {
        background-color: #FFFFFF !important;
    }
    div[data-testid="stSelectbox"] > div > div {
        background-color: #FFFFFF !important;
    }
    /* Modern Streamlit dropdown container */
    div[data-testid="stSelectbox"] div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
    }
    /* Dropdown menu container - simple positioning below */
    .css-26l3qy-menu {
        background-color: #FFFFFF !important;
        border: 1px solid #CCCCCC !important;
        border-radius: 4px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
    }
    .css-1hwfws3-menu {
        background-color: #FFFFFF !important;
        border: 1px solid #CCCCCC !important;
        border-radius: 4px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
    }
    /* Streamlit selectbox dropdown menu */
    div[data-testid="stSelectbox"] div[data-baseweb="popover"] > div {
        background-color: #FFFFFF !important;
        border: 1px solid #CCCCCC !important;
        border-radius: 4px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
    }
    /* Modern Streamlit dropdown menu */
    .st-emotion-cache-1y0tads {
        background-color: #FFFFFF !important;
    }
    /* Dropdown options container */
    div[role="listbox"] {
        background-color: #FFFFFF !important;
    }
    /* Individual dropdown options */
    div[role="option"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    div[role="option"]:hover {
        background-color: #F0F0F0 !important;
        color: #000000 !important;
    }
    /* Force all menu lists below */
    .css-26l3qy-menu-list {
        background-color: #FFFFFF !important;
    }
    /* Additional dropdown menu styles */
    div[data-testid="stSelectbox"] [role="combobox"] + div {
        background-color: #FFFFFF !important;
    }
    /* Ensure all dropdown menus appear below */
    [data-baseweb="menu"] {
        background-color: #FFFFFF !important;
    }
    /* Force dropdown placement to bottom only */
    div[data-baseweb="popover"][data-placement*="top"] {
        display: none !important;
    }
    div[data-baseweb="popover"]:not([data-placement*="top"]) {
        background-color: #FFFFFF !important;
    }
    /* Override Streamlit's auto-positioning to force bottom placement */
    .stSelectbox div[data-baseweb="select"] {
        position: relative !important;
    }
    /* Ensure dropdown always opens downward */
    div[data-testid="stSelectbox"] div[data-baseweb="popover"] {
        transform: translateY(0) !important;
        top: 100% !important;
        bottom: auto !important;
        margin-top: 2px !important;
    }
    /* Alternative selector for newer Streamlit versions */
    div[data-testid="stSelectbox"] > div > div > div[data-baseweb="popover"] {
        transform: translateY(0) !important;
        top: 100% !important;
        bottom: auto !important;
        margin-top: 2px !important;
    }
    /* Dropdown loading/disabled state */
    .css-1s2u09g-control--is-disabled {
        background-color: #FFFFFF !important;
        color: #666666 !important;
        opacity: 0.7 !important;
    }
    .css-1pahdxg-control--is-disabled {
        background-color: #FFFFFF !important;
        color: #666666 !important;
        opacity: 0.7 !important;
    }
    .stSelectbox select:disabled {
        background-color: #FFFFFF !important;
        color: #666666 !important;
    }
    /* Dropdown placeholder when loading */
    .css-1wa3eu0-placeholder {
        background-color: #FFFFFF !important;
        color: #666666 !important;
    }
    /* Dropdown with loading state */
    .css-1hwfws3[aria-disabled="true"] {
        background-color: #FFFFFF !important;
        color: #666666 !important;
    }
    /* Streamlit selectbox disabled state */
    .stSelectbox[data-disabled="true"] > div > div {
        background-color: #FFFFFF !important;
        color: #666666 !important;
        opacity: 0.7 !important;
    }
    .stSelectbox > div > div[aria-disabled="true"] {
        background-color: #FFFFFF !important;
        color: #666666 !important;
        opacity: 0.7 !important;
    }
    /* General disabled selectbox */
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
    }
    div[data-testid="stSelectbox"][aria-disabled="true"] div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        color: #666666 !important;
        opacity: 0.7 !important;
    }
    /* Dropdown text color - BLACK */
    .stSelectbox > div > div {
        color: #000000 !important;
    }
    .css-1uccc91-singleValue {
        color: #000000 !important;
    }
    .css-1wa3eu0-placeholder {
        color: #000000 !important;
    }
    /* Dropdown input text */
    div[data-testid="stSelectbox"] div[role="combobox"] {
        color: #000000 !important;
    }
    div[data-testid="stSelectbox"] * {
        color: #000000 !important;
    }
    /* Override any white text in dropdown */
    .stSelectbox div,
    .stSelectbox span,
    .stSelectbox input {
        color: #000000 !important;
    }
    /* React Select text components */
    div[class*="css-"][class*="singleValue"] {
        color: #000000 !important;
    }
    div[class*="css-"][class*="placeholder"] {
        color: #000000 !important;
    }
    /* Force specific control text classes */
    .css-1pahdxg-control,
    .css-1s2u09g-control,
    .css-1hwfws3,
    .css-1wa3eu0,
    .css-1uccc91 {
        color: #000000 !important;
    }
    /* Universal dropdown text override */
    [data-testid="stSelectbox"] [class*="css-"] {
        color: #000000 !important;
    }
    /* DROPDOWN ALL STATES - Loading, Expanded, Focused */
    /* Loading state */
    .stSelectbox div[aria-busy="true"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    .css-1s2u09g-control--is-loading {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    .css-1pahdxg-control--is-loading {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    /* Expanded/Open state */
    .css-1s2u09g-control--menu-is-open {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    .css-1pahdxg-control--menu-is-open {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    /* Focused state */
    .css-1s2u09g-control--is-focused {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border-color: #2196F3 !important;
        box-shadow: 0 0 0 1px #2196F3 !important;
    }
    .css-1pahdxg-control--is-focused {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border-color: #2196F3 !important;
    }
    /* Disabled state */
    .css-1s2u09g-control--is-disabled {
        background-color: #FFFFFF !important;
        color: #CCCCCC !important;
        opacity: 0.7 !important;
    }
    .css-1pahdxg-control--is-disabled {
        background-color: #FFFFFF !important;
        color: #CCCCCC !important;
        opacity: 0.7 !important;
    }
    /* Loading indicator */
    .css-1pahdxg .css-1wa3eu0-placeholder,
    .css-1s2u09g .css-1wa3eu0-placeholder {
        color: #000000 !important;
    }
    /* Dropdown value when selected */
    .css-1pahdxg .css-1uccc91-singleValue,
    .css-1s2u09g .css-1uccc91-singleValue {
        color: #000000 !important;
    }
    /* All dropdown states universal override */
    div[data-testid="stSelectbox"] div[class*="css-"][class*="control"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    div[data-testid="stSelectbox"] div[class*="css-"][class*="control"] * {
        color: #000000 !important;
    }
    /* Override any state changes */
    .stSelectbox [class*="control"]:hover,
    .stSelectbox [class*="control"]:focus,
    .stSelectbox [class*="control"]:active {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    /* DROPDOWN OPTIONS - When clicked and opened */
    /* All dropdown options white background */
    div[role="option"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    div[role="option"]:hover {
        background-color: #F0F0F0 !important;
        color: #000000 !important;
    }
    div[role="option"]:focus {
        background-color: #E3F2FD !important;
        color: #000000 !important;
    }
    /* Dropdown menu container */
    .css-26l3qy-menu {
        background-color: #FFFFFF !important;
        border: 1px solid #CCCCCC !important;
        border-radius: 4px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
    }
    .css-1hwfws3-menu {
        background-color: #FFFFFF !important;
        border: 1px solid #CCCCCC !important;
        border-radius: 4px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
    }
    /* Menu list container */
    .css-26l3qy-menu-list {
        background-color: #FFFFFF !important;
    }
    /* Selected option */
    .css-1n7v3ny-option--is-selected {
        background-color: #2196F3 !important;
        color: #FFFFFF !important;
    }
    /* Focused option */
    .css-1n7v3ny-option--is-focused {
        background-color: #E3F2FD !important;
        color: #000000 !important;
    }
    /* Regular options */
    .css-1n7v3ny-option {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    .css-1n7v3ny-option:hover {
        background-color: #F0F0F0 !important;
    }
    /* Dropdown loading message */
    .css-1wa3eu0-placeholder {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    /* "Loading..." or "No options" text */
    div[data-testid="stSelectbox"] div[class*="css-"][class*="noOptionsMessage"],
    div[data-testid="stSelectbox"] div[class*="css-"][class*="loadingMessage"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    /* UNIVERSAL DROPDOWN STATE OVERRIDE */
    /* All selectbox states - comprehensive coverage */
    .stSelectbox,
    .stSelectbox *,
    div[data-testid="stSelectbox"],
    div[data-testid="stSelectbox"] * {
        transition: none !important;
    }
    /* Dropdown container in all states */
    div[data-testid="stSelectbox"] div[data-baseweb="select"],
    div[data-testid="stSelectbox"] div[data-baseweb="select"] *:not([role="option"]) {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    /* Dropdown when loading regions */
    .stSelectbox div[aria-expanded="false"],
    .stSelectbox div[aria-expanded="true"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    /* Streamlit specific loading and disabled states */
    div[data-testid="stSelectbox"][data-disabled="true"],
    div[data-testid="stSelectbox"][data-disabled="true"] * {
        background-color: #FFFFFF !important;
        color: #CCCCCC !important;
    }
    /* Override theme colors completely */
    .stSelectbox > div > div[class*="css-"],
    .stSelectbox > div > div[class*="css-"] * {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    /* Number input styling */
    .stNumberInput > div > div > input {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    /* Text input styling */
    .stTextInput > div > div > input {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    /* Primary button styling - Generate Plan button */
    .stButton > button[kind="primary"] {
        background-color: #085A3E !important;
        border: 1px solid #085A3E !important;
        color: #FFFFFF !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #064229 !important;
        border: 1px solid #064229 !important;
        color: #FFFFFF !important;
    }
    .stButton > button[kind="primary"]:active {
        background-color: #053822 !important;
        border: 1px solid #053822 !important;
        color: #FFFFFF !important;
    }
    /* Alternative primary button selectors */
    button[data-testid="baseButton-primary"] {
        background-color: #085A3E !important;
        border: 1px solid #085A3E !important;
        color: #FFFFFF !important;
    }
    button[data-testid="baseButton-primary"]:hover {
        background-color: #064229 !important;
        border: 1px solid #064229 !important;
        color: #FFFFFF !important;
    }
    /* More specific text color for button content */
    .stButton > button[kind="primary"] p,
    .stButton > button[kind="primary"] span,
    .stButton > button[kind="primary"] div {
        color: #FFFFFF !important;
    }
    button[data-testid="baseButton-primary"] p,
    button[data-testid="baseButton-primary"] span,
    button[data-testid="baseButton-primary"] div {
        color: #FFFFFF !important;
    }
    /* Streamlit primary button text override */
    div[data-testid="stButton"] button[kind="primary"] {
        color: #FFFFFF !important;
    }
    div[data-testid="stButton"] button[kind="primary"] * {
        color: #FFFFFF !important;
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
    
    /* Map responsive sizing - Force white background */
    .folium-map {
        width: 100% !important;
        height: 100% !important;
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
    
    /* Override any dark map themes */
    .folium-map * {
        background-color: transparent !important;
    }
    
    /* Map wrapper div */
    div[data-testid="stIFrame"] > div {
        background-color: #FFFFFF !important;
    }
    
    /* Additional iframe background fixes */
    iframe[title*="folium"] {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
    }
    
    /* Force streamlit map container background */
    .streamlit-folium > div {
        background-color: #FFFFFF !important;
    }
    
    /* Remove black from any map loading states */
    .stSpinner,
    .stSpinner > div {
        background-color: transparent !important;
    }
    
    /* CRITICAL: Fix black space below map */
    /* Force iframe height to match content exactly */
    iframe[title="streamlit_folium.st_folium"] {
        height: 450px !important;
        max-height: 450px !important;
        min-height: 450px !important;
        overflow: hidden !important;
    }
    
    /* Remove any extra space below iframe */
    div[data-testid="stIFrame"] {
        height: auto !important;
        max-height: 470px !important;
        overflow: hidden !important;
        background-color: #FFFFFF !important;
    }
    
    /* Force container to not expand beyond content */
    .streamlit-folium {
        height: auto !important;
        max-height: 470px !important;
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
    
    /* FORCE ALL DROPDOWNS TO BE WHITE - NUCLEAR OPTION */
    /* Universal dropdown override */
    * {
        transition: none !important;
    }
    
    /* Force all select elements */
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
    
    /* Additional aggressive dropdown targeting */
    .stSelectbox, .stSelectbox *, 
    [data-testid="stSelectbox"], [data-testid="stSelectbox"] *,
    div[data-testid="stSelectbox"], div[data-testid="stSelectbox"] * {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        background: #FFFFFF !important;
    }
    
    /* Universal override for any dark themed elements */
    [style*="background"] {
        background-color: #FFFFFF !important;
    }
    
    /* Force all CSS classes with dark colors */
    [class*="css-"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* Override any inherited styles */
    .stApp * {
        background-color: inherit !important;
        color: #000000 !important;
    }
    
    /* Specific override for dropdown containers */
    .stApp .stSelectbox {
        background-color: #FFFFFF !important;
    }
    
    .stApp .stSelectbox * {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* FORCE DROPDOWN POSITIONING ON CONTAINER LEVEL */
    /* Set selectbox container positioning */
    .stSelectbox,
    [data-testid="stSelectbox"] {
        position: relative !important;
        overflow: visible !important;
    }
    
    /* Set dropdown wrapper positioning */
    .stSelectbox > div,
    [data-testid="stSelectbox"] > div {
        position: relative !important;
        overflow: visible !important;
    }
    
    /* Set BaseWeb select container positioning */
    [data-testid="stSelectbox"] div[data-baseweb="select"] {
        position: relative !important;
        overflow: visible !important;
    }
    
    /* Force dropdown menu positioning below */
    [data-testid="stSelectbox"] [data-baseweb="popover"] {
        position: absolute !important;
        top: calc(100% + 4px) !important;
        left: 0 !important;
        right: 0 !important;
        z-index: 1000 !important;
    }
    
    /* Hide upward facing dropdowns */
    [data-testid="stSelectbox"] [data-baseweb="popover"][data-placement*="top"] {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Navigation header
    st.markdown("<h1 style='text-align: center; color: #000000;'>Campaign Preparation</h1>", unsafe_allow_html=True)
   
    # API health check
    try:
        health_response = requests.get(f"{API_BASE_URL}/geospatial/health", timeout=5)
        if health_response.status_code != 200:
            st.error("❌ API server is not running. Please start the API server.")
            st.stop()
    except Exception as e:
        st.error("❌ Cannot connect to API server. Please check if it's running.")
        st.stop()
    
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
        selected_country = next((c for c in countries if c['name'] == selected_country_option), None)
        country_id = selected_country['id'] if selected_country else None
        
        boundary_data = get_boundary_data(country_id)
        
        if boundary_data and boundary_data.get("rows"):
            regions = boundary_data["rows"]
            
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
            
            # Check if valid region is selected
            region_selected = selected_region_name != "-- Select Region --"
            
            if region_selected:
                selected_region_index = region_options.index(selected_region_name)
                selected_region_data = regions[selected_region_index]
                
                # Use default values for advanced options
                top_percent = 0.5
                chunk_size = 15
                max_workers = 10
                precision = 6
        
            
            # Show button with appropriate state
            if region_selected:
                # Check if currently processing
                is_processing = st.session_state.get('is_processing', False)
                
                if is_processing:
                    st.button("🔄 Processing...", type="secondary", disabled=True, use_container_width=True)
                    generate_clicked = False
                else:
                    generate_clicked = st.button("Generate Plan", type="primary", use_container_width=True)
                    
              
            else:
                st.button("Generate Plan", type="primary", disabled=True, use_container_width=True)
                generate_clicked = False
            
            # Process workflow if button clicked and region selected
            if generate_clicked and region_selected:
                # Set processing state
                st.session_state.is_processing = True
                
                # Clear previous results and store new selection info
                st.session_state.workflow_result = None
                st.session_state.budget_result = None  # Clear budget too
                st.session_state.selected_country_info = selected_country
                st.session_state.selected_region_info = {
                    'name': selected_region_name,
                    'data': selected_region_data
                }
                
                with st.spinner("🔄 Processing - this may take a few minutes..."):
                    result = process_complete_geohash_workflow(
                        country_id=country_id,
                        region_data=selected_region_data,
                        top_percent=top_percent,
                        precision=precision,
                        chunk_size=chunk_size,
                        max_workers=max_workers,
                        use_cache=False
                    )
                
                # Clear processing state
                st.session_state.is_processing = False
                
                # Store result in session state
                st.session_state.workflow_result = result
                
                if result['success']:
                    st.success("✅ **Plan generation completed successfully!**")
                    st.info("📊 Results will be displayed below...")
                    st.balloons()  # Celebration animation
                    st.rerun()  # Refresh to show results
                else:
                    st.error("❌ **Plan generation failed!**")
                    st.write("**Error Details:**")
                    for error in result['errors']:
                        st.error(f"• {error}")
                    st.info("💡 Please try again or contact support if the problem persists.")
        else:
            st.selectbox("Choose a region:", ["-- No regions available --"], disabled=True)
            st.button("Generate Plan", type="primary", disabled=True, use_container_width=True)
            st.warning("⚠️ No regions available for the selected country")
    else:
        st.selectbox("Choose a region:", ["-- Select Country first --"], disabled=True)
        
        # Always show Generate Plan button (disabled)
        st.button("Generate Plan", type="primary", disabled=True, use_container_width=True)
        

    # Display results and download buttons if workflow has been completed
    # This section is outside all the selection logic to ensure it always runs
    if (hasattr(st.session_state, 'workflow_result') and 
        st.session_state.workflow_result and 
        st.session_state.workflow_result.get('success', False) and
        hasattr(st.session_state, 'selected_country_info') and
        hasattr(st.session_state, 'selected_region_info') and
        st.session_state.selected_country_info and
        st.session_state.selected_region_info):
        
        result = st.session_state.workflow_result
        selected_country = st.session_state.selected_country_info
        selected_region = st.session_state.selected_region_info
        
        st.markdown("---")
        
        # 1. Map Preview After Processing
        st.subheader("🗺️ Results Map Preview")
        
        # Create map with all available data
        try:
            # Get boundary data for map (if available from step1)
            boundary_geojson = None
            if result['step1_geohash'] and result['step1_geohash'].get('geohashes_geojson'):
                # Use original boundary if available, otherwise use generated geohash as boundary reference
                boundary_geojson = result['step1_geohash']['geohashes_geojson']
            
            # Get dense geohash data
            dense_geohash_gdf = result['step2_dense_geohash']
            
            # Get roads data
            roads_geojson = result['step3_ukm_result'].get('roads_geojson')
            
            # Create and display map
            map_obj = create_workflow_map(
                boundary_geojson=boundary_geojson,
                dense_geohash_gdf=dense_geohash_gdf,
                roads_geojson=roads_geojson
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
            
            map_data = st_folium(
                map_obj, 
                width=None, 
                height=450,  # Fixed height to prevent black space
                returned_objects=["last_clicked"],
                key="workflow_map"
            )
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Show clicked feature info if available
            if map_data['last_clicked'] and map_data['last_clicked'].get('lat'):
                clicked_lat = map_data['last_clicked']['lat']
                clicked_lng = map_data['last_clicked']['lng']
                st.info(f"📍 Clicked Location: {clicked_lat:.6f}, {clicked_lng:.6f}")
                    
        except Exception as e:
            st.error(f"❌ Error creating map preview: {str(e)}")
            st.info("🗺️ Map preview unavailable, but you can still download the data files.")
        
        # 2. Forecast Budget Section - minimal spacing
        st.markdown("<br>", unsafe_allow_html=True)  # Small spacing instead of full markdown divider
        st.subheader("💱 Forecast Budget Calculator")
        
        try:
            # Load countries pricing data
            countries_pricing = get_countries_pricing()
            
            if countries_pricing:
                # Create country lookup
                country_dict = {country['name']: country for country in countries_pricing}
                country_names = list(country_dict.keys())
                
                # Get target km from workflow result
                target_km = result['step3_ukm_result']['total_road_length_km']
                
                # Use columns for compact input layout
                col1, col2 = st.columns([1, 1])
                
                with col1:   
                    # Display auto-filled target km from workflow result
                    st.metric("📏 UKM Target", f"{target_km:.2f} km")
                    
                    # Country selection
                    selected_budget_country = st.selectbox(
                        "🌍 Country for Pricing:",
                        options=country_names,
                        index=0 if country_names else None,
                        key="budget_country_selector"
                    )
                    
                with col2:
                    # DAX number input
                    dax_number = st.number_input(
                        "👷 DAX Count:", 
                        min_value=1, 
                        value=1,
                        step=1,
                        help="Number of DAX (drivers)"
                    )
                    
                    # Enhanced Calculate Budget button with validation
                    budget_ready = target_km > 0 and dax_number > 0 and selected_budget_country
                    
                    if budget_ready:
                        calculate_budget = st.button(
                            "💰 Calculate Budget", 
                            type="primary",
                            use_container_width=True,
                            key="calculate_budget_btn"
                        )
                    else:
                        st.button(
                            "💰 Calculate Budget", 
                            type="primary",
                            disabled=True,
                            use_container_width=True,
                            key="calculate_budget_btn_disabled"
                        )
                        calculate_budget = False
                
                # Show validation warnings below columns
                if not budget_ready:
                    if target_km <= 0:
                        st.warning("⚠️ Target KM must be > 0")
                    if dax_number <= 0:
                        st.warning("⚠️ DAX count must be > 0") 
                    if not selected_budget_country:
                        st.warning("⚠️ Select a country")
                
                # Handle budget calculation
                if calculate_budget and selected_budget_country:
                    try:
                        # Get selected country data
                        country_data = country_dict[selected_budget_country]
                        
                        # Calculate forecast budget
                        budget_result = forecast_budget_simple(target_km, dax_number, country_data)
                        
                        # Add calculation parameters to result
                        budget_result['target_km_input'] = target_km
                        budget_result['dax_number_input'] = dax_number
                        
                        # Store in session state
                        st.session_state.budget_result = budget_result
                        
                        st.success("✅ Budget calculated!")
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                
                # Display budget result if available
                if (hasattr(st.session_state, 'budget_result') and 
                    st.session_state.budget_result):
                    
                    budget_result = st.session_state.budget_result
                    
                    # Display country and currency info
                    currency = budget_result['Currency']
                    symbol = budget_result['Symbol']
                    
                    st.markdown("<br>", unsafe_allow_html=True)  # Small spacing
                    # Budget breakdown with more compact format
                    st.markdown("**💰 Budget Breakdown:**")
                    breakdown_items = [
                        ("Duration", f"{budget_result['Month Estimation']} months"),
                        ("Basic Incentive", format_currency(budget_result['Basic Incentive'], currency, symbol)),
                        (">95% Bonus", format_currency(budget_result['>95% Bonus Coverage'], currency, symbol)),
                        ("Insurance", format_currency(budget_result['Insurance'], currency, symbol)),
                        ("Data Plan", format_currency(budget_result['Dataplan'], currency, symbol)),
                        ("Misc (5%)", format_currency(budget_result['Miscellaneous (5%)'], currency, symbol))
                    ]
                    
                    for item, value in breakdown_items:
                        st.write(f"• **{item}**: {value}")
                    
                    total_local = format_currency(budget_result['Total Forecast Budget'], currency, symbol)
                    total_usd = f"${budget_result['Total Forecast Budget (USD)']:,.2f}"
                    
                    st.success(f"""
                    **💵 Total Budget:**  
                    **{total_local}**  
                    **{total_usd} USD**
                    """)
                       
            else:
                st.error("❌ Unable to load pricing data")
                
        except Exception as e:
            st.error(f"❌ Error loading budget calculator: {str(e)}")
        
        # Download options - closer spacing
        st.markdown("<br>", unsafe_allow_html=True)  # Small spacing instead of full divider
        st.subheader("📥 Download Results")
        
        download_col1, download_col2, download_col3 = st.columns(3)
        
        with download_col1:
            # Download original geohash
            geohash_str = json.dumps(result['step1_geohash']["geohashes_geojson"], indent=2)
            filename_prefix = f"{selected_country['name'].lower().replace(' ', '_')}_{selected_region['name'].lower().replace(' ', '_')}"
            
            st.download_button(
                "📄 Download All Geohash",
                geohash_str,
                f"{filename_prefix}_all_geohash.geojson",
                "application/geo+json",
                key="download_all_geohash"
            )
        
        with download_col2:
            # Download dense geohash
            buffer = BytesIO()
            result['step2_dense_geohash'].to_file(buffer, driver="GeoJSON")
            buffer.seek(0)
            st.download_button(
                "🧭 Download Selected Geohash",
                buffer.getvalue(),
                f"{filename_prefix}_dense_geohash.geojson",
                "application/geo+json",
                key="download_dense_geohash"
            )
        
        with download_col3:
            # Download roads
            if result['step3_ukm_result'].get('roads_geojson'):
                roads_str = json.dumps(result['step3_ukm_result']['roads_geojson'], indent=2)
                st.download_button(
                    "🛣️ Download Roads Plan",
                    roads_str,
                    f"{filename_prefix}_roads.geojson",
                    "application/geo+json",
                    key="download_roads"
                )
        
        # Clear results button
        st.markdown("<br>", unsafe_allow_html=True)  # Small spacing
        if st.button("🗑️ Clear All Results", help="Clear workflow and budget results to start over"):
            if hasattr(st.session_state, 'workflow_result'):
                st.session_state.workflow_result = None
            if hasattr(st.session_state, 'selected_country_info'):
                st.session_state.selected_country_info = None
            if hasattr(st.session_state, 'selected_region_info'):
                st.session_state.selected_region_info = None
            if hasattr(st.session_state, 'budget_result'):
                st.session_state.budget_result = None
            if hasattr(st.session_state, 'is_processing'):
                st.session_state.is_processing = False
            st.success("✅ All results cleared!")
            st.rerun()
    
    # If no results but there's a failed workflow, show error info
    elif (hasattr(st.session_state, 'workflow_result') and 
          st.session_state.workflow_result and 
          not st.session_state.workflow_result.get('success', False)):
        st.error("❌ Last workflow execution failed!")
        st.write("**Errors:**")
        for error in st.session_state.workflow_result.get('errors', []):
            st.error(f"• {error}")
   
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

if __name__ == "__main__":
    streamlit_complete_workflow_ui()
