import streamlit as st
import geopandas as gpd
import pandas as pd
import requests
import json
from shapely.geometry import Polygon
from io import BytesIO

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"

if "result_gdf" not in st.session_state:
    st.session_state["result_gdf"] = None
if "download_ready" not in st.session_state:
    st.session_state["download_ready"] = False


def call_select_dense_geohash_api(
    boundary_data, 
    tag_filters, 
    top_percent=0.5,
    precision=6
):
    """Call the API endpoint for dense geohash selection"""
    try:
        # Prepare the request payload
        payload = {
            "boundary_geojson": boundary_data,
            "tag_filters": tag_filters,
            "top_percent": top_percent,
            "precision": precision
        }
        
        # Make API call
        response = requests.post(
            f"{API_BASE_URL}/geospatial/select-dense-geohash",
            json=payload,
            timeout=300  # 5 minutes timeout for processing
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                # Convert GeoJSON response back to GeoDataFrame
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

# ================================
# STREAMLIT APP UI STARTS HERE
# ================================

st.title("🧭 Select Dense Geohash (Fixed Geohash6)")

st.markdown("""
📍 **Supported boundary formats:**
- Single polygon/area GeoJSON
- FeatureCollection with multiple polygons
- **Geohash GeoJSON** (multiple geohash cells as boundary)
""")

uploaded_file = st.file_uploader("📁 Upload GeoJSON Boundary (supports geohash GeoJSON)", type=["geojson", "json"])
top_percent = 0.5  # Fixed value

default_tags = [
    'shop', 'restaurant', 'fast_food', 'cafe', 'food_court',
    'bakery', 'convenience', 'supermarket', 'marketplace',
    'residential', 'building', 'commercial', 'retail',
    'bank', 'atm', 'clinic', 'pharmacy', 'hospital',
    'school', 'college', 'university',
    'parking', 'taxi', 'car_rental',
    'bus_station', 'bus_stop'
]

if uploaded_file and st.button("🚀 Run Extraction"):
    st.session_state.download_ready = False  # Reset download status
    
    # Read the uploaded GeoJSON file
    try:
        file_content = uploaded_file.getvalue()
        geojson_data = json.loads(file_content.decode('utf-8'))
        
        # Handle different GeoJSON formats
        if geojson_data.get("type") == "FeatureCollection":
            # If it's a FeatureCollection (could be multiple geohash polygons), pass the entire collection
            boundary_data = geojson_data
            st.info(f"📍 Loaded FeatureCollection with {len(geojson_data.get('features', []))} features as boundary")
        elif geojson_data.get("type") == "Feature":
            # If it's a single Feature, pass it as is
            boundary_data = geojson_data
            st.info("📍 Loaded single Feature as boundary")
        else:
            # If it's just a geometry object, wrap it in a Feature
            boundary_data = {
                "type": "Feature",
                "geometry": geojson_data,
                "properties": {}
            }
            st.info("📍 Loaded geometry as boundary")
            
        st.info("📡 Calling API for dense geohash analysis...")
        
        result_gdf = call_select_dense_geohash_api(
            boundary_data,
            tag_filters=default_tags,
            top_percent=top_percent,
            precision=6
        )

        if result_gdf is not None:
            st.session_state.result_gdf = result_gdf
            st.session_state.download_ready = True
            st.success("✅ Geohash padat berhasil diekstrak melalui API.")
            
    except json.JSONDecodeError:
        st.error("❌ Invalid GeoJSON file format.")
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")

# Menampilkan tabel dan tombol download hanya jika sudah ada hasil
if st.session_state.download_ready and st.session_state.result_gdf is not None:
    st.dataframe(st.session_state.result_gdf[['geoHash', 'count']])

    buffer = BytesIO()
    st.session_state.result_gdf.to_file(buffer, driver="GeoJSON")
    buffer.seek(0)

    st.download_button(
        label="💾 Download Selected Geohash (GeoJSON)",
        data=buffer,
        file_name="dense_osm_geohash.geojson",
        mime="application/geo+json"
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