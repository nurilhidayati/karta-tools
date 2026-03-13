import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Geocoder, MarkerCluster, Draw

import geopandas as gpd
import pandas as pd
import re, json, io, zipfile
import geohash2
from shapely.geometry import box

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

def create_geohash_list(gdf: gpd.GeoDataFrame, precision: int, inner: bool = False) -> pd.DataFrame:
    """Convert polygon geometries to geohash list using geohash2 (no polygeohasher)."""
    def _geom_to_geohashes(geom):
        if geom is None or geom.is_empty:
            return []
        try:
            bounds = geom.bounds
            minx, miny, maxx, maxy = bounds
            # Approx cell size per precision: level 6 ~0.002 deg, level 7 ~0.0005, level 8 ~0.00006
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
    geohash_lists = gdf.geometry.apply(_geom_to_geohashes)
    return pd.DataFrame({"geohash_list": geohash_lists})

def geohashes_to_geometry(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """Convert geohash strings to polygon geometries using geohash2."""
    def _gh_to_polygon(gh: str):
        try:
            lat, lon, lat_err, lon_err = geohash2.decode_exactly(gh)
            return box(lon - lon_err, lat - lat_err, lon + lon_err, lat + lat_err)
        except Exception:
            return None
    geometries = df[column_name].astype(str).apply(_gh_to_polygon)
    valid = geometries.notna()
    out = df[valid].copy().reset_index(drop=True)
    out["geometry"] = geometries[valid].values
    return out

def geohash_cells_to_csv(cells_gdf: gpd.GeoDataFrame) -> str:
    """Convert geohash GeoDataFrame to CSV format (geohash, lat, lon) seperti 3_Tools_Add_On."""
    if cells_gdf is None or cells_gdf.empty:
        return ""
    rows = []
    for _, row in cells_gdf.iterrows():
        cent = row.geometry.centroid
        rows.append({
            "geohash": row.get("geohash", ""),
            "lat": round(cent.y, 6),
            "lon": round(cent.x, 6)
        })
    return pd.DataFrame(rows).to_csv(index=False)

def geohash_cells_to_geojson_dict(cells_gdf: gpd.GeoDataFrame) -> dict:
    """Convert geohash GeoDataFrame to GeoJSON dict (compatibel dengan 3_Tools_Add_On format)."""
    if cells_gdf is None or cells_gdf.empty:
        return {"type": "FeatureCollection", "features": []}
    features = []
    for _, row in cells_gdf.iterrows():
        cent = row.geometry.centroid
        feat = {
            "type": "Feature",
            "properties": {
                "geoHash": str(row.get("geohash", "")),
                "center_lat": round(cent.y, 6),
                "center_lon": round(cent.x, 6),
                "precision": int(row.get("precision", len(str(row.get("geohash", "")))))
            },
            "geometry": json.loads(gpd.GeoSeries([row.geometry]).to_json())["features"][0]["geometry"]
        }
        features.append(feat)
    return {"type": "FeatureCollection", "features": features}

PRECISION_COLORS = {
    1:"#1f77b4", 2:"#ff7f0e", 3:"#2ca02c", 4:"#d62728",
    5:"#9467bd", 6:"#8c564b", 7:"#e377c2", 8:"#7f7f7f",
    9:"#bcbd22", 10:"#17becf", 11:"#a55194", 12:"#393b79"
}

# ---------------- Sidebar / Controls ----------------
st.title("Draw Polygons")

# Precision & conversion settings (seperti 3_Tools_Add_On)
if "precision_level" not in st.session_state:
    st.session_state.precision_level = 6

colA, colB = st.columns(2)
with colA:
    precision = st.selectbox(
        "🎯 Select GeoHash Precision Level",
        options=[5, 6, 7, 8],
        index=1,  # Default level 6
        help="Higher precision levels create more detailed (smaller) geohash cells"
    )
    st.session_state.precision_level = precision
with colB:
    precision_info = {
        5: "~5km × 5km cells",
        6: "~1.2km × 1.2km cells",
        7: "~150m × 150m cells",
        8: "~19m × 19m cells"
    }
    cell_size = precision_info.get(precision, "Unknown")
    st.info(f"""
    **Precision Level {precision}:**

    Cell Size: {cell_size}
    """)

# Default values (inner_cover = False, Map Overlay Options removed)
inner_cover = False
color_mode = "By precision length"
base_color = "#d62728"
fill_polygon = False
weight = 2
opacity = 1.0
fill_opacity = 0.25
max_cells_on_map = 5000
show_centroids = False
compress_zip = True

# ---------------- Session state to keep drawings ----------------
# Kita simpan FeatureCollection hasil gambar di session_state supaya
# di render map berikutnya dapat ditampilkan lagi dan dihitung cell-nya.
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
        tooltip=folium.GeoJsonTooltip(fields=[]),  # sesuaikan jika ada properti
    ).add_to(draw_group)

# Tambahkan Draw control (folium built-in, no newdraw dependency)
Draw(export=False).add_to(m)

# Geocoder & Tiles
Geocoder(add_marker=True).add_to(m)
for tile in ['OpenStreetMap']:
    folium.TileLayer(tile).add_to(m)

