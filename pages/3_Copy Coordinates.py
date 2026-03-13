"""
Copy Coordinates → Polygon → Geohash
Input coordinate (copy-paste), convert to polygon, then convert to geohash.
Sistem sama seperti Draw Polygons, bedanya input dari koordinat bukan gambar.
"""
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Geocoder

import pandas as pd
import re, json
import geohash2
from shapely.geometry import Polygon

from geo_helpers import (
    df_to_geojson,
    geohashes_to_geometry,
    geohash_cells_to_csv,
    geohash_cells_to_geojson_dict,
)

st.set_page_config(page_title="Copy Coordinates → Geohash", layout="wide")

CENTER_FALLBACK = [-6.175337169759785, 106.82713616185086]
EXAMPLE_COORDS = "-6.171046259577523, 106.82269788734317, -6.180712281012674, 106.8225072511238, -6.180295319024069, 106.83230595281657, -6.170894634306194, 106.82952266400855, -6.171046259577523, 106.82269788734317"

# ---------------- Helpers ----------------
VALID_RE = re.compile(r"^[0123456789bcdefghjkmnpqrstuvwxyz]+$")

def parse_coordinates_to_polygon(text: str) -> tuple:
    """
    Parse coordinate string (lat,lon,lat,lon,...) ke polygon.
    Returns: (gdf: GeoDataFrame or None, error_msg: str or None)
    """
    if not text or not text.strip():
        return None, "Masukkan koordinat"
    parts = re.split(r"[\s,;]+", text.strip())
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) < 6:
        return None, "Minimal 3 titik (6 angka) untuk polygon. Format: lat1,lon1,lat2,lon2,..."
    coords = []
    for i in range(0, len(parts) - 1, 2):
        try:
            lat = float(parts[i])
            lon = float(parts[i + 1])
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                coords.append((lon, lat))
            else:
                return None, f"Koordinat di luar jangkauan: ({lat},{lon})"
        except ValueError:
            return None, f"Format tidak valid di posisi {i}: '{parts[i]}'"
    if len(coords) < 3:
        return None, "Minimal 3 titik untuk polygon"
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    try:
        poly = Polygon(coords)
        if not poly.is_valid:
            poly = poly.buffer(0)
        gdf = pd.DataFrame({"name": ["polygon"], "geometry": [poly]})
        return gdf, None
    except Exception as e:
        return None, str(e)

def create_geohash_list(gdf: pd.DataFrame, precision: int, inner: bool = False) -> pd.DataFrame:
    """Convert polygon geometries to geohash list using geohash2."""
    from shapely.geometry import box
    def _geom_to_geohashes(geom):
        if geom is None or geom.is_empty:
            return []
        try:
            bounds = geom.bounds
            minx, miny, maxx, maxy = bounds
            cell_approx = 0.005 / (2 ** (precision - 4))
            step = max(cell_approx / 2, 0.00001)
            unique_gh = set()
            lat = miny
            while lat <= maxy:
                lon = minx
                while lon <= maxx:
                    try:
                        gh = geohash2.encode(lat, lon, precision)
                        if gh in unique_gh:
                            lon += step
                            continue
                        _, _, lat_err, lon_err = geohash2.decode_exactly(gh)
                        gh_box = box(lon - lon_err, lat - lat_err, lon + lon_err, lat + lat_err)
                        if inner:
                            if geom.contains(gh_box.centroid):
                                unique_gh.add(gh)
                        else:
                            if geom.intersects(gh_box):
                                unique_gh.add(gh)
                    except Exception:
                        pass
                    lon += step
                lat += step
            return list(unique_gh)
        except Exception:
            return []
    geohash_lists = gdf["geometry"].apply(_geom_to_geohashes)
    return pd.DataFrame({"geohash_list": geohash_lists})

