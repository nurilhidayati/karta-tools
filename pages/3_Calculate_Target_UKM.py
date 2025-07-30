import streamlit as st
import pandas as pd
import geopandas as gpd
import io
import requests
import json
from config import settings

st.set_page_config(page_title="🛣️ Calculate Target UKM", layout="wide")
st.title("🛣️ Calculate Target UKM")

# Set default processing parameters (no sidebar UI)
use_advanced = True
chunk_size = 15
max_workers = 10
use_cache = False  # Disabled by default as requested
return_geojson = True  # Changed back to True to enable roads download

uploaded_file = st.file_uploader("📄 Upload GeoJSON or CSV with `geoHash` column", type=["csv", "geojson", "json"])

# Reset hasil roads saat tombol calculate ditekan
if 'ukm_result' not in st.session_state:
    st.session_state['ukm_result'] = None

def call_backend_calculate_ukm_advanced(geohashes, chunk_size=15, max_workers=10, use_cache=True, return_geojson=True):
    """Call FastAPI backend to calculate UKM with advanced options"""
    try:
        # Prepare API endpoint URL
        api_url = f"http://{settings.API_HOST}:{settings.API_PORT}/api/v1/geospatial/calculate-target-ukm-advanced"
        
        # Prepare request payload
        payload = {
            "geohashes": geohashes,
            "chunk_size": chunk_size,
            "max_workers": max_workers,
            "use_cache": use_cache,
            "return_geojson": return_geojson,
            "background_task": False
        }
        
        # Make API call
        response = requests.post(api_url, json=payload, timeout=300)  # 5 min timeout
        
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

def call_backend_calculate_ukm_basic(geohashes):
    """Call FastAPI backend to calculate UKM with basic options"""
    try:
        # Prepare API endpoint URL
        api_url = f"http://{settings.API_HOST}:{settings.API_PORT}/api/v1/geospatial/calculate-target-ukm"
        
        # Prepare request payload
        payload = {"geohashes": geohashes}
        
        # Make API call
        response = requests.post(api_url, json=payload, timeout=300)  # 5 min timeout
        
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

if uploaded_file and st.button("🗂️ Calculate UKM"):
    st.session_state['ukm_result'] = None  # reset saat tombol calculate ditekan
    
    try:
        filename = uploaded_file.name.lower()
        if filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif filename.endswith((".geojson", ".json")):
            gdf = gpd.read_file(uploaded_file)
            if 'geoHash' not in gdf.columns:
                st.error("❌ GeoJSON must contain a 'geoHash' property.")
                st.stop()
            df = pd.DataFrame(gdf.drop(columns='geometry', errors='ignore'))
        else:
            st.error("❌ Unsupported file type.")
            st.stop()

        if 'geoHash' not in df.columns:
            st.error("❌ File must contain a column named 'geoHash'")
        else:
            geohash_list = df['geoHash'].dropna().astype(str).str.strip()
            geohash_list = geohash_list[geohash_list.str.len() == 6].unique().tolist()

            if not geohash_list:
                st.warning("⚠️ No valid 6-character geohashes found.")
            else:
                st.info(f"🚀 Processing {len(geohash_list)} geohash6 areas using FastAPI backend...")
                
                # Show progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                status_text.text("📡 Sending request to backend...")
                
                progress_bar.progress(10)
                
                # Call advanced backend API with optimized settings
                result = call_backend_calculate_ukm_advanced(
                    geohash_list, chunk_size, max_workers, use_cache, return_geojson
                )
                
                progress_bar.progress(90)
                
                if result and result.get('success'):
                    progress_bar.progress(100)
                    status_text.text("✅ Calculation completed!")
                    
                    # Display results
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("🛣️ Road Segments", result['total_road_segments'])
                        st.metric("✅ Processed", result['processed_geohashes'])
                    
                    with col2:
                        st.metric("📏 Total Length", f"{result['total_road_length_km']:.2f} km")
                        st.metric("❌ Failed", result['failed_geohashes'])
                    
                    with col3:
                        if 'processing_time_seconds' in result:
                            st.metric("⏱️ Processing Time", f"{result['processing_time_seconds']}s")
                        st.metric("📊 Total Geohashes", len(geohash_list))
                    
                    # Store result for download
                    st.session_state['ukm_result'] = result
                    
                    # Clear progress indicators
                    progress_bar.empty()
                    status_text.empty()
                else:
                    progress_bar.empty()
                    status_text.empty()
                    if result:
                        st.warning("⚠️ No roads found in the specified geohashes.")
                    else:
                        st.error("❌ Failed to calculate UKM. Please check backend connectivity.")

    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")

# Tombol download muncul hanya jika sudah ada hasil
if st.session_state['ukm_result'] is not None and st.session_state['ukm_result'].get('roads_geojson'):
    roads_geojson = st.session_state['ukm_result']['roads_geojson']
    
    # Convert to string for download
    geojson_str = json.dumps(roads_geojson, indent=2)
    
    st.download_button(
        "⬇️ Download Roads GeoJSON",
        geojson_str,
        "roads_inside_geohash.geojson",
        "application/geo+json"
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