# ------ Jika ada gambar tersimpan, hitung cells & overlay di MAP YANG SAMA ------
cells_gdf = None
if st.session_state["features_fc"]["features"]:
    # Build GeoDataFrame dari gambar tersimpan
    gdf = gpd.GeoDataFrame.from_features(st.session_state["features_fc"], crs="EPSG:4326")

    # Pastikan polygon: LineString/Point → buffer kecil (5 m)
    non_poly = ~gdf.geom_type.isin(["Polygon", "MultiPolygon"])
    if non_poly.any():
        gdf_poly = gdf.to_crs(3857)
        gdf_poly.loc[non_poly, "geometry"] = gdf_poly.loc[non_poly, "geometry"].buffer(5)  # 5 meter
        gdf_poly = gdf_poly.to_crs(4326)
    else:
        gdf_poly = gdf

    # Generate geohash list dari gambar tersimpan
    try:
        gh_df = create_geohash_list(gdf_poly, precision, inner=inner_cover)
        list_col = "geohash_list" if "geohash_list" in gh_df.columns else ("geohash" if "geohash" in gh_df.columns else None)
        if list_col:
            flat = gh_df[list_col].explode() if list_col == "geohash_list" else gh_df[list_col]
            flat = normalize_and_validate_series(pd.Series(flat)).drop_duplicates().reset_index(drop=True)
        else:
            flat = pd.Series([], dtype=str)
    except Exception as e:
        st.error(f"Gagal membuat geohash list: {e}")
        flat = pd.Series([], dtype=str)

    # Jika ada geohash → buat cell polygons & overlay
    if not flat.empty:
        try:
            cells_gdf = geohashes_to_geometry(pd.DataFrame({"geohash": flat}), "geohash")
            cells_gdf = gpd.GeoDataFrame(cells_gdf, geometry=cells_gdf["geometry"], crs="EPSG:4326")
            cells_gdf["precision"] = cells_gdf["geohash"].astype(str).str.len()
        except Exception as e:
            st.error(f"Gagal membuat GeoJSON polygon sel geohash: {e}")
            cells_gdf = None

        if cells_gdf is not None and not cells_gdf.empty:
            # Limit jumlah cell yang ditampilkan di peta (unduhan tetap semua)
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
st.caption("Setiap selesai menggambar, aplikasi otomatis rerun → overlay cells diperbarui di map ini.")
st_map = st_folium(
    m,
    width=1200, height=700,
    returned_objects=['last_object_clicked', 'all_drawings', 'last_active_drawing'],
    feature_group_to_add=draw_group,
    key="one_map"
)

# ---------------- Update session_state dengan gambar terbaru ----------------
# Normalisasi keluaran st_folium ke FeatureCollection dan simpan ke session_state
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
# Hanya update jika ada fitur (mencegah mengosongkan saat interaksi lain)
if fc_new["features"]:
    st.session_state["features_fc"] = fc_new

# ---------------- Panel hasil & unduhan ----------------
st.subheader("Download Data")
if st.session_state["features_fc"]["features"]:
    # Hitung ulang daftar geohash dari gambar tersimpan (konsisten dengan overlay)
    gdf_saved = gpd.GeoDataFrame.from_features(st.session_state["features_fc"], crs="EPSG:4326")
    non_poly = ~gdf_saved.geom_type.isin(["Polygon", "MultiPolygon"])
    if non_poly.any():
        gdf_saved = gdf_saved.to_crs(3857)
        gdf_saved.loc[non_poly, "geometry"] = gdf_saved.loc[non_poly, "geometry"].buffer(5)
        gdf_saved = gdf_saved.to_crs(4326)

    try:
        gh_df2 = create_geohash_list(gdf_saved, precision, inner=inner_cover)
        list_col2 = "geohash_list" if "geohash_list" in gh_df2.columns else ("geohash" if "geohash" in gh_df2.columns else None)
        if list_col2:
            flat2 = gh_df2[list_col2].explode() if list_col2 == "geohash_list" else gh_df2[list_col2]
            flat2 = normalize_and_validate_series(pd.Series(flat2)).drop_duplicates().reset_index(drop=True)
        else:
            flat2 = pd.Series([], dtype=str)
    except Exception as e:
        st.error(f"Gagal membuat geohash list: {e}")
        flat2 = pd.Series([], dtype=str)

    st.caption(f"Geohash Level: {precision} | Total Geohash Unique: {len(flat2)}")
    joined_comma = ",".join(flat2.tolist())

    # Build cells_all untuk export GeoJSON & CSV (format seperti 3_Tools_Add_On)

    cells_all = geohashes_to_geometry(pd.DataFrame({"geohash": flat2}), "geohash")
    cells_all = gpd.GeoDataFrame(cells_all, geometry=cells_all["geometry"], crs="EPSG:4326")
    cells_all["precision"] = cells_all["geohash"].astype(str).str.len()

    col_geo, col_csv = st.columns(2)

    with col_geo:
        geojson_dict = geohash_cells_to_geojson_dict(cells_all)
        geojson_str = json.dumps(geojson_dict, ensure_ascii=False, indent=2)
        filename_geojson = f"draw_geohash_level_{precision}.geojson"
        st.download_button(
                label="📄 Download GeoHash GeoJSON",
                data=geojson_str,
                file_name=filename_geojson,
                mime="application/geo+json",
                key="download_draw_geojson"
            )

    with col_csv:
        csv_data = geohash_cells_to_csv(cells_all)
        if csv_data:
            filename_csv = f"draw_geohash_level_{precision}.csv"
            st.download_button(
                    label="📊 Download GeoHash CSV",
                    data=csv_data,
                    file_name=filename_csv,
                    mime="text/csv",
                    key="download_draw_csv"
                )
        else:
            st.warning("Tidak ada data untuk CSV")

      