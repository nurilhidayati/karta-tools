import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Geocoder, MarkerCluster
from newdraw import NewDraw

import geopandas as gpd
import pandas as pd
import re, json, io, zipfile
import geohash2 as geohash
from shapely.geometry import box, Polygon, MultiPolygon

st.set_page_config(page_title="Draw → Geohash (Overlay in One Map)", layout="wide")

# ---------------- Helpers ----------------
VALID_RE = re.compile(r"^[0123456789bcdefghjkmnpqrstuvwxyz]+$")  # geohash base32 (tanpa a/i/l/o)

def normalize_and_validate_series(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().str.lower()
    s = s[s.str.len().between(1, 12)]
    s = s[s.apply(lambda x: bool(VALID_RE.match(x)))]
    return s.dropna()

def make_zip_bytes(inner_filename: str, inner_bytes: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(inner_filename, inner_bytes)
    buf.seek(0)
    return buf.read()

def geohash_to_polygon(gh):
    """Convert geohash to polygon using geohash2"""
    lat, lon, lat_err, lon_err = geohash.decode_exactly(gh)
    return Polygon([
        (lon - lon_err, lat - lat_err),
        (lon - lon_err, lat + lat_err),
        (lon + lon_err, lat + lat_err),
        (lon + lon_err, lat - lat_err),
        (lon - lon_err, lat - lat_err)
    ])

def linestring_to_geohashes(linestring, precision=6, distance_meters=10):
    """
    Generate geohashes along a LineString by sampling points
    
    Parameters:
    - linestring: Shapely LineString geometry
    - precision: geohash precision (1-12)
    - distance_meters: distance between sample points in meters
    
    Returns:
    - Set of geohash strings
    """
    from shapely.geometry import LineString
    geohashes = set()
    
    # Convert to meter projection for accurate distance sampling
    gdf_temp = gpd.GeoDataFrame({'geometry': [linestring]}, crs="EPSG:4326")
    gdf_meters = gdf_temp.to_crs("EPSG:3857")
    line_meters = gdf_meters.iloc[0].geometry
    
    # Get total length
    total_length = line_meters.length
    
    # Sample points along the line
    num_points = max(2, int(total_length / distance_meters))
    
    for i in range(num_points + 1):
        distance = (i / num_points) * total_length
        point_meters = line_meters.interpolate(distance)
        
        # Convert back to lat/lon
        gdf_point = gpd.GeoDataFrame({'geometry': [point_meters]}, crs="EPSG:3857")
        point_latlon = gdf_point.to_crs("EPSG:4326").iloc[0].geometry
        
        # Generate geohash
        gh = geohash.encode(point_latlon.y, point_latlon.x, precision=precision)
        geohashes.add(gh)
    
    return geohashes

def polygon_to_geohashes(polygon, precision=6, inner=False):
    """
    Generate geohashes that cover a polygon completely
    
    Parameters:
    - polygon: Shapely Polygon geometry
    - precision: geohash precision (1-12)
    - inner: if True, only include geohashes fully inside polygon
    
    Returns:
    - Set of geohash strings
    """
    from shapely.geometry import Point
    geohashes = set()
    
    # Get bounds
    minx, miny, maxx, maxy = polygon.bounds
    
    # Calculate step size based on precision (smaller step for denser coverage)
    # Using half of geohash cell size to ensure no gaps
    step_sizes = {
        1: 1.25, 2: 0.315, 3: 0.039, 4: 0.01,
        5: 0.0012, 6: 0.0003, 7: 0.0000375, 8: 0.0000095,
        9: 0.0000012, 10: 0.0000003, 11: 0.0000000375, 12: 0.0000000095
    }
    step = step_sizes.get(precision, 0.0005)
    
    # First pass: sample grid points and generate geohashes
    lat = miny
    while lat <= maxy:
        lon = minx
        while lon <= maxx:
            point = Point(lon, lat)
            
            # Check if point is in polygon
            if polygon.contains(point) or (not inner and polygon.intersects(point)):
                gh = geohash.encode(lat, lon, precision=precision)
                geohashes.add(gh)
            
            lon += step
        lat += step
    
    # Second pass: for non-inner mode, check cells that intersect boundary
    if not inner:
        # Get all unique geohashes from boundary sampling
        boundary_geohashes = set()
        
        # Sample points along polygon boundary
        boundary_length = polygon.boundary.length
        num_boundary_points = max(100, int(boundary_length / (step * 100)))
        
        for i in range(num_boundary_points):
            distance = (i / num_boundary_points) * boundary_length
            point = polygon.boundary.interpolate(distance)
            gh = geohash.encode(point.y, point.x, precision=precision)
            boundary_geohashes.add(gh)
        
        # Add boundary geohashes
        geohashes.update(boundary_geohashes)
        
        # Check geohashes around the polygon for partial intersections
        for gh in list(geohashes):
            gh_poly = geohash_to_polygon(gh)
            # Get neighboring geohashes
            lat_gh, lon_gh = geohash.decode(gh)
            
            # Check 8 neighbors
            for dlat in [-step*2, 0, step*2]:
                for dlon in [-step*2, 0, step*2]:
                    if dlat == 0 and dlon == 0:
                        continue
                    neighbor_gh = geohash.encode(lat_gh + dlat, lon_gh + dlon, precision=precision)
                    if neighbor_gh not in geohashes:
                        neighbor_poly = geohash_to_polygon(neighbor_gh)
                        if polygon.intersects(neighbor_poly):
                            geohashes.add(neighbor_gh)
    
    return geohashes

PRECISION_COLORS = {
    1:"#1f77b4", 2:"#ff7f0e", 3:"#2ca02c", 4:"#d62728",
    5:"#9467bd", 6:"#8c564b", 7:"#e377c2", 8:"#7f7f7f",
    9:"#bcbd22", 10:"#17becf", 11:"#a55194", 12:"#393b79"
}

# CSS for styling
st.markdown("""
    <style>
    /* Main app background */
    .stApp {
        background-color: #F3F6FB;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
    }
    
    /* Text color */
    .stApp, .stApp p, .stApp div, .stApp span, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
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
    
    /* Download button styling */
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
    }
    
    /* Map container */
    .leaflet-container {
        background-color: #FFFFFF !important;
        width: 100% !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------- Sidebar / Controls ----------------
st.title("Draw → Geohash (Overlay in One Map)")

colA, colB = st.columns(2)
with colA:
    precision = st.slider("Precision geohash (1 = sel besar … 12 = sel kecil)", 1, 12, 6, 1)
with colB:
    inner_cover = st.checkbox("Inner coverage (hanya cells yang sepenuhnya di dalam polygon)", value=False)

st.info("ℹ️ **Coverage Mode**: Unchecked = cells yang menyentuh/intersect area | Checked = hanya cells yang 100% di dalam area")

with st.sidebar:
    st.header("Map Overlay Options")
    color_mode = st.selectbox("Warna cells", ["By precision length", "Single color"], index=0)
    base_color = st.color_picker("Warna default (Single color)", "#d62728")
    fill_polygon = st.checkbox("Isi polygon (fill)", value=False)
    weight = st.slider("Garis (weight)", 1, 6, 2)
    opacity = st.slider("Opacity garis", 0.1, 1.0, 1.0, step=0.1)
    fill_opacity = st.slider("Opacity fill", 0.0, 1.0, 0.25, step=0.05)
    max_cells_on_map = st.number_input("Batas cell ditampilkan (agar ringan)", 100, 20000, 5000, 100)
    show_centroids = st.checkbox("Tampilkan centroid markers (cluster)", value=False)
    
    st.header("Polyline Options")
    polyline_sample_distance = st.slider("Jarak sampling polyline (meter)", 5, 100, 10, 5)

    st.header("Export")
    compress_zip = st.checkbox("Compress GeoJSON polygons ke .zip", value=True)

# ---------------- Session state to keep drawings ----------------
if "features_fc" not in st.session_state:
    st.session_state["features_fc"] = {"type": "FeatureCollection", "features": []}

# ---------------- Build ONE Map (with Draw + Overlay) ----------------
m = folium.Map(location=[-6.169689493684541, 106.82936319156342], zoom_start=12, zoom_control=True)

# FeatureGroup untuk gambar (Draw plugin akan menaruh layer di sini)
draw_group = folium.FeatureGroup(name='Drawings', show=True, overlay=True, control=True).add_to(m)

# Jika sudah ada gambar tersimpan dari session_state, tampilkan kembali di group yang sama
if st.session_state["features_fc"]["features"]:
    folium.GeoJson(
        data=st.session_state["features_fc"],
        name="Drawings (saved)",
        tooltip=folium.GeoJsonTooltip(fields=[]),
    ).add_to(draw_group)

# Tambahkan Draw control yang menunjuk ke draw_group
NewDraw(edit_options={'featureGroup': draw_group.get_name()}).add_to(m)

# Geocoder & Tiles
Geocoder(add_marker=True).add_to(m)
for tile in ['CartoDB positron', 'OpenStreetMap', 'CartoDB dark_matter']:
    folium.TileLayer(tile).add_to(m)

# ------ Jika ada gambar tersimpan, hitung cells & overlay di MAP YANG SAMA ------
cells_gdf = None
flat2 = pd.Series([], dtype=str)

if st.session_state["features_fc"]["features"]:
    try:
        # Build GeoDataFrame dari gambar tersimpan
        gdf = gpd.GeoDataFrame.from_features(st.session_state["features_fc"], crs="EPSG:4326")

        # Generate geohash list untuk setiap geometry
        all_geohashes = set()
        for idx, row in gdf.iterrows():
            geom = row.geometry
            geom_type = geom.geom_type
            
            if geom_type == 'LineString':
                # Generate geohashes along the polyline
                gh_set = linestring_to_geohashes(geom, precision, distance_meters=polyline_sample_distance)
                all_geohashes.update(gh_set)
            
            elif geom_type == 'MultiLineString':
                # Handle multiple polylines
                for line in geom.geoms:
                    gh_set = linestring_to_geohashes(line, precision, distance_meters=polyline_sample_distance)
                    all_geohashes.update(gh_set)
            
            elif geom_type == 'Point':
                # Single point - just convert to geohash
                gh = geohash.encode(geom.y, geom.x, precision=precision)
                all_geohashes.add(gh)
            
            elif geom_type == 'MultiPoint':
                # Multiple points
                for point in geom.geoms:
                    gh = geohash.encode(point.y, point.x, precision=precision)
                    all_geohashes.add(gh)
            
            elif geom_type == 'Polygon':
                # Handle polygon normally
                gh_set = polygon_to_geohashes(geom, precision, inner_cover)
                all_geohashes.update(gh_set)
            
            elif geom_type == 'MultiPolygon':
                # Handle MultiPolygon
                for poly in geom.geoms:
                    gh_set = polygon_to_geohashes(poly, precision, inner_cover)
                    all_geohashes.update(gh_set)
            
            else:
                # For any other geometry type, try to convert to polygon
                try:
                    gdf_temp = gpd.GeoDataFrame({'geometry': [geom]}, crs="EPSG:4326")
                    gdf_temp = gdf_temp.to_crs(3857)
                    gdf_temp['geometry'] = gdf_temp['geometry'].buffer(10)
                    poly = gdf_temp.to_crs(4326).iloc[0].geometry
                    gh_set = polygon_to_geohashes(poly, precision, inner_cover)
                    all_geohashes.update(gh_set)
                except:
                    pass

        # Convert to series
        flat2 = pd.Series(list(all_geohashes), dtype=str)
        flat2 = normalize_and_validate_series(flat2).drop_duplicates().reset_index(drop=True)

    except Exception as e:
        st.error(f"Gagal membuat geohash list: {e}")
        flat2 = pd.Series([], dtype=str)

    # Jika ada geohash → buat cell polygons & overlay
    if not flat2.empty:
        try:
            # Create GeoDataFrame with geohash polygons
            geohash_data = []
            for gh in flat2:
                poly = geohash_to_polygon(gh)
                geohash_data.append({
                    'geohash': gh,
                    'precision': len(gh),
                    'geometry': poly
                })
            
            cells_gdf = gpd.GeoDataFrame(geohash_data, crs="EPSG:4326")
            
        except Exception as e:
            st.error(f"Gagal membuat GeoJSON polygon sel geohash: {e}")
            cells_gdf = None

        if cells_gdf is not None and not cells_gdf.empty:
            # Limit jumlah cell yang ditampilkan di peta
            if len(cells_gdf) > max_cells_on_map:
                st.info(f"Preview cell dibatasi {max_cells_on_map} dari {len(cells_gdf)} untuk performa. Unduhan tetap semua data.")
                cells_preview = cells_gdf.iloc[:max_cells_on_map].copy()
            else:
                cells_preview = cells_gdf

            # Style function
            if color_mode == "By precision length":
                def style_fn(feat):
                    prec = feat["properties"].get("precision", 0)
                    col = PRECISION_COLORS.get(int(prec), base_color)
                    return {
                        "color": col,
                        "weight": weight,
                        "opacity": opacity,
                        "fillColor": col,
                        "fillOpacity": fill_opacity if fill_polygon else 0.0,
                    }
                tooltip_fields = ["geohash", "precision"]
            else:
                def style_fn(_):
                    return {
                        "color": base_color,
                        "weight": weight,
                        "opacity": opacity,
                        "fillColor": base_color,
                        "fillOpacity": fill_opacity if fill_polygon else 0.0,
                    }
                tooltip_fields = ["geohash"]

            # Overlay cells di MAP YANG SAMA
            folium.GeoJson(
                data=cells_preview.to_json(),
                name="Geohash Cells",
                tooltip=folium.GeoJsonTooltip(fields=tooltip_fields),
                style_function=style_fn,
                control=True,
                embed=False,
                zoom_on_click=False,
                highlight_function=lambda _: {"weight": weight + 1},
            ).add_to(m)

            # Opsional: centroid markers (cluster)
            if show_centroids:
                mc = MarkerCluster(name="Geohash Centroids")
                for _, row in cells_preview.iterrows():
                    c = row.geometry.centroid
                    folium.Marker(
                        location=[c.y, c.x],
                        tooltip=f"geohash: {row['geohash']} | precision: {row['precision']}",
                        icon=folium.Icon(color="blue", icon="info-sign"),
                    ).add_to(mc)
                mc.add_to(m)

# Layer control
folium.LayerControl(position='bottomleft', collapsed=False).add_to(m)

# ---------------- Render ONE MAP (draw + overlay) ----------------
st.subheader("Gambar area & lihat overlay cells pada peta yang sama")
st.caption("✏️ **Polygon/Rectangle/Circle**: Seluruh area akan diisi penuh dengan geohash cells")
st.caption("✏️ **Polyline**: Geohash cells sepanjang garis yang digambar")
st.caption("⚠️ **PENTING untuk Polyline**: Selesaikan dengan **DOUBLE-CLICK** pada titik terakhir. Jangan klik titik awal (akan jadi polygon)!")
st.caption("🔄 Setiap selesai menggambar, aplikasi otomatis rerun → overlay cells diperbarui di map ini.")
st_map = st_folium(
    m,
    width=1200, height=700,
    returned_objects=['last_object_clicked', 'all_drawings', 'last_active_drawing'],
    feature_group_to_add=draw_group,
    key="one_map"
)

# ---------------- Update session_state dengan gambar terbaru ----------------
def extract_features(st_data_obj):
    feats = []
    if isinstance(st_data_obj, dict):
        ad = st_data_obj.get("all_drawings")
        if isinstance(ad, list):
            feats = ad
        elif isinstance(ad, dict):
            if ad.get("type") == "FeatureCollection":
                feats = ad.get("features", [])
            elif ad:
                feats = [ad]
    elif isinstance(st_data_obj, list):
        feats = st_data_obj
    return {"type": "FeatureCollection", "features": feats}

fc_new = extract_features(st_map)
# Hanya update jika ada fitur
if fc_new["features"]:
    st.session_state["features_fc"] = fc_new

# ---------------- Panel hasil & unduhan ----------------
st.subheader("Hasil & Unduhan")
if st.session_state["features_fc"]["features"] and not flat2.empty:
    st.caption(f"Precision: {precision} | Total geohash unik: {len(flat2)} | Inner: {inner_cover}")
    joined_comma = ",".join(flat2.tolist())
    st.text_area("Salin geohash (comma-separated, no space):", joined_comma, height=120)

    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # TXT (comma)
        st.download_button("⬇️ TXT (comma)", joined_comma.encode("utf-8"), "geohash_list.txt", "text/plain")
    
    with col2:
        # JSON array
        st.download_button("⬇️ JSON array", json.dumps(flat2.tolist()).encode("utf-8"), "geohash_list.json", "application/json")
    
    with col3:
        # TXT (newline)
        st.download_button("⬇️ TXT (newline)", "\n".join(flat2.tolist()).encode("utf-8"), "geohash_list_lines.txt", "text/plain")
    
    with col4:
        # CSV
        st.download_button("⬇️ CSV", flat2.to_frame("geohash").to_csv(index=False).encode("utf-8"), "geohash_list.csv", "text/csv")

    # GeoJSON polygons (ALL)
    if cells_gdf is not None and not cells_gdf.empty:
        st.write("")  # Spacing
        col5, col6 = st.columns(2)
        
        with col5:
            geojson_bytes = cells_gdf.to_json().encode("utf-8")
            if compress_zip:
                st.download_button(
                    "⬇️ GeoJSON polygons (ZIP)",
                    make_zip_bytes("geohash_polygons.geojson", geojson_bytes),
                    "geohash_polygons.zip",
                    "application/zip"
                )
            else:
                st.download_button(
                    "⬇️ GeoJSON polygons",
                    geojson_bytes,
                    "geohash_polygons.geojson",
                    "application/geo+json"
                )
else:
    st.info("Belum ada gambar untuk dihitung/diunduh. Gunakan tools gambar di peta untuk memulai.")

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
