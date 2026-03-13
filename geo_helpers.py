"""
Lightweight geo utilities replacing geopandas for Streamlit Cloud compatibility.
Uses shapely, pyproj, geojson - no geopandas/fiona/GDAL.
"""
import json
import pandas as pd
import geohash2
from shapely.geometry import shape, mapping, box
from shapely.ops import transform
from pyproj import Transformer


def features_to_gdf(feature_collection: dict):
    """Convert GeoJSON FeatureCollection to pandas DataFrame with geometry column (shapely)."""
    features = feature_collection.get("features", [])
    if not features:
        return pd.DataFrame(columns=["geometry"])

    geoms = []
    for f in features:
        geom = f.get("geometry")
        if geom:
            try:
                geoms.append(shape(geom))
            except Exception:
                geoms.append(None)
        else:
            geoms.append(None)

    return pd.DataFrame({"geometry": geoms}).dropna(subset=["geometry"], how="all")


def transform_crs(df: pd.DataFrame, from_crs: str = "EPSG:4326", to_crs: str = "EPSG:3857") -> pd.DataFrame:
    """Transform geometries in dataframe from one CRS to another."""
    transformer = Transformer.from_crs(from_crs, to_crs, always_xy=True)

    def _transform(geom):
        if geom is None or geom.is_empty:
            return geom
        return transform(
            lambda x, y: transformer.transform(x, y),
            geom
        )

    out = df.copy()
    out["geometry"] = out["geometry"].apply(_transform)
    return out


def df_to_geojson(df: pd.DataFrame) -> str:
    """Convert DataFrame with geometry column (shapely) to GeoJSON string for folium."""
    if df is None or df.empty or "geometry" not in df.columns:
        return json.dumps({"type": "FeatureCollection", "features": []})

    features = []
    for _, row in df.iterrows():
        geom = row["geometry"]
        if geom is None or geom.is_empty:
            continue
        props = {k: v for k, v in row.items() if k != "geometry" and pd.notna(v)}
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": mapping(geom)
        })
    return json.dumps({"type": "FeatureCollection", "features": features})


def geom_to_geojson_geom(geom) -> dict:
    """Convert shapely geometry to GeoJSON geometry dict."""
    if geom is None or geom.is_empty:
        return {"type": "Point", "coordinates": [0, 0]}
    return mapping(geom)


def ensure_polygons(df: pd.DataFrame) -> pd.DataFrame:
    """Convert non-polygon geometries (Point, LineString) to polygon via buffer. Returns copy."""
    if df is None or df.empty:
        return df
    geom_types = df["geometry"].apply(lambda g: g.geom_type if g else "")
    non_poly = ~geom_types.isin(["Polygon", "MultiPolygon"])
    if not non_poly.any():
        return df.copy()
    # Transform to meters, buffer 5m, transform back
    df_3857 = transform_crs(df, "EPSG:4326", "EPSG:3857")
    for idx in df_3857.index:
        if non_poly.loc[idx]:
            g = df_3857.loc[idx, "geometry"]
            if g and not g.is_empty:
                df_3857.loc[idx, "geometry"] = g.buffer(5)
    return transform_crs(df_3857, "EPSG:3857", "EPSG:4326")


def geohashes_to_geometry(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """Convert geohash strings to polygon geometries using geohash2."""
    import geohash2
    from shapely.geometry import box

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


def geohash_cells_to_csv(df: pd.DataFrame) -> str:
    """Convert geohash DataFrame to CSV format (geohash, lat, lon)."""
    if df is None or df.empty or "geometry" not in df.columns:
        return ""
    rows = []
    for _, row in df.iterrows():
        geom = row["geometry"]
        if geom is None or geom.is_empty:
            continue
        cent = geom.centroid
        rows.append({
            "geohash": row.get("geohash", ""),
            "lat": round(cent.y, 6),
            "lon": round(cent.x, 6)
        })
    return pd.DataFrame(rows).to_csv(index=False)


def geohash_cells_to_geojson_dict(df: pd.DataFrame) -> dict:
    """Convert geohash DataFrame to GeoJSON dict."""
    if df is None or df.empty or "geometry" not in df.columns:
        return {"type": "FeatureCollection", "features": []}
    features = []
    for _, row in df.iterrows():
        geom = row["geometry"]
        if geom is None or geom.is_empty:
            continue
        cent = geom.centroid
        feat = {
            "type": "Feature",
            "properties": {
                "geoHash": str(row.get("geohash", "")),
                "center_lat": round(cent.y, 6),
                "center_lon": round(cent.x, 6),
                "precision": int(row.get("precision", len(str(row.get("geohash", "")))))
            },
            "geometry": mapping(geom)
        }
        features.append(feat)
    return {"type": "FeatureCollection", "features": features}
