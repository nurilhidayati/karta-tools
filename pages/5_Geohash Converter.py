# app.py
import streamlit as st
import pandas as pd
import geohash2
from shapely.geometry import Polygon
import geopandas as gpd
from io import StringIO
import tempfile
import zipfile
import os

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

st.title("CSV to GeoJSON Converter")
st.markdown("Upload one or more CSV files containing a `geoHash` column. Each file will be converted to a GeoJSON with polygons.")

uploaded_files = st.file_uploader("📄 Upload CSV files", type="csv", accept_multiple_files=True)

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
                mime="application/geo+json"
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
                mime="application/zip"
            )


st.title("GeoJSON to CSV Converter")
st.markdown("Upload one or more GeoJSON files. Each file will be converted to a CSV with geometry coordinates.")

uploaded_files = st.file_uploader("📄 Upload GeoJSON files", type="geojson", accept_multiple_files=True)

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
                mime="text/csv"
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
                mime="application/zip"
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