def normalize_and_validate_series(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().str.lower()
    s = s[s.str.len().between(1, 12)]
    s = s[s.apply(lambda x: bool(VALID_RE.match(x)))]
    return s.dropna()

PRECISION_COLORS = {
    1:"#1f77b4", 2:"#ff7f0e", 3:"#2ca02c", 4:"#d62728",
    5:"#9467bd", 6:"#8c564b", 7:"#e377c2", 8:"#7f7f7f",
    9:"#bcbd22", 10:"#17becf", 11:"#a55194", 12:"#393b79"
}

# ---------------- UI ----------------
st.title("Copy Coordinates → Geohash")
st.caption("Paste koordinat (lat,lon,lat,lon,...), convert menjadi polygon, lalu ke geohash. Sistem sama seperti Draw Polygons.")

# Session state
if "coords_polygon_gdf" not in st.session_state:
    st.session_state.coords_polygon_gdf = None
if "geohash_converted" not in st.session_state:
    st.session_state.geohash_converted = False
if "last_converted_coords" not in st.session_state:
    st.session_state.last_converted_coords = ""

# Precision (sama seperti Draw Polygons)
colA, colB = st.columns(2)
with colA:
    precision = st.selectbox(
        "🎯 Select GeoHash Precision Level",
        options=[5, 6, 7, 8],
        index=1,
        help="Higher precision levels create more detailed (smaller) geohash cells"
    )
with colB:
    precision_info = {5: "~5km × 5km cells", 6: "~1.2km × 1.2km cells", 7: "~150m × 150m cells", 8: "~19m × 19m cells"}
    st.info(f"**Precision Level {precision}:**\n\nCell Size: {precision_info.get(precision, 'Unknown')}\n\nHigher levels = Smaller cells = More detailed")

# Input coordinates
st.subheader("📍 Input Coordinates")
coord_input = st.text_area(
    "Paste koordinat (format: lat1,lon1,lat2,lon2,lat3,lon3,...). Pisah dengan koma atau spasi.",
    value=EXAMPLE_COORDS,
    height=120,
    help="Contoh: -6.17, 106.82, -6.18, 106.82, -6.18, 106.83, -6.17, 106.83"
)

# Parse & validate
gdf_polygon = None
if not coord_input or not coord_input.strip():
    st.session_state.coords_polygon_gdf = None
    st.session_state.geohash_converted = False
elif coord_input:
    gdf_polygon, parse_err = parse_coordinates_to_polygon(coord_input)
    if parse_err:
        st.error(f"❌ {parse_err}")
    else:
        # Reset convert jika koordinat berubah (bandingkan dengan yang tersimpan)
        prev_coords = st.session_state.get("last_converted_coords", "")
        if prev_coords and prev_coords.strip() != coord_input.strip():
            st.session_state.geohash_converted = False
        st.session_state.coords_polygon_gdf = gdf_polygon
        centroid = gdf_polygon.geometry.iloc[0].centroid
        st.success(f"✅ Polygon valid. Centroid: {centroid.y:.6f}, {centroid.x:.6f}")

# Use stored polygon if we have it (e.g. after Convert)
gdf_to_use = st.session_state.coords_polygon_gdf if st.session_state.coords_polygon_gdf is not None else gdf_polygon

# Convert & Clear buttons (sama seperti Draw Polygons)
st.subheader("🔄 Convert")
col_btn, col_clear, _ = st.columns([1, 1, 2])
with col_btn:
    has_polygon = gdf_to_use is not None and not gdf_to_use.empty
    if has_polygon and not st.session_state.geohash_converted:
        if st.button("🔄 Convert to GeoHash", type="primary", use_container_width=True):
            st.session_state.geohash_converted = True
            st.session_state["last_converted_coords"] = coord_input or ""
            st.rerun()
with col_clear:
    if st.button("🗑️ Clear", type="secondary", use_container_width=True):
        st.session_state.coords_polygon_gdf = None
        st.session_state.geohash_converted = False
        st.session_state.pop("last_converted_coords", None)
        st.rerun()

# Build map
m = folium.Map(location=CENTER_FALLBACK, zoom_start=14)
Geocoder(add_marker=True).add_to(m)
for tile in ['OpenStreetMap']:
    folium.TileLayer(tile).add_to(m)

cells_gdf = None
if gdf_to_use is not None and st.session_state.geohash_converted:
    try:
        gh_df = create_geohash_list(gdf_to_use, precision, inner=False)
        flat = gh_df["geohash_list"].explode()
        flat = normalize_and_validate_series(pd.Series(flat)).drop_duplicates().reset_index(drop=True)
        if not flat.empty:
            cells_gdf = geohashes_to_geometry(pd.DataFrame({"geohash": flat}), "geohash")
            cells_gdf["precision"] = cells_gdf["geohash"].astype(str).str.len()
    except Exception as e:
        st.error(f"Gagal membuat geohash: {e}")

# Add polygon layer
if gdf_to_use is not None:
    folium.GeoJson(
        df_to_geojson(gdf_to_use),
        name="Polygon (from coordinates)",
        style_function=lambda x: {"color": "#d62728", "weight": 4, "opacity": 1}
    ).add_to(m)

# Add geohash overlay
if cells_gdf is not None and not cells_gdf.empty:
    def style_fn(feat):
        prec = feat["properties"].get("precision", 6)
        col = PRECISION_COLORS.get(int(prec), "#8c564b")
        return {"color": col, "weight": 2, "opacity": 1, "fillColor": col, "fillOpacity": 0.2}
    folium.GeoJson(
        data=df_to_geojson(cells_gdf),
        name="Geohash Cells",
        tooltip=folium.GeoJsonTooltip(fields=["geohash", "precision"]),
        style_function=style_fn,
        control=True
    ).add_to(m)

folium.LayerControl(position='bottomleft', collapsed=False).add_to(m)

st.subheader("🗺️ Map")
st_folium(m, width=1200, height=700)

# Reset geohash_converted when coordinates change
if gdf_polygon is None and st.session_state.coords_polygon_gdf is not None:
    st.session_state.geohash_converted = False

# Download (sama seperti Draw Polygons)
st.subheader("📥 Download Data")
if gdf_to_use is not None and st.session_state.geohash_converted and cells_gdf is not None:
    st.caption(f"Geohash Level: {precision} | Total Geohash Unique: {len(cells_gdf)}")
    cells_all = cells_gdf.copy()
    col_geo, col_csv = st.columns(2)
    with col_geo:
        geojson_dict = geohash_cells_to_geojson_dict(cells_all)
        geojson_str = json.dumps(geojson_dict, ensure_ascii=False, indent=2)
        st.download_button(
            label="📄 Download GeoHash GeoJSON",
            data=geojson_str,
            file_name=f"coords_geohash_level_{precision}.geojson",
            mime="application/geo+json",
            key="download_coords_geojson"
        )
    with col_csv:
        csv_data = geohash_cells_to_csv(cells_all)
        if csv_data:
            st.download_button(
                label="📊 Download GeoHash CSV",
                data=csv_data,
                file_name=f"coords_geohash_level_{precision}.csv",
                mime="text/csv",
                key="download_coords_csv"
            )
else:
    st.info("Paste koordinat, lalu klik 'Convert to GeoHash' untuk melihat hasil dan download.")
