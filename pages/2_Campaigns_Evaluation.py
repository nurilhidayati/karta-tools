import streamlit as st
import pandas as pd
import geopandas as gpd
import csv
import ast
import osmnx as ox
import json
import io
import os
import math
import numpy as np
from collections import Counter, defaultdict
from io import StringIO
from shapely.geometry import LineString, shape, box

st.set_page_config(page_title="Campaign Evaluation", layout="wide")

# Custom CSS for navbar, sidebar, and main background colors
st.markdown("""
<style>
    /* Navbar background color - Multiple selectors for compatibility */
    .stApp > header {
        background-color: #F3F6FB !important;
    }
    
    header[data-testid="stHeader"] {
        background-color: #F3F6FB !important;
    }
    
    .css-18ni7ap {
        background-color: #F3F6FB !important;
    }
    
    .css-vk3wp9 {
        background-color: #F3F6FB !important;
    }
    
    .stApp header {
        background-color: #F3F6FB !important;
    }
    
    /* Navbar text color - Make all navbar text black */
    .stApp > header * {
        color: black !important;
    }
    
    header[data-testid="stHeader"] * {
        color: black !important;
    }
    
    .css-18ni7ap * {
        color: black !important;
    }
    
    .css-vk3wp9 * {
        color: black !important;
    }
    
    .stApp header * {
        color: black !important;
    }
    
    /* Navbar links and buttons */
    .stApp header a, .stApp header button {
        color: black !important;
    }
    
    header[data-testid="stHeader"] a, header[data-testid="stHeader"] button {
        color: black !important;
    }
    
    /* AGGRESSIVE NAVBAR TEXT FORCING - Override everything in navbar */
    .stApp > header div, .stApp > header span, .stApp > header p, .stApp > header h1, .stApp > header h2, .stApp > header h3 {
        color: black !important;
    }
    
    header[data-testid="stHeader"] div, header[data-testid="stHeader"] span, header[data-testid="stHeader"] p {
        color: black !important;
    }
    
    header[data-testid="stHeader"] h1, header[data-testid="stHeader"] h2, header[data-testid="stHeader"] h3 {
        color: black !important;
    }
    
    /* Target Streamlit specific navbar elements */
    .css-1v0mbdj.e1tzin5v2, .css-1cpxqw2.e1ewe7hr3 {
        color: black !important;
    }
    
    /* Force navbar text in all possible states */
    .stApp header .css-1v0mbdj, .stApp header .css-1cpxqw2 {
        color: black !important;
    }
    
    /* Target navigation elements specifically */
    nav *, nav a, nav button, nav div, nav span {
        color: black !important;
    }
    
    /* Additional navbar element targeting */
    [data-testid="stHeader"] .css-1v0mbdj, [data-testid="stHeader"] .css-1cpxqw2 {
        color: black !important;
    }
    
    /* Nuclear option for navbar - force black on everything */
    header *, header, 
    .stApp > header *, .stApp > header,
    [data-testid="stHeader"] *, [data-testid="stHeader"] {
        color: black !important;
    }
    
    /* Main content background color */
    .stApp {
        background-color: #F3F6FB !important;
    }
    
    .main .block-container {
        background-color: #F3F6FB !important;
    }
    
    section[data-testid="stMain"] {
        background-color: #F3F6FB !important;
    }
    
    .css-1lcbmhc {
        background-color: #F3F6FB !important;
    }
    
    /* Sidebar background color */
    .css-1d391kg {
        background-color: white !important;
    }
    
    .css-1cypcdb {
        background-color: white !important;
    }
    
    /* Additional sidebar selectors for different Streamlit versions */
    section[data-testid="stSidebar"] > div {
        background-color: white !important;
    }
    
    .css-k1vhr4 {
        background-color: white !important;
    }
    
    /* Ensure sidebar text is visible on white background */
    .css-1d391kg .css-17eq0hr {
        color: #262730 !important;
    }
    
    /* Change all text color to black */
    .stApp {
        color: black !important;
    }
    
    .stApp .main {
        color: black !important;
    }
    
    /* Ensure all text elements are black */
    .stApp p, .stApp div, .stApp span, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        color: black !important;
    }
    
    /* Streamlit specific text elements */
    .css-1629p8f, .css-1cpxqw2, .css-1v0mbdj, .css-1evcfpn {
        color: black !important;
    }
    
    /* Markdown text */
    .stMarkdown {
        color: black !important;
    }
    
    /* Text input labels */
    .stTextInput label {
        color: black !important;
    }
    
    /* Metric labels and values */
    .css-1wivap2, .css-1xarl3l {
        color: black !important;
    }
    
    /* Default button text - Force white color */
    .stButton button {
        color: #FFFFFF !important;
    }
    
    /* Force all button text to be white - Multiple selectors */
    .stButton button * {
        color: #FFFFFF !important;
    }
    
    .stButton > button {
        color: #FFFFFF !important;
    }
    
    .stButton > button * {
        color: #FFFFFF !important;
    }
    
    button {
        color: #FFFFFF !important;
    }
    
    button * {
        color: #FFFFFF !important;
    }
    
    /* Force button text in all states */
    .stButton button:hover, .stButton button:focus, .stButton button:active {
        color: #FFFFFF !important;
    }
    
    .stButton button:hover *, .stButton button:focus *, .stButton button:active * {
        color: #FFFFFF !important;
    }
    
    /* Run Complete Gap Analysis button - specific styling */
    .stButton > button[kind="primary"] {
        background-color: #085A3E !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 12px 24px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #06412F !important;
        color: #FFFFFF !important;
    }
    
    /* Alternative selector for primary button */
    button[data-testid="baseButton-primary"] {
        background-color: #085A3E !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    
    button[data-testid="baseButton-primary"]:hover {
        background-color: #06412F !important;
        color: #FFFFFF !important;
    }
    
    /* Additional selectors for primary button */
    .css-1cpxqw2[data-testid="baseButton-primary"] {
        background-color: #085A3E !important;
        color: #FFFFFF !important;
    }
    
    .stButton button[type="submit"] {
        background-color: #085A3E !important;
        color: #FFFFFF !important;
    }
    
    /* CSS class based selector for primary button */
    .css-1r6slb0 {
        background-color: #085A3E !important;
        color: #FFFFFF !important;
    }
    
    .css-1r6slb0:hover {
        background-color: #06412F !important;
        color: #FFFFFF !important;
    }
    
    /* Keep sidebar text readable on white background */
    section[data-testid="stSidebar"] {
        color: black !important;
    }
    
    /* Alert messages - keep their default colors for visibility */
    .stAlert .css-1cpxqw2 {
        color: inherit !important;
    }
    
    /* Success messages */
    .stSuccess {
        color: #155724 !important;
    }
    
    /* Error messages */
    .stError {
        color: #721c24 !important;
    }
    
    /* Warning messages */
    .stWarning {
        color: #856404 !important;
    }
    
    /* Info messages */
    .stInfo {
        color: #004085 !important;
    }
    
    /* File uploader container - force white background */
    .stFileUploader {
        background-color: white !important;
        border-radius: 8px !important;
        padding: 10px !important;
        border: 1px solid #ddd !important;
    }
    
    /* File uploader text - force black */
    .stFileUploader label {
        color: black !important;
    }
    
    .stFileUploader .css-1cpxqw2 {
        color: black !important;
    }
    
    .stFileUploader div {
        color: black !important;
    }
    
    /* Upload button styling */
    .stFileUploader button {
        background-color: #085A3E !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 8px 16px !important;
        font-weight: 500 !important;
    }
    
    .stFileUploader button:hover {
        background-color: #06412F !important;
        color: #FFFFFF !important;
    }
    
    /* Upload area drag and drop - force white background */
    .stFileUploader > div > div {
        background-color: white !important;
        color: black !important;
    }
    
    /* Drag and drop zone specific */
    .stFileUploader [data-testid="stFileUploadDropzone"] {
        background-color: white !important;
        border: 2px dashed #cccccc !important;
        color: black !important;
    }
    
    .stFileUploader [data-testid="stFileUploadDropzone"] div {
        background-color: white !important;
        color: black !important;
    }
    
    /* File uploader inner area */
    .css-1v8vjqx {
        background-color: white !important;
        color: black !important;
    }
    
    .css-1v8vjqx .css-1cpxqw2 {
        color: black !important;
    }
    
    /* Upload area text */
    .stFileUploader .css-1v8vjqx {
        color: black !important;
        background-color: white !important;
    }
    
    /* Additional specific selectors for upload area */
    .stFileUploader section {
        background-color: white !important;
    }
    
    .stFileUploader section div {
        background-color: white !important;
        color: black !important;
    }
    
    /* Upload zone text elements */
    .stFileUploader section p {
        color: black !important;
    }
    
    .stFileUploader section small {
        color: #666666 !important;
    }
    
    /* AGGRESSIVE BUTTON TEXT FORCING - Override everything */
    button[data-testid*="button"] {
        color: #FFFFFF !important;
    }
    
    button[data-testid*="button"] * {
        color: #FFFFFF !important;
    }
    
    button[data-testid*="baseButton"] {
        color: #FFFFFF !important;
    }
    
    button[data-testid*="baseButton"] * {
        color: #FFFFFF !important;
    }
    
    /* Target all Streamlit button variations */
    .stButton, .stButton *, 
    .stDownloadButton, .stDownloadButton *,
    .stFormSubmitButton, .stFormSubmitButton * {
        color: #FFFFFF !important;
    }
    
    /* Target button content specifically */
    .stButton button span,
    .stButton button div,
    .stButton button p {
        color: #FFFFFF !important;
    }
    
    /* Force all primary buttons */
    button[kind="primary"],
    button[kind="primary"] *,
    button[type="primary"],
    button[type="primary"] * {
        color: #FFFFFF !important;
    }
    
    /* Override any inherited text colors in buttons */
    .stApp button,
    .stApp button *,
    .stApp .stButton,
    .stApp .stButton * {
        color: #FFFFFF !important;
    }
    
    /* Nuclear option - Force white on all button-related CSS classes */
    .css-1cpxqw2,
    .css-1r6slb0,
    .css-k1vhr4 button,
    .css-1evcfpn button,
    .css-1v0mbdj button {
        color: #FFFFFF !important;
    }
    
    /* Target button text by element type within buttons */
    button span, button div, button p, button a, button label {
        color: #FFFFFF !important;
    }
    
    /* Make sure download buttons are white too */
    [data-testid="stDownloadButton"] button,
    [data-testid="stDownloadButton"] button *,
    .stDownloadButton button,
    .stDownloadButton button * {
        color: #FFFFFF !important;
    }
    
    /* Universal override for button elements */
    *[role="button"], *[role="button"] * {
        color: #FFFFFF !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("Campaign Evaluation")

# Initialize session state variables
session_vars = [
    "flattened_data", "road_gdf", "restricted_areas_gdf", 
    "restricted_roads_gdf", "final_analysis_result", "analysis_completed", "ai_analysis_result"
]

for var in session_vars:
    if var not in st.session_state:
        st.session_state[var] = None

if "analysis_completed" not in st.session_state:
    st.session_state.analysis_completed = False

# Helper functions
def generate_geohash(lat, lon, precision=5):
    """Generate geohash for given coordinates"""
    base32 = "0123456789bcdefghjkmnpqrstuvwxyz"
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    
    geohash = []
    bits = 0
    bit = 0
    ch = 0
    even = True
    
    while len(geohash) < precision:
        if even:  # longitude
            mid = (lon_range[0] + lon_range[1]) / 2
            if lon >= mid:
                ch |= (1 << (4 - bit))
                lon_range[0] = mid
            else:
                lon_range[1] = mid
        else:  # latitude
            mid = (lat_range[0] + lat_range[1]) / 2
            if lat >= mid:
                ch |= (1 << (4 - bit))
                lat_range[0] = mid
            else:
                lat_range[1] = mid
        
        even = not even
        
        if bit < 4:
            bit += 1
        else:
            geohash.append(base32[ch])
            bit = 0
            ch = 0
    
    return ''.join(geohash)

def geohash_to_bbox(geohash):
    """Convert geohash back to bounding box"""
    base32 = "0123456789bcdefghjkmnpqrstuvwxyz"
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    
    even = True
    
    for c in geohash:
        cd = base32.index(c)
        
        for mask in [16, 8, 4, 2, 1]:
            if even:  # longitude
                mid = (lon_range[0] + lon_range[1]) / 2
                if cd & mask:
                    lon_range[0] = mid
                else:
                    lon_range[1] = mid
            else:  # latitude
                mid = (lat_range[0] + lat_range[1]) / 2
                if cd & mask:
                    lat_range[0] = mid
                else:
                    lat_range[1] = mid
            
            even = not even
    
    return lat_range[0], lon_range[0], lat_range[1], lon_range[1]  # min_lat, min_lon, max_lat, max_lon

def create_polygon_from_coords(coords_data):
    """Create polygon with buffer around coordinate points"""
    if not coords_data or len(coords_data) == 0:
        return None
    
    # Get min/max coordinates
    lats = [coord[1] for coord in coords_data]  # y coordinates (latitude)
    lons = [coord[0] for coord in coords_data]  # x coordinates (longitude)
    
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    
    # Add buffer (approximately 5km in degrees)
    buffer_deg = 0.045  # roughly 5km
    
    return box(min_lon - buffer_deg, min_lat - buffer_deg, 
              max_lon + buffer_deg, max_lat + buffer_deg)

def flatten_coordinates_from_file(uploaded_file):
    output_rows = []
    content = uploaded_file.getvalue().decode('utf-8')
    lines = content.splitlines()
    header = lines[0]
    data_lines = lines[1:]

    for start in range(0, len(data_lines), 1000):
        batch_lines = data_lines[start:start + 1000]
        reader = csv.DictReader(StringIO("\n".join([header] + batch_lines)))
        for row in reader:
            try:
                coords_data = ast.literal_eval(row.get("road_coordinates", "[]"))
                if coords_data and len(coords_data) > 0 and isinstance(coords_data[0], (int, float)):
                    coords_data = [coords_data]
                for segment_index, segment_coords in enumerate(coords_data, start=1):
                    if segment_coords is None:
                        continue
                    for coord in segment_coords:
                        if coord is None or len(coord) < 2:
                            continue
                        output_rows.append({
                            "country_id": row.get("country_id", ""),
                            "id": row.get("id", ""),
                            "grid_id": row.get("grid_id", ""),
                            "created_at": row.get("created_at", ""),
                            "report_user_id": row.get("report_user_id", ""),
                            "type": row.get("type", ""),
                            "org_code": row.get("org_code", ""),
                            "note": row.get("note", ""),
                            "segment_id": f"{row.get('id', '')}_{segment_index}",
                            "x": coord[0],
                            "y": coord[1],
                        })
            except Exception as e:
                st.error(f"❌ Error in row {row.get('id', '')}: {e}")

    return pd.DataFrame(output_rows)

def convert_csv_to_geojson(df):
    if df is None or len(df) == 0:
        return gpd.GeoDataFrame()
        
    lines = []
    metadata_rows = []
    for seg_id, group in df.groupby("segment_id"):
        coords = list(zip(group["x"], group["y"]))
        if len(coords) >= 2:  # Need at least 2 points for a LineString
            lines.append(LineString(coords))
            meta = group.iloc[0].copy()
            # Remove x, y columns since they're now in geometry, don't add coords list
            meta = meta.drop(['x', 'y'], errors='ignore')
            metadata_rows.append(meta)

    if len(lines) == 0:
        return gpd.GeoDataFrame()

    gdf_roads = gpd.GeoDataFrame(metadata_rows, geometry=lines, crs="EPSG:4326")
    gdf_singlepart = gdf_roads.explode(index_parts=False).reset_index(drop=True)
    return gdf_singlepart

def download_restricted_areas(polygon):
    try:
        tags = {
            "landuse": ["military", "industrial", "commercial", "government", "cemetery", "landfill"],
            "leisure": ["nature_reserve", "golf_course"],
            "boundary": ["protected_area"],
            "aeroway": ["aerodrome"],
            "building": ["military", "government", "warehouse", "university", "school", "hospital"],
            "amenity": ["school", "college", "university", "police", "hospital", "kindergarten"],
            "barrier": ["fence", "wall", "gate", "bollard"],
            "access": ["private", "customers", "permit", "military", "no"]
        }
        gdf = ox.features.features_from_polygon(polygon, tags=tags)
        if gdf is not None and len(gdf) > 0:
            # Filter to only polygon geometries
            polygon_mask = gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
            gdf = gdf[polygon_mask]
            return gdf
        else:
            return gpd.GeoDataFrame()
    except Exception as e:
        st.warning(f"Could not download restricted areas: {e}")
        return gpd.GeoDataFrame()

def download_restricted_roads(polygon):
    try:
        tags = {
            "highway": ["service", "unclassified", "track"],
            "access": ["private", "customers", "permit", "military", "no"],
            "motorcycle": ["no", "private"],
            "service": ["driveway", "alley", "emergency_access"],
        }
        gdf = ox.features.features_from_polygon(polygon, tags=tags)
        if gdf is not None and len(gdf) > 0:
            # Filter to only line geometries
            line_mask = gdf.geometry.geom_type.isin(["LineString", "MultiLineString"])
            gdf = gdf[line_mask]
            return gdf
        else:
            return gpd.GeoDataFrame()
    except Exception as e:
        st.warning(f"Could not download restricted roads: {e}")
        return gpd.GeoDataFrame()

def analyze_gap_intersections(gdf_roads, gdf_polygons, gdf_lines, distance_meters=100.0):
    # Check for empty GeoDataFrames
    if gdf_roads is None or len(gdf_roads) == 0:
        return gpd.GeoDataFrame()
    if gdf_polygons is None or len(gdf_polygons) == 0:
        return gpd.GeoDataFrame()
    if gdf_lines is None or len(gdf_lines) == 0:
        return gpd.GeoDataFrame()
        
    if gdf_roads.crs.is_geographic:
        utm_crs = gdf_roads.estimate_utm_crs()
        gdf_roads = gdf_roads.to_crs(utm_crs)
        gdf_polygons = gdf_polygons.to_crs(utm_crs)
        gdf_lines = gdf_lines.to_crs(utm_crs)

    buffered_polygons = gdf_polygons.buffer(distance_meters)
    buffered_polygons_gdf = gpd.GeoDataFrame(geometry=buffered_polygons, crs=gdf_polygons.crs)

    combined_geometry = pd.concat([buffered_polygons_gdf.geometry, gdf_lines.geometry], ignore_index=True)
    all_combined = gpd.GeoDataFrame(geometry=combined_geometry, crs=buffered_polygons_gdf.crs)

    selected = gpd.sjoin(gdf_roads, all_combined, how="inner", predicate="intersects")
    
    # Get column names excluding those that might contain lists (unhashable types)
    safe_columns = []
    for col in gdf_roads.columns:
        if col != 'coords' and col != 'geometry':  # Exclude coords column and geometry
            try:
                # Test if column values are hashable
                sample_val = gdf_roads[col].iloc[0] if len(gdf_roads) > 0 else None
                if sample_val is not None:
                    hash(sample_val)  # This will raise TypeError if unhashable
                safe_columns.append(col)
            except (TypeError, AttributeError):
                # Skip columns with unhashable types
                continue
    
    # Use safe columns for duplicate removal, or use index if no safe columns
    if safe_columns:
        selected = selected.drop_duplicates(subset=safe_columns)
    else:
        selected = selected.drop_duplicates()
    
    return selected.to_crs("EPSG:4326")

# AI/ML Analysis Functions
def analyze_osm_features_with_ai(intersecting_roads_gdf, restricted_areas_gdf, restricted_roads_gdf):
    """Advanced AI analysis of OSM features affecting the roads"""
    
    analysis_results = {
        'area_types': {},
        'road_restrictions': {},
        'severity_analysis': {},
        'geographic_patterns': {},
        'recommendations': []
    }
    
    try:
        # Analyze restricted areas
        if restricted_areas_gdf is not None and len(restricted_areas_gdf) > 0:
            area_analysis = analyze_area_features(restricted_areas_gdf)
            analysis_results['area_types'] = area_analysis
        
        # Analyze restricted roads  
        if restricted_roads_gdf is not None and len(restricted_roads_gdf) > 0:
            road_analysis = analyze_road_features(restricted_roads_gdf)
            analysis_results['road_restrictions'] = road_analysis
        
        # Severity and impact analysis
        if intersecting_roads_gdf is not None and len(intersecting_roads_gdf) > 0:
            severity_analysis = calculate_impact_severity(intersecting_roads_gdf, restricted_areas_gdf, restricted_roads_gdf)
            analysis_results['severity_analysis'] = severity_analysis
            
            # Geographic clustering analysis
            geographic_analysis = analyze_geographic_patterns(intersecting_roads_gdf)
            analysis_results['geographic_patterns'] = geographic_analysis
            
            # Generate AI recommendations
            recommendations = generate_ai_recommendations(analysis_results)
            analysis_results['recommendations'] = recommendations

    except Exception as e:
        st.warning(f"AI analysis encountered an issue: {e}")
        # Return basic results even if AI analysis fails
        analysis_results['recommendations'] = [{
            'type': 'SYSTEM',
            'priority': 'LOW',
            'message': f"AI analysis partially completed. Basic intersection results available."
        }]
    
    return analysis_results

def analyze_area_features(restricted_areas_gdf):
    """Analyze types of restricted areas using ML categorization"""
    
    # Define OSM feature categories with intelligent mapping
    area_categories = {
        'High Security': ['military', 'government', 'police', 'restricted'],
        'Educational': ['school', 'college', 'university', 'kindergarten'],
        'Healthcare': ['hospital', 'clinic', 'medical'],
        'Industrial': ['industrial', 'warehouse', 'factory', 'commercial'],
        'Environmental': ['nature_reserve', 'protected_area', 'cemetery', 'landfill'],
        'Transportation': ['aerodrome', 'airport', 'helipad'],
        'Recreational': ['golf_course', 'sports', 'leisure'],
        'Infrastructure': ['fence', 'wall', 'gate', 'bollard', 'barrier']
    }
    
    feature_analysis = defaultdict(list)
    category_counts = Counter()
    total_area = 0
    
    # Analyze each feature
    for idx, feature in restricted_areas_gdf.iterrows():
        feature_tags = {}
        
        # Extract all available tags from the feature
        for col in restricted_areas_gdf.columns:
            if col != 'geometry':
                try:
                    col_value = feature[col]
                    if pd.notna(col_value) and col_value is not None and str(col_value).strip():
                        feature_tags[col] = col_value
                except:
                    continue
        
        # Calculate area if possible
        try:
            if hasattr(feature.geometry, 'area'):
                feature_area = feature.geometry.area * 111000 * 111000  # Convert to square meters approximately
                total_area += feature_area
            else:
                feature_area = 0
        except:
            feature_area = 0
        
        # Categorize feature using ML-like approach
        categorized = False
        for category, keywords in area_categories.items():
            for keyword in keywords:
                # Check if keyword appears in any tag value
                for tag_key, tag_value in feature_tags.items():
                    if keyword.lower() in str(tag_value).lower():
                        category_counts[category] += 1
                        feature_analysis[category].append({
                            'tags': feature_tags,
                            'area_sqm': feature_area,
                            'primary_tag': f"{tag_key}={tag_value}"
                        })
                        categorized = True
                        break
                if categorized:
                    break
            if categorized:
                break
        
        # If not categorized, put in 'Other'
        if not categorized:
            category_counts['Other'] += 1
            feature_analysis['Other'].append({
                'tags': feature_tags,
                'area_sqm': feature_area,
                'primary_tag': list(feature_tags.items())[0] if feature_tags else 'unknown'
            })
    
    return {
        'categories': dict(category_counts),
        'details': dict(feature_analysis),
        'total_features': len(restricted_areas_gdf),
        'total_area_sqm': total_area,
        'most_common': category_counts.most_common(3)
    }

def analyze_road_features(restricted_roads_gdf):
    """Analyze restricted road features"""
    
    road_categories = {
        'Access Restricted': ['private', 'customers', 'permit', 'no'],
        'Service Roads': ['service', 'driveway', 'alley', 'emergency_access'],
        'Vehicle Specific': ['motorcycle', 'bicycle', 'motor_vehicle'],
        'Road Type': ['unclassified', 'track', 'path', 'footway'],
        'Military/Security': ['military', 'restricted']
    }
    
    road_analysis = defaultdict(list)
    category_counts = Counter()
    total_length = 0
    
    for idx, road in restricted_roads_gdf.iterrows():
        road_tags = {}
        
        # Extract road tags
        for col in restricted_roads_gdf.columns:
            if col != 'geometry':
                try:
                    col_value = road[col]
                    if pd.notna(col_value) and col_value is not None and str(col_value).strip():
                        road_tags[col] = col_value
                except:
                    continue
        
        # Calculate length in kilometers
        try:
            road_length_km = road.geometry.length * 111  # Convert to kilometers approximately
            total_length += road_length_km
        except:
            road_length_km = 0
        
        # Categorize road
        categorized = False
        for category, keywords in road_categories.items():
            for keyword in keywords:
                for tag_key, tag_value in road_tags.items():
                    if keyword.lower() in str(tag_value).lower():
                        category_counts[category] += 1
                        road_analysis[category].append({
                            'tags': road_tags,
                            'length_km': road_length_km,
                            'primary_tag': f"{tag_key}={tag_value}"
                        })
                        categorized = True
                        break
                if categorized:
                    break
            if categorized:
                break
        
        if not categorized:
            category_counts['Other'] += 1
            road_analysis['Other'].append({
                'tags': road_tags,
                'length_km': road_length_km,
                'primary_tag': list(road_tags.items())[0] if road_tags else 'unknown'
            })
    
    return {
        'categories': dict(category_counts),
        'details': dict(road_analysis),
        'total_roads': len(restricted_roads_gdf),
        'total_length_km': total_length,
        'most_common': category_counts.most_common(3)
    }

def calculate_impact_severity(intersecting_roads_gdf, restricted_areas_gdf, restricted_roads_gdf):
    """Calculate impact severity using ML-like scoring"""
    
    # Define severity weights for different restriction types
    severity_weights = {
        'military': 10,
        'government': 9,
        'police': 9,
        'hospital': 8,
        'school': 7,
        'university': 7,
        'industrial': 6,
        'private': 5,
        'commercial': 4,
        'residential': 3,
        'recreational': 2,
        'other': 1
    }
    
    total_severity_score = 0
    severity_breakdown = defaultdict(int)
    intersection_density = len(intersecting_roads_gdf)
    
    # Calculate area-based severity
    if restricted_areas_gdf is not None and len(restricted_areas_gdf) > 0:
        for idx, area in restricted_areas_gdf.iterrows():
            area_tags = {}
            for col in restricted_areas_gdf.columns:
                if col != 'geometry':
                    try:
                        col_value = area[col]
                        if pd.notna(col_value) and col_value is not None and str(col_value).strip():
                            area_tags[col] = col_value
                    except:
                        continue
            
            # Find highest severity weight for this area
            area_severity = 1  # default
            for tag_key, tag_value in area_tags.items():
                for keyword, weight in severity_weights.items():
                    if keyword in str(tag_value).lower():
                        area_severity = max(area_severity, weight)
                        severity_breakdown[keyword] += 1
                        break
            
            total_severity_score += area_severity
    
    # Calculate road-based severity
    if restricted_roads_gdf is not None and len(restricted_roads_gdf) > 0:
        for idx, road in restricted_roads_gdf.iterrows():
            road_tags = {}
            for col in restricted_roads_gdf.columns:
                if col != 'geometry':
                    try:
                        col_value = road[col]
                        if pd.notna(col_value) and col_value is not None and str(col_value).strip():
                            road_tags[col] = col_value
                    except:
                        continue
            
            road_severity = 1  # default
            for tag_key, tag_value in road_tags.items():
                for keyword, weight in severity_weights.items():
                    if keyword in str(tag_value).lower():
                        road_severity = max(road_severity, weight)
                        break
            
            total_severity_score += road_severity * 0.5  # Roads have half weight of areas
    
    # Normalize severity
    max_possible_score = len(restricted_areas_gdf if restricted_areas_gdf is not None else []) * 10 + \
                        len(restricted_roads_gdf if restricted_roads_gdf is not None else []) * 5
    
    normalized_severity = (total_severity_score / max(max_possible_score, 1)) * 100
    
    # Classify severity level
    if normalized_severity >= 80:
        severity_level = "CRITICAL"
        severity_color = "🔴"
    elif normalized_severity >= 60:
        severity_level = "HIGH"
        severity_color = "🟠"
    elif normalized_severity >= 40:
        severity_level = "MEDIUM"
        severity_color = "🟡"
    elif normalized_severity >= 20:
        severity_level = "LOW"
        severity_color = "🟢"
    else:
        severity_level = "MINIMAL"
        severity_color = "🔵"
    
    return {
        'severity_score': normalized_severity,
        'severity_level': severity_level,
        'severity_color': severity_color,
        'intersection_density': intersection_density,
        'severity_breakdown': dict(severity_breakdown),
        'total_raw_score': total_severity_score
    }

def analyze_geographic_patterns(intersecting_roads_gdf):
    """Analyze geographic clustering patterns using spatial analysis"""
    
    if len(intersecting_roads_gdf) == 0:
        return {}
    
    # Get coordinates of intersecting roads
    coords = []
    for idx, road in intersecting_roads_gdf.iterrows():
        try:
            centroid = road.geometry.centroid
            coords.append([centroid.x, centroid.y])
        except:
            continue
    
    if len(coords) == 0:
        return {}
    
    coords_array = np.array(coords)
    
    # Calculate basic geographic statistics
    center_lon = np.mean(coords_array[:, 0])
    center_lat = np.mean(coords_array[:, 1])
    
    spread_lon = np.std(coords_array[:, 0])
    spread_lat = np.std(coords_array[:, 1])
    
    # Calculate bounding box
    min_lon, max_lon = np.min(coords_array[:, 0]), np.max(coords_array[:, 0])
    min_lat, max_lat = np.min(coords_array[:, 1]), np.max(coords_array[:, 1])
    
    # Simple clustering analysis (density-based)
    grid_size = 0.01  # approximately 1km grid
    lon_bins = np.arange(min_lon, max_lon + grid_size, grid_size)
    lat_bins = np.arange(min_lat, max_lat + grid_size, grid_size)
    
    # Count intersections in each grid cell
    hist, _, _ = np.histogram2d(coords_array[:, 0], coords_array[:, 1], bins=[lon_bins, lat_bins])
    
    # Find hotspots (cells with high intersection density)
    hotspot_threshold = np.percentile(hist[hist > 0], 75) if len(hist[hist > 0]) > 0 else 0
    hotspot_count = np.sum(hist >= hotspot_threshold)
    
    return {
        'center_coordinates': {'lon': center_lon, 'lat': center_lat},
        'geographic_spread': {'lon_std': spread_lon, 'lat_std': spread_lat},
        'bounding_box': {
            'min_lon': min_lon, 'max_lon': max_lon,
            'min_lat': min_lat, 'max_lat': max_lat
        },
        'hotspot_analysis': {
            'hotspot_count': int(hotspot_count),
            'max_density': int(np.max(hist)),
            'avg_density': float(np.mean(hist[hist > 0])) if len(hist[hist > 0]) > 0 else 0
        },
        'coverage_area_km2': ((max_lon - min_lon) * 111) * ((max_lat - min_lat) * 111)
    }

def generate_ai_recommendations(analysis_results):
    """Generate intelligent recommendations based on analysis"""
    
    recommendations = []
    
    # Area-based recommendations
    if 'area_types' in analysis_results and analysis_results['area_types']:
        area_data = analysis_results['area_types']
        most_common_areas = area_data.get('most_common', [])
        
        if most_common_areas:
            top_area_type = most_common_areas[0][0]
            top_area_count = most_common_areas[0][1]
            
            
    
    # Severity-based recommendations
    if 'severity_analysis' in analysis_results:
        severity = analysis_results['severity_analysis']
        severity_level = severity.get('severity_level', 'UNKNOWN')
        
        if severity_level == 'CRITICAL':
            recommendations.append({
                'type': 'OPERATIONS',
                'priority': 'CRITICAL',
                'message': "🚨 CRITICAL impact level detected. Recommend comprehensive route planning and stakeholder coordination before operations."
            })
        elif severity_level == 'HIGH':
            recommendations.append({
                'type': 'PLANNING',
                'priority': 'HIGH',
                'message': "⚡ HIGH impact level. Enhanced planning and permits may be required for affected areas."
            })
    
   
    

# File upload
uploaded_file = st.file_uploader("📂 Upload CSV file with road_coordinates", type=["csv"])

# Fixed configuration values
distance_buffer = 100  # Fixed buffer distance in meters

# Main processing button
if uploaded_file is not None:
    if st.button("🚀 **Run Complete Gap Analysis**", type="primary"):
        st.session_state.analysis_completed = False
        
        # Progress container
        progress_container = st.container()
        status_container = st.container()
        
        with progress_container:
            progress_bar = st.progress(0)
            current_status = st.empty()
        
        try:
            # Step 1: Flatten Coordinates
            current_status.info("🔄 Step 1/4: Flattening coordinates...")
            progress_bar.progress(0.1)
            
            st.session_state.flattened_data = flatten_coordinates_from_file(uploaded_file)
            
            if st.session_state.flattened_data is None or len(st.session_state.flattened_data) == 0:
                st.error("❌ No valid coordinate data found in the uploaded file!")
                st.stop()
            
            flattened_count = len(st.session_state.flattened_data)
            current_status.success(f"✅ Step 1 Complete: Flattened {flattened_count} coordinate points")
            progress_bar.progress(0.25)
            
            # Step 2: Convert to GeoJSON
            current_status.info("🗺️ Step 2/4: Converting to GeoJSON LineStrings...")
            
            st.session_state.road_gdf = convert_csv_to_geojson(st.session_state.flattened_data)
            
            if st.session_state.road_gdf is None or len(st.session_state.road_gdf) == 0:
                st.error("❌ Could not create valid GeoJSON LineStrings from coordinate data!")
                st.stop()
            
            roads_count = len(st.session_state.road_gdf)
            current_status.success(f"✅ Step 2 Complete: Created {roads_count} road LineStrings")
            progress_bar.progress(0.5)
            
            # Step 3: Geohash-based Area Detection & Download Restrictions
            current_status.info("🌍 Step 3/4: Auto-detecting area and downloading restrictions...")
            
            # Extract coordinates and create analysis polygon
            coords_data = list(zip(st.session_state.flattened_data['x'], st.session_state.flattened_data['y']))
            analysis_polygon = create_polygon_from_coords(coords_data)
            
            if analysis_polygon is None:
                st.error("❌ Could not create analysis polygon from coordinate data!")
                st.stop()
            
            # Generate geohashes for the area
            unique_geohashes = set()
            sample_coords = coords_data[::max(1, len(coords_data)//50)]  # Max 50 samples
            for lon, lat in sample_coords:
                geohash = generate_geohash(lat, lon, precision=5)
                unique_geohashes.add(geohash)
            
            # Download restrictions
            st.session_state.restricted_areas_gdf = download_restricted_areas(analysis_polygon)
            st.session_state.restricted_roads_gdf = download_restricted_roads(analysis_polygon)
            
            areas_count = len(st.session_state.restricted_areas_gdf) if st.session_state.restricted_areas_gdf is not None else 0
            roads_restricted_count = len(st.session_state.restricted_roads_gdf) if st.session_state.restricted_roads_gdf is not None else 0
            
            current_status.success(f"✅ Step 3 Complete: Found {areas_count} restricted areas, {roads_restricted_count} restricted roads")
            progress_bar.progress(0.75)
            
            # Step 4: Analyze Gap Intersections
            current_status.info("📊 Step 4/4: Analyzing gap intersections...")
            
            if (st.session_state.restricted_areas_gdf is None or len(st.session_state.restricted_areas_gdf) == 0) and \
               (st.session_state.restricted_roads_gdf is None or len(st.session_state.restricted_roads_gdf) == 0):
                st.warning("⚠️ No restricted areas or roads found in the analysis area!")
                st.session_state.final_analysis_result = gpd.GeoDataFrame()
            else:
                st.session_state.final_analysis_result = analyze_gap_intersections(
                    st.session_state.road_gdf,
                    st.session_state.restricted_areas_gdf,
                    st.session_state.restricted_roads_gdf,
                    distance_buffer
                )
            
            intersections_count = len(st.session_state.final_analysis_result) if st.session_state.final_analysis_result is not None else 0
            
            current_status.success(f"✅ Step 4 Complete: Found {intersections_count} intersecting roads")
            progress_bar.progress(0.9)
            
            # Step 5: AI Analysis (Bonus step)
            current_status.info("🤖 Create analysis ...")
            
            st.session_state.ai_analysis_result = analyze_osm_features_with_ai(
                st.session_state.final_analysis_result,
                st.session_state.restricted_areas_gdf,
                st.session_state.restricted_roads_gdf
            )
            
            current_status.success("✅ AI Analysis Complete: Intelligent insights generated")
            progress_bar.progress(1.0)
            
            st.session_state.analysis_completed = True
            
            # Clear progress indicators
            progress_container.empty()
            
        except Exception as e:
            st.error(f"❌ Error during analysis: {e}")
            st.write("Error details:", str(e))
            progress_container.empty()

# Display results if analysis completed
if st.session_state.analysis_completed and st.session_state.final_analysis_result is not None:
    st.success("🎉 **Gap Analysis Completed Successfully!**")
    
    # Analysis Summary
    st.subheader("📊 Analysis Summary")
    
    # Calculate total length of intersecting roads in kilometers
    intersecting_road_length_km = 0
    total_road_length_km = 0
    
    if st.session_state.final_analysis_result is not None and len(st.session_state.final_analysis_result) > 0:
        try:
            intersecting_road_length_km = st.session_state.final_analysis_result.geometry.length.sum() * 111  # Convert to km
        except:
            intersecting_road_length_km = 0
    
    if st.session_state.road_gdf is not None and len(st.session_state.road_gdf) > 0:
        try:
            total_road_length_km = st.session_state.road_gdf.geometry.length.sum() * 111  # Convert to km
        except:
            total_road_length_km = 0
    
    # First row of metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric("🛣️ Total Gap Length", 
                 f"{total_road_length_km:.2f} km")
    with col2:
        # Calculate intersection percentage
        intersection_percentage = 0
        if total_road_length_km > 0:
            intersection_percentage = (intersecting_road_length_km / total_road_length_km) * 100
        
        st.metric("📏 Validated Gap Length", 
                 f"{intersecting_road_length_km:.2f} km",
                 delta=f"{intersection_percentage:.1f}% of total")
        
    
    # Download Results
    if len(st.session_state.final_analysis_result) > 0:
        st.subheader("⬇️ Download Results")
        
        # Use fixed default filename
        final_filename = "gap_analysis_result.geojson"

        buffer = io.BytesIO()
        st.session_state.final_analysis_result.to_file(buffer, driver="GeoJSON")
        buffer.seek(0)

        st.download_button(
            "🎯 Download Gap Analysis Result",
            buffer,
            file_name=final_filename,
            mime="application/geo+json",
            help="Download the intersecting roads as GeoJSON file"
        )
    else:
        st.info("ℹ️ No intersecting roads found in the analysis area.")
    
    # AI Analysis Results Section
    if st.session_state.ai_analysis_result is not None:
        st.divider()
        st.header("🤖 AI-Powered OSM Feature Analysis")
        
        ai_data = st.session_state.ai_analysis_result
        
        # Severity Analysis - Most Important First
        if 'severity_analysis' in ai_data and ai_data['severity_analysis']:
            severity = ai_data['severity_analysis']
            st.subheader(f"{severity.get('severity_color', '🔵')} Impact Severity Analysis")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Severity Level", severity.get('severity_level', 'UNKNOWN'))
                st.metric("Severity Score", f"{severity.get('severity_score', 0):.1f}/100")
            with col2:
                st.metric("Intersection Density", severity.get('intersection_density', 0))
                st.metric("Total Risk Score", severity.get('total_raw_score', 0))
            with col3:
                if severity.get('severity_breakdown'):
                    st.write("**Risk Factors:**")
                    for factor, count in list(severity['severity_breakdown'].items())[:3]:
                        st.write(f"• {factor.title()}: {count}")
        
        # AI Recommendations - Critical Information
        if 'recommendations' in ai_data and ai_data['recommendations']:
            st.subheader("💡 AI-Generated Recommendations")
            
            for i, rec in enumerate(ai_data['recommendations']):
                priority = rec.get('priority', 'LOW')
                rec_type = rec.get('type', 'GENERAL')
                message = rec.get('message', 'No message')
                
                # Color code by priority
                if priority == 'CRITICAL':
                    st.error(f"**{rec_type}**: {message}")
                elif priority == 'HIGH':
                    st.warning(f"**{rec_type}**: {message}")
                else:
                    st.info(f"**{rec_type}**: {message}")
        
        # Detailed Analysis in Expandable Sections
        col1, col2 = st.columns(2)
        
        with col1:
            # Restricted Areas Analysis
            if 'area_types' in ai_data and ai_data['area_types']:
                area_data = ai_data['area_types']
                with st.expander(f"🏢 Restricted Areas Analysis ({area_data.get('total_features', 0)} areas)", expanded=False):
                    
                    if area_data.get('categories'):
                        st.write("**Area Categories:**")
                        for category, count in area_data['categories'].items():
                            percentage = (count / area_data['total_features']) * 100 if area_data['total_features'] > 0 else 0
                            st.write(f"• **{category}**: {count} areas ({percentage:.1f}%)")
                    
                    if area_data.get('total_area_sqm', 0) > 0:
                        total_area_km2 = area_data['total_area_sqm'] / 1000000
                        st.metric("Total Restricted Area", f"{total_area_km2:.2f} km²")
                    
                    if area_data.get('most_common'):
                        st.write("**Top 3 Area Types:**")
                        for i, (category, count) in enumerate(area_data['most_common'], 1):
                            st.write(f"{i}. {category}: {count} areas")
            
            # Geographic Patterns Analysis
            if 'geographic_patterns' in ai_data and ai_data['geographic_patterns']:
                geo_data = ai_data['geographic_patterns']
                with st.expander("📍 Geographic Pattern Analysis", expanded=False):
                    
                    if 'center_coordinates' in geo_data:
                        center = geo_data['center_coordinates']
                        st.write(f"**Analysis Center:** {center['lat']:.4f}, {center['lon']:.4f}")
                    
                    if 'coverage_area_km2' in geo_data:
                        st.metric("Coverage Area", f"{geo_data['coverage_area_km2']:.1f} km²")
                    
                    if 'hotspot_analysis' in geo_data:
                        hotspots = geo_data['hotspot_analysis']
                        st.write("**Density Hotspots:**")
                        st.write(f"• Hotspot Count: {hotspots.get('hotspot_count', 0)}")
                        st.write(f"• Max Density: {hotspots.get('max_density', 0)} intersections/cell")
                        st.write(f"• Avg Density: {hotspots.get('avg_density', 0):.1f} intersections/cell")
        
        with col2:
            # Restricted Roads Analysis
            if 'road_restrictions' in ai_data and ai_data['road_restrictions']:
                road_data = ai_data['road_restrictions']
                with st.expander(f"🛣️ Restricted Roads Analysis ({road_data.get('total_roads', 0)} roads)", expanded=False):
                    
                    if road_data.get('categories'):
                        st.write("**Road Restriction Categories:**")
                        for category, count in road_data['categories'].items():
                            percentage = (count / road_data['total_roads']) * 100 if road_data['total_roads'] > 0 else 0
                            st.write(f"• **{category}**: {count} roads ({percentage:.1f}%)")
                    
                    if road_data.get('total_length_km', 0) > 0:
                        st.metric("Total Restricted Length", f"{road_data['total_length_km']:.2f} km")
                    
                    if road_data.get('most_common'):
                        st.write("**Top 3 Road Restriction Types:**")
                        for i, (category, count) in enumerate(road_data['most_common'], 1):
                            st.write(f"{i}. {category}: {count} roads")
            
            # Feature Details Viewer
            with st.expander("🔍 Detailed Feature Explorer", expanded=False):
                
                analysis_type = st.selectbox("Select Analysis Type:", 
                                           ["Restricted Areas", "Restricted Roads"])
                
                if analysis_type == "Restricted Areas" and 'area_types' in ai_data:
                    area_details = ai_data['area_types'].get('details', {})
                    if area_details:
                        selected_category = st.selectbox("Select Area Category:", 
                                                       list(area_details.keys()))
                        if selected_category and area_details[selected_category]:
                            features = area_details[selected_category][:5]  # Show first 5
                            for i, feature in enumerate(features, 1):
                                st.write(f"**Feature {i}:**")
                                st.write(f"• Type: {feature.get('primary_tag', 'Unknown')}")
                                if feature.get('area_sqm', 0) > 0:
                                    st.write(f"• Area: {feature['area_sqm']/10000:.2f} hectares")
                                st.write("---")
                
                elif analysis_type == "Restricted Roads" and 'road_restrictions' in ai_data:
                    road_details = ai_data['road_restrictions'].get('details', {})
                    if road_details:
                        selected_category = st.selectbox("Select Road Category:", 
                                                       list(road_details.keys()))
                        if selected_category and road_details[selected_category]:
                            roads = road_details[selected_category][:5]  # Show first 5
                            for i, road in enumerate(roads, 1):
                                st.write(f"**Road {i}:**")
                                st.write(f"• Type: {road.get('primary_tag', 'Unknown')}")
                                if road.get('length_km', 0) > 0:
                                    st.write(f"• Length: {road['length_km']:.2f} km")
                                st.write("---")

# Reset button
if st.session_state.analysis_completed:
    if st.button("🔄 Start New Analysis"):
        for var in session_vars:
            st.session_state[var] = None
        st.session_state.analysis_completed = False
        st.rerun()