from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json
import logging
import uuid
import time
import pandas as pd
from datetime import datetime
import geopandas as gpd
import osmnx as ox
import geohash2
from shapely.geometry import Polygon
from collections import Counter
import io
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import numpy as np
from functools import lru_cache
import hashlib

from api.database.connection import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/geospatial", tags=["geospatial"])

# Enhanced caching system
osm_cache_with_ttl = {}
CACHE_TTL = 3600  # 1 hour cache

def is_cache_valid(cache_entry):
    """Check if cache entry is still valid"""
    return time.time() - cache_entry['timestamp'] < CACHE_TTL

def get_from_cache(cache_key):
    """Get data from cache if valid"""
    if cache_key in osm_cache_with_ttl:
        if is_cache_valid(osm_cache_with_ttl[cache_key]):
            return osm_cache_with_ttl[cache_key]['data']
        else:
            # Remove expired cache
            del osm_cache_with_ttl[cache_key]
    return None

def save_to_cache(cache_key, data):
    """Save data to cache with timestamp"""
    osm_cache_with_ttl[cache_key] = {
        'data': data,
        'timestamp': time.time()
    }

# Pydantic models for request/response
class BoundaryToGeohashRequest(BaseModel):
    boundary_geojson: Dict[str, Any]
    precision: int = Field(default=6, ge=5, le=7)

class ExtractGeojsonRequest(BaseModel):
    boundary_data: Dict[str, Any]

class GeohashToCsvRequest(BaseModel):
    geohashes_geojson: Dict[str, Any]

class GetBoundsRequest(BaseModel):
    geojson: Dict[str, Any]

class CalculateTargetUkmRequest(BaseModel):
    geohashes: List[str]

class CalculateTargetUkmResponse(BaseModel):
    success: bool
    total_road_segments: int
    total_road_length_km: float
    processed_geohashes: int
    failed_geohashes: int
    roads_geojson: Optional[Dict[str, Any]] = None

class CalculateTargetUkmAdvancedRequest(BaseModel):
    geohashes: List[str]
    chunk_size: int = Field(default=10, ge=5, le=50)
    max_workers: int = Field(default=8, ge=2, le=16)
    use_cache: bool = Field(default=False)
    return_geojson: bool = Field(default=True)
    background_task: bool = Field(default=False)

class CalculateTargetUkmAdvancedResponse(BaseModel):
    success: bool
    total_road_segments: int
    total_road_length_km: float
    processed_geohashes: int
    failed_geohashes: int
    processing_time_seconds: float
    cache_hits: int
    cache_misses: int
    roads_geojson: Optional[Dict[str, Any]] = None
    task_id: Optional[str] = None  # For background tasks
    
class CompleteAnalysisRequest(BaseModel):
    boundary_geojson: Dict[str, Any]
    tag_filters: List[str] = ["building", "commercial"]
    top_percent: float = Field(default=0.5, ge=0.1, le=1.0)
    precision: int = Field(default=6, ge=5, le=7)
    include_initial_geohash: bool = False
    analysis_name: str = "Complete Analysis"

class SelectDenseGeohashRequest(BaseModel):
    boundary_geojson: Dict[str, Any]
    tag_filters: List[str] = Field(default=[
        'shop', 'restaurant', 'fast_food', 'cafe', 'food_court',
        'bakery', 'convenience', 'supermarket', 'marketplace',
        'residential', 'building', 'commercial', 'retail',
        'bank', 'atm', 'clinic', 'pharmacy', 'hospital',
        'school', 'college', 'university',
        'parking', 'taxi', 'car_rental',
        'bus_station', 'bus_stop'
    ])
    top_percent: float = Field(default=0.5, ge=0.1, le=1.0)
    precision: int = Field(default=6, ge=5, le=7)

class AnalysisResponse(BaseModel):
    id: str
    status: str
    message: str

class AnalysisStatusResponse(BaseModel):
    id: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None

# In-memory storage for analysis results (in production, use database)
analysis_storage = {}

# Cache for OSM data to avoid repeated requests for same areas
osm_cache = {}

@lru_cache(maxsize=1000)
def cached_geohash_encode(lat: float, lon: float, precision: int) -> str:
    """Cached geohash encoding for better performance"""
    return geohash2.encode(lat, lon, precision=precision)

@lru_cache(maxsize=1000) 
def cached_geohash_to_polygon(geohash_str: str):
    """Cached geohash to polygon conversion"""
    lat, lon, lat_err, lon_err = geohash2.decode_exactly(geohash_str)
    return Polygon([
        (lon - lon_err, lat - lat_err),
        (lon - lon_err, lat + lat_err),
        (lon + lon_err, lat + lat_err),
        (lon + lon_err, lat - lat_err),
        (lon - lon_err, lat - lat_err)
    ])

def encode_geohash_batch(geometries, precision):
    """Vectorized geohash encoding for better performance"""
    geohashes = []
    for geom in geometries:
        try:
            if geom.is_empty:
                geohashes.append(None)
                continue
            if geom.geom_type == 'Point':
                point = geom
            else:
                point = geom.representative_point()
            geohashes.append(cached_geohash_encode(point.y, point.x, precision))
        except:
            geohashes.append(None)
    return geohashes

def get_cache_key(polygon_wkt: str, tags: list) -> str:
    """Generate cache key for OSM data"""
    tags_str = ','.join(sorted(tags))
    combined = f"{polygon_wkt}_{tags_str}"
    return hashlib.md5(combined.encode()).hexdigest()

async def fetch_osm_data_parallel(polygon, poi_tags, road_tags):
    """Fetch POI and road data in parallel"""
    loop = asyncio.get_event_loop()
    
    # Check cache first
    polygon_wkt = polygon.wkt
    poi_cache_key = get_cache_key(polygon_wkt, list(poi_tags.keys()))
    road_cache_key = get_cache_key(polygon_wkt, list(road_tags.keys()))
    
    # Use ThreadPoolExecutor for OSM requests (I/O bound)
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit tasks
        poi_future = None
        road_future = None
        
        if poi_cache_key not in osm_cache:
            poi_future = loop.run_in_executor(executor, fetch_poi_data, polygon, poi_tags)
        
        if road_cache_key not in osm_cache:
            road_future = loop.run_in_executor(executor, fetch_road_data, polygon, road_tags)
        
        # Get results
        if poi_future:
            poi_gdf = await poi_future
            osm_cache[poi_cache_key] = poi_gdf
        else:
            poi_gdf = osm_cache[poi_cache_key]
            
        if road_future:
            roads_gdf = await road_future
            osm_cache[road_cache_key] = roads_gdf
        else:
            roads_gdf = osm_cache[road_cache_key]
    
    return poi_gdf, roads_gdf

def fetch_poi_data(polygon, tags_dict):
    """Fetch POI data from OSM"""
    try:
        poi_gdf = ox.geometries_from_polygon(polygon, tags=tags_dict)
        poi_gdf = poi_gdf[poi_gdf.geometry.type.isin(['Point', 'Polygon', 'MultiPolygon'])]
        return poi_gdf.to_crs("EPSG:4326")
    except Exception as e:
        logger.warning(f"⚠️ Failed to fetch POI: {e}")
        return gpd.GeoDataFrame(columns=['geometry'], geometry='geometry', crs='EPSG:4326')

def fetch_road_data(polygon, road_tags):
    """Fetch road data from OSM"""
    try:
        roads_gdf = ox.geometries_from_polygon(polygon, tags=road_tags)
        roads_gdf = roads_gdf[roads_gdf.geometry.type.isin(['LineString', 'MultiLineString'])]
        return roads_gdf.to_crs("EPSG:4326")
    except Exception as e:
        logger.warning(f"⚠️ Failed to fetch major roads: {e}")
        return gpd.GeoDataFrame(columns=['geometry'], geometry='geometry', crs='EPSG:4326')

def geohash_to_bounds(gh):
    """Convert geohash to bounding box coordinates"""
    lat, lon, lat_err, lon_err = geohash2.decode_exactly(gh)
    return (lat - lat_err, lat + lat_err, lon - lon_err, lon + lon_err)

def fetch_roads_for_geohash(geohash_str):
    """Fetch and clip roads for a single geohash"""
    try:
        from shapely.geometry import box
        
        south, north, west, east = geohash_to_bounds(geohash_str)
        polygon = box(west, south, east, north)
        
        # Define road tags for UKM calculation
        tags = {
            "highway": [
                "motorway", "motorway_link", "secondary", "secondary_link",
                "primary", "primary_link", "residential", "trunk", "trunk_link",
                "tertiary", "tertiary_link", "living_street", "service", "unclassified"
            ]
        }
        
        # Fetch road data from OSM
        gdf_all = ox.features_from_bbox(north, south, east, west, tags=tags)
        gdf_lines = gdf_all[gdf_all.geometry.type.isin(["LineString", "MultiLineString"])]
        
        # Clip to geohash bounds
        gdf_clipped = gpd.clip(gdf_lines, polygon)
        
        if not gdf_clipped.empty:
            return gdf_clipped.to_crs("EPSG:4326")
        else:
            return gpd.GeoDataFrame(columns=['geometry'], geometry='geometry', crs='EPSG:4326')
            
    except Exception as e:
        logger.warning(f"⚠️ Failed to fetch roads for geohash {geohash_str}: {e}")
        return gpd.GeoDataFrame(columns=['geometry'], geometry='geometry', crs='EPSG:4326')

def fetch_roads_for_geohash_cached(geohash_str, use_cache=True):
    """Fetch and clip roads for a single geohash with caching"""
    try:
        from shapely.geometry import box
        
        # Create cache key
        cache_key = f"roads_{geohash_str}"
        
        # Try cache first if enabled
        if use_cache:
            cached_data = get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data, True  # Return data and cache hit flag
        
        south, north, west, east = geohash_to_bounds(geohash_str)
        polygon = box(west, south, east, north)
        
        # Define road tags for UKM calculation
        tags = {
            "highway": [
                "motorway", "motorway_link", "secondary", "secondary_link",
                "primary", "primary_link", "residential", "trunk", "trunk_link",
                "tertiary", "tertiary_link", "living_street", "service", "unclassified"
            ]
        }
        
        # Fetch road data from OSM with timeout
        import socket
        original_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(30)  # 30 second timeout
        
        try:
            gdf_all = ox.features_from_bbox(north, south, east, west, tags=tags)
            gdf_lines = gdf_all[gdf_all.geometry.type.isin(["LineString", "MultiLineString"])]
            
            # Clip to geohash bounds
            gdf_clipped = gpd.clip(gdf_lines, polygon)
            
            if not gdf_clipped.empty:
                result = gdf_clipped.to_crs("EPSG:4326")
            else:
                result = gpd.GeoDataFrame(columns=['geometry'], geometry='geometry', crs='EPSG:4326')
            
            # Cache the result if caching is enabled
            if use_cache:
                save_to_cache(cache_key, result)
            
            return result, False  # Return data and cache miss flag
            
        finally:
            socket.setdefaulttimeout(original_timeout)
            
    except Exception as e:
        logger.warning(f"⚠️ Failed to fetch roads for geohash {geohash_str}: {e}")
        return gpd.GeoDataFrame(columns=['geometry'], geometry='geometry', crs='EPSG:4326'), False

async def fetch_roads_parallel_advanced(geohash_list, max_workers=8, chunk_size=10, use_cache=True):
    """Advanced parallel road fetching with chunking and caching"""
    loop = asyncio.get_event_loop()
    
    # Split geohashes into chunks for better memory management
    chunks = [geohash_list[i:i + chunk_size] for i in range(0, len(geohash_list), chunk_size)]
    
    all_results = []
    total_failed = 0
    total_cache_hits = 0
    total_cache_misses = 0
    
    logger.info(f"🔄 Processing {len(geohash_list)} geohashes in {len(chunks)} chunks")
    
    for chunk_idx, chunk in enumerate(chunks):
        logger.info(f"📦 Processing chunk {chunk_idx + 1}/{len(chunks)} with {len(chunk)} geohashes")
        
        # Use ThreadPoolExecutor for I/O bound OSM requests
        with ThreadPoolExecutor(max_workers=min(max_workers, len(chunk))) as executor:
            # Submit all tasks for this chunk
            tasks = [
                loop.run_in_executor(executor, fetch_roads_for_geohash_cached, geohash, use_cache)
                for geohash in chunk
            ]
            
            # Wait for all results in this chunk
            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process chunk results
            chunk_valid_results = []
            chunk_failed = 0
            chunk_cache_hits = 0
            chunk_cache_misses = 0
            
            for i, result in enumerate(chunk_results):
                if isinstance(result, Exception):
                    logger.warning(f"⚠️ Failed to process geohash {chunk[i]}: {result}")
                    chunk_failed += 1
                else:
                    gdf_result, cache_hit = result
                    if cache_hit:
                        chunk_cache_hits += 1
                    else:
                        chunk_cache_misses += 1
                    
                    if not gdf_result.empty:
                        chunk_valid_results.append(gdf_result)
                    else:
                        chunk_failed += 1
            
            all_results.extend(chunk_valid_results)
            total_failed += chunk_failed
            total_cache_hits += chunk_cache_hits
            total_cache_misses += chunk_cache_misses
            
            logger.info(f"✅ Chunk {chunk_idx + 1} completed: {len(chunk_valid_results)} valid, {chunk_failed} failed, {chunk_cache_hits} cache hits")
    
    logger.info(f"🎯 Total processing completed: {len(all_results)} valid results, {total_failed} failed, {total_cache_hits} cache hits")
    
    return all_results, total_failed, total_cache_hits, total_cache_misses

@router.get("/health")
async def health_check():
    """Health check for geospatial services"""
    return {
        "status": "healthy",
        "service": "geospatial",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "boundary_to_geohash",
            "extract_geojson",
            "geohash_to_csv",
            "get_bounds",
            "complete_analysis",
            "calculate_target_ukm",
            "calculate_target_ukm_advanced",
            "status_monitoring",
            "cache_management"
        ]
    }

@router.post("/extract-geojson")
async def extract_geojson_from_boundary_data(request: ExtractGeojsonRequest):
    """Extract GeoJSON from boundary data response"""
    try:
        boundary_data = request.boundary_data
        
        if not boundary_data or not boundary_data.get("rows"):
            raise HTTPException(status_code=400, detail="No boundary data rows found")
        
        features = []
        for row in boundary_data["rows"]:
            geometry = None
            properties = {}
            
            # Look for geometry field
            for key, value in row.items():
                if key.lower() in ['geom', 'geometry', 'the_geom']:
                    try:
                        if isinstance(value, str):
                            # Try to parse as different formats
                            if value.startswith(('0', '1')) and len(value) > 20:
                                # WKB format
                                try:
                                    from shapely.wkb import loads as wkb_loads
                                    from shapely.geometry import mapping
                                    import binascii
                                    binary_data = binascii.unhexlify(value)
                                    geom = wkb_loads(binary_data)
                                    geometry = mapping(geom)
                                except:
                                    pass
                            
                            if geometry is None:
                                try:
                                    # Try JSON format
                                    geometry = json.loads(value)
                                except:
                                    # Try WKT format
                                    try:
                                        from shapely.wkt import loads as wkt_loads
                                        from shapely.geometry import mapping
                                        geom = wkt_loads(value)
                                        geometry = mapping(geom)
                                    except:
                                        pass
                        elif isinstance(value, dict):
                            geometry = value
                    except:
                        pass
                else:
                    properties[key] = value
            
            if geometry:
                features.append({
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": properties
                })
        
        if features:
            result = {
                "type": "FeatureCollection",
                "features": features
            }
            return {
                "success": True,
                "geojson": result,
                "feature_count": len(features)
            }
        else:
            raise HTTPException(status_code=400, detail="No valid geometry found in boundary data")
            
    except Exception as e:
        logger.error(f"Error in extract_geojson: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to extract GeoJSON: {str(e)}")

@router.post("/geohash-to-csv")
async def geohash_to_csv(request: GeohashToCsvRequest):
    """Convert geohash GeoJSON to CSV format"""
    try:
        geohashes_geojson = request.geohashes_geojson
        
        if not geohashes_geojson or not geohashes_geojson.get("features"):
            raise HTTPException(status_code=400, detail="No geohash features found")
        
        rows = []
        for feature in geohashes_geojson["features"]:
            props = feature.get("properties", {})
            rows.append({
                "geohash": props.get("geoHash", ""),
                "lat": props.get("center_lat", ""),
                "lon": props.get("center_lon", "")
            })
        
        if rows:
            df = pd.DataFrame(rows)
            csv_data = df.to_csv(index=False)
            return {
                "success": True,
                "csv_data": csv_data,
                "row_count": len(rows)
            }
        else:
            raise HTTPException(status_code=400, detail="No valid geohash data found")
            
    except Exception as e:
        logger.error(f"Error in geohash_to_csv: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to convert to CSV: {str(e)}")

@router.post("/get-bounds")
async def get_bounds_from_geojson(request: GetBoundsRequest):
    """Calculate bounds from GeoJSON for map fitting"""
    try:
        geojson = request.geojson
        
        if not geojson or not geojson.get('features'):
            raise HTTPException(status_code=400, detail="No GeoJSON features found")
        
        bounds = [[90, 180], [-90, -180]]
        
        for feature in geojson['features']:
            coords = feature['geometry']['coordinates']
            if feature['geometry']['type'] == 'Polygon':
                rings = [coords]
            elif feature['geometry']['type'] == 'MultiPolygon':
                rings = coords
            else:
                continue
                
            for ring in rings:
                for point in ring[0]:
                    lon, lat = point[:2]  # Handle 2D and 3D coordinates
                    bounds[0][0] = min(bounds[0][0], lat)
                    bounds[0][1] = min(bounds[0][1], lon)
                    bounds[1][0] = max(bounds[1][0], lat)
                    bounds[1][1] = max(bounds[1][1], lon)
        
        return {
            "success": True,
            "bounds": bounds,
            "bbox": {
                "min_lat": bounds[0][0],
                "min_lon": bounds[0][1],
                "max_lat": bounds[1][0],
                "max_lon": bounds[1][1]
            }
        }
        
    except Exception as e:
        logger.error(f"Error in get_bounds: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate bounds: {str(e)}")

@router.post("/boundary-to-geohash", response_model=Dict[str, Any])
async def convert_boundary_to_geohash(
    request: BoundaryToGeohashRequest,
    db: Session = Depends(get_db)
):
    """Convert boundary area to geohash grid (eliminates duplicate geohashes)"""
    try:
        # Import geohash library
        import geohash2 as geohash
        import geopandas as gpd
        from shapely.geometry import box, shape
        
        # Convert boundary to shapely geometry
        boundary_geom = shape(request.boundary_geojson["geometry"] if "geometry" in request.boundary_geojson else request.boundary_geojson)
        
        # Get bounding box
        minx, miny, maxx, maxy = boundary_geom.bounds
        
        # Generate geohash grid
        # Use set to track unique geohashes and avoid duplicates
        unique_geohashes = set()
        geohash_features = []
        
        # Calculate step size based on precision (more conservative to ensure coverage)
        precision = request.precision
        lat_step = 0.008 if precision == 5 else 0.003 if precision == 6 else 0.001
        lon_step = 0.008 if precision == 5 else 0.003 if precision == 6 else 0.001
        
        # Generate grid points
        current_lat = miny
        while current_lat <= maxy:
            current_lon = minx
            while current_lon <= maxx:
                # Create point and get geohash
                point_geohash = geohash.encode(current_lat, current_lon, precision)
                
                # Skip if this geohash already processed
                if point_geohash in unique_geohashes:
                    current_lon += lon_step
                    continue
                
                # Decode back to get the geohash polygon bounds
                decoded_lat, decoded_lon, lat_err, lon_err = geohash.decode_exactly(point_geohash)
                
                # Create geohash bounding box
                geohash_box = box(
                    decoded_lon - lon_err, decoded_lat - lat_err,
                    decoded_lon + lon_err, decoded_lat + lat_err
                )
                
                # Check if geohash intersects with boundary
                if boundary_geom.intersects(geohash_box):
                    # Add to unique set
                    unique_geohashes.add(point_geohash)
                    
                    # Calculate center point
                    center_lat = decoded_lat
                    center_lon = decoded_lon
                    
                    geohash_features.append({
                        "type": "Feature",
                        "properties": {
                            "geoHash": point_geohash,
                            "center_lat": center_lat,
                            "center_lon": center_lon
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [decoded_lon - lon_err, decoded_lat - lat_err],
                                [decoded_lon + lon_err, decoded_lat - lat_err],
                                [decoded_lon + lon_err, decoded_lat + lat_err],
                                [decoded_lon - lon_err, decoded_lat + lat_err],
                                [decoded_lon - lon_err, decoded_lat - lat_err]
                            ]]
                        }
                    })
                
                current_lon += lon_step
            current_lat += lat_step
        
        # Create GeoJSON FeatureCollection
        result = {
            "type": "FeatureCollection",
            "features": geohash_features
        }
        
        logger.info(f"Generated {len(unique_geohashes)} unique geohashes (precision {precision})")
        
        return {
            "success": True,
            "geohash_count": len(unique_geohashes),
            "precision": precision,
            "geohashes_geojson": result
        }
        
    except Exception as e:
        logger.error(f"Error in boundary_to_geohash: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate geohash: {str(e)}")

@router.post("/select-dense-geohash")
async def select_dense_geohash_from_boundary(
    request: SelectDenseGeohashRequest,
    db: Session = Depends(get_db)
):
    """Select dense geohash areas from uploaded boundary using OSM data"""
    try:
        # 1. Convert GeoJSON to GeoDataFrame (read boundary)
        # Handle both single geometry and FeatureCollection (from geohash GeoJSON)
        if request.boundary_geojson.get("type") == "FeatureCollection":
            # If it's a FeatureCollection (e.g., from geohash GeoJSON), use all features
            boundary_gdf = gpd.GeoDataFrame.from_features(
                request.boundary_geojson["features"], 
                crs="EPSG:4326"
            )
        elif request.boundary_geojson.get("type") == "Feature":
            # If it's a single Feature
            boundary_gdf = gpd.GeoDataFrame.from_features([request.boundary_geojson], crs="EPSG:4326")
        else:
            # If it's just a geometry object
            boundary_gdf = gpd.GeoDataFrame.from_features([{
                "type": "Feature",
                "geometry": request.boundary_geojson,
                "properties": {}
            }], crs="EPSG:4326")
        
        # Create union of all boundary polygons
        polygon = boundary_gdf.unary_union

        # 2. Fetch POI and road data in parallel (optimized)
        logger.info("📡 Fetching OSM data in parallel...")
        tags_dict = {tag: True for tag in request.tag_filters}
        road_tags = {'highway': ['motorway', 'trunk', 'primary', 'secondary']}
        
        # Use parallel fetching for better performance
        poi_gdf, roads_gdf = await fetch_osm_data_parallel(polygon, tags_dict, road_tags)

        # 4. Combine POI and roads data
        logger.info(f"📊 Found {len(poi_gdf)} POI features and {len(roads_gdf)} road features")
        all_gdf = pd.concat([poi_gdf, roads_gdf], ignore_index=True)
        if all_gdf.empty:
            logger.error("❌ No POI or road data found.")
            raise HTTPException(status_code=400, detail="No POI or road data found")
        
        logger.info(f"🔄 Processing {len(all_gdf)} total features...")

        # 5. Encode to geohash (optimized batch processing)
        logger.info("🔢 Encoding geometries to geohash...")
        all_gdf['geohash'] = encode_geohash_batch(all_gdf.geometry, request.precision)
        all_gdf = all_gdf.dropna(subset=['geohash'])
        all_gdf = all_gdf[all_gdf['geohash'].apply(lambda x: isinstance(x, str))]

        # 6. Count objects per geohash
        logger.info("📈 Calculating geohash density...")
        count_df = all_gdf.groupby('geohash').size().reset_index(name='count')
        threshold = count_df['count'].quantile(1 - request.top_percent)
        dense_df = count_df[count_df['count'] >= threshold]
        
        logger.info(f"📍 Selected {len(dense_df)} dense geohash areas (threshold: {threshold:.1f})")
        
        # Early exit if no dense areas found
        if dense_df.empty:
            logger.warning("⚠️ No dense areas found with current threshold")
            return {
                "success": True,
                "geohash_count": 0,
                "precision": request.precision,
                "top_percent": request.top_percent,
                "dense_geohash_geojson": {"type": "FeatureCollection", "features": []}
            }

        # 7. Add geohash that become "centers" of dense neighbors (optimized)
        logger.info("📍 Finding missing center geohash areas...")
        def add_missing_centers_optimized(df):
            # Use set for faster lookups
            existing_geohashes = set(df['geohash'].values)
            all_neighbors = []
            
            # Batch process neighbors
            for gh in df['geohash']:
                try:
                    nbs = geohash2.neighbors(gh)
                    all_neighbors.extend(nbs)
                except:
                    continue
            
            # Use Counter for frequency count
            freq = Counter(all_neighbors)
            
            # Find missing centers more efficiently
            missing = [g for g, count in freq.items() 
                      if g not in existing_geohashes and count >= 2]
            
            if missing:
                df_extra = count_df[count_df['geohash'].isin(missing)]
                return pd.concat([df, df_extra], ignore_index=True)
            return df

        dense_df = add_missing_centers_optimized(dense_df)

        # 8. Convert geohash to polygon (using cached function)
        logger.info("🔄 Converting geohash to polygons...")
        dense_gdf = gpd.GeoDataFrame({
            'geohash': dense_df['geohash'],
            'count': dense_df['count'],
            'geometry': dense_df['geohash'].apply(cached_geohash_to_polygon)
        }, crs='EPSG:4326')

        # 9. Remove spatial outliers
        logger.info("🧹 Removing outlier geohash areas...")
        dense_union = dense_gdf.unary_union
        if dense_union.geom_type == 'MultiPolygon':
            largest = max(dense_union.geoms, key=lambda g: g.area)
        else:
            largest = dense_union
        dense_gdf = dense_gdf[dense_gdf.geometry.intersects(largest)]

        # 10. Convert to GeoJSON format (optimized)
        logger.info("📋 Converting to GeoJSON format...")
        features = []
        for _, row in dense_gdf.iterrows():
            feature = {
                "type": "Feature", 
                "properties": {
                    "geoHash": row['geohash'],
                    "count": int(row['count'])
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [list(row['geometry'].exterior.coords)]
                }
            }
            features.append(feature)

        result_geojson = {
            "type": "FeatureCollection",
            "features": features
        }

        logger.info(f"✅ Dense geohash analysis completed. Found {len(features)} dense areas.")

        return {
            "success": True,
            "geohash_count": len(features),
            "precision": request.precision,
            "top_percent": request.top_percent,
            "dense_geohash_geojson": result_geojson
        }

    except Exception as e:
        logger.error(f"Error in select_dense_geohash: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to select dense geohash: {str(e)}")

@router.post("/calculate-target-ukm", response_model=CalculateTargetUkmResponse)
async def calculate_target_ukm(request: CalculateTargetUkmRequest):
    """Calculate target UKM by fetching and clipping roads from geohash areas in parallel"""
    try:
        start_time = time.time()
        geohash_list = request.geohashes
        
        if not geohash_list:
            raise HTTPException(status_code=400, detail="No geohashes provided")
        
        # Filter to valid 6-character geohashes
        valid_geohashes = [gh for gh in geohash_list if len(str(gh).strip()) == 6]
        
        if not valid_geohashes:
            raise HTTPException(status_code=400, detail="No valid 6-character geohashes found")
        
        logger.info(f"🔍 Processing {len(valid_geohashes)} geohashes for UKM calculation...")
        
        # Fetch roads in parallel with optimized worker count
        max_workers = min(8, len(valid_geohashes))  # Limit workers to avoid overwhelming OSM API
        road_results, failed_count, _, _ = await fetch_roads_parallel_advanced(valid_geohashes, max_workers)
        
        # Combine all road segments
        if road_results:
            logger.info(f"✅ Successfully processed {len(road_results)} geohashes")
            combined_roads = pd.concat(road_results, ignore_index=True)
            
            # Calculate total length in kilometers (using metric projection)
            roads_metric = combined_roads.to_crs(epsg=3857)
            total_length_km = roads_metric.length.sum() / 1000
            
            # Convert back to WGS84 for response
            combined_roads = combined_roads.to_crs(epsg=4326)
            
            # Convert to GeoJSON for response
            roads_geojson = json.loads(combined_roads.to_json())
            
            processing_time = time.time() - start_time
            logger.info(f"🎯 UKM calculation completed in {processing_time:.2f}s")
            logger.info(f"📊 Total road length: {total_length_km:.2f} km from {len(combined_roads)} segments")
            
            return CalculateTargetUkmResponse(
                success=True,
                total_road_segments=len(combined_roads),
                total_road_length_km=round(total_length_km, 2),
                processed_geohashes=len(valid_geohashes) - failed_count,
                failed_geohashes=failed_count,
                roads_geojson=roads_geojson
            )
        else:
            logger.warning("⚠️ No roads found in any geohash areas")
            return CalculateTargetUkmResponse(
                success=True,
                total_road_segments=0,
                total_road_length_km=0.0,
                processed_geohashes=0,
                failed_geohashes=len(valid_geohashes),
                roads_geojson={"type": "FeatureCollection", "features": []}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in calculate_target_ukm: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate target UKM: {str(e)}")

@router.post("/calculate-target-ukm-advanced", response_model=CalculateTargetUkmAdvancedResponse)
async def calculate_target_ukm_advanced(request: CalculateTargetUkmAdvancedRequest):
    """Advanced UKM calculation with caching, chunking, and performance optimizations"""
    try:
        start_time = time.time()
        geohash_list = request.geohashes
        
        if not geohash_list:
            raise HTTPException(status_code=400, detail="No geohashes provided")
        
        # Filter to valid 6-character geohashes
        valid_geohashes = [gh for gh in geohash_list if len(str(gh).strip()) == 6]
        
        if not valid_geohashes:
            raise HTTPException(status_code=400, detail="No valid 6-character geohashes found")
        
        logger.info(f"🚀 Advanced UKM processing: {len(valid_geohashes)} geohashes, chunk_size={request.chunk_size}, workers={request.max_workers}, cache={request.use_cache}")
        
        # Use advanced parallel processing with all optimizations
        road_results, failed_count, cache_hits, cache_misses = await fetch_roads_parallel_advanced(
            valid_geohashes, 
            max_workers=request.max_workers,
            chunk_size=request.chunk_size,
            use_cache=request.use_cache
        )
        
        processing_time = time.time() - start_time
        
        # Combine all road segments
        if road_results:
            logger.info(f"✅ Successfully processed {len(road_results)} geohashes")
            combined_roads = pd.concat(road_results, ignore_index=True)
            
            # Calculate total length in kilometers (using metric projection)
            roads_metric = combined_roads.to_crs(epsg=3857)
            total_length_km = roads_metric.length.sum() / 1000
            
            # Convert back to WGS84 for response
            combined_roads = combined_roads.to_crs(epsg=4326)
            
            # Convert to GeoJSON for response if requested
            roads_geojson = None
            if request.return_geojson:
                roads_geojson = json.loads(combined_roads.to_json())
            
            logger.info(f"🎯 Advanced UKM calculation completed in {processing_time:.2f}s")
            logger.info(f"📊 Total road length: {total_length_km:.2f} km from {len(combined_roads)} segments")
            logger.info(f"🚀 Performance: {cache_hits} cache hits, {cache_misses} cache misses")
            
            return CalculateTargetUkmAdvancedResponse(
                success=True,
                total_road_segments=len(combined_roads),
                total_road_length_km=round(total_length_km, 2),
                processed_geohashes=len(valid_geohashes) - failed_count,
                failed_geohashes=failed_count,
                processing_time_seconds=round(processing_time, 2),
                cache_hits=cache_hits,
                cache_misses=cache_misses,
                roads_geojson=roads_geojson
            )
        else:
            logger.warning("⚠️ No roads found in any geohash areas")
            return CalculateTargetUkmAdvancedResponse(
                success=True,
                total_road_segments=0,
                total_road_length_km=0.0,
                processed_geohashes=0,
                failed_geohashes=len(valid_geohashes),
                processing_time_seconds=round(processing_time, 2),
                cache_hits=cache_hits,
                cache_misses=cache_misses,
                roads_geojson={"type": "FeatureCollection", "features": []} if request.return_geojson else None
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in calculate_target_ukm_advanced: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate advanced target UKM: {str(e)}")

@router.post("/clear-cache")
async def clear_osm_cache():
    """Clear OSM data cache to free memory"""
    global osm_cache, osm_cache_with_ttl
    old_cache_size = len(osm_cache)
    ttl_cache_size = len(osm_cache_with_ttl)
    
    # Clear both cache systems
    osm_cache.clear()
    osm_cache_with_ttl.clear()
    
    # Clear LRU caches
    cached_geohash_encode.cache_clear()
    cached_geohash_to_polygon.cache_clear()
    
    total_cleared = old_cache_size + ttl_cache_size
    logger.info(f"🧹 Cleared cache with {total_cleared} total entries")
    
    return {
        "success": True,
        "message": f"Cache cleared successfully. Removed {total_cleared} cached entries.",
        "cache_stats": {
            "old_osm_cache_cleared": old_cache_size,
            "ttl_cache_cleared": ttl_cache_size,
            "geohash_encode_cache_cleared": True,
            "geohash_polygon_cache_cleared": True
        }
    }

@router.get("/cache-stats")
async def get_cache_stats():
    """Get current cache statistics with TTL info"""
    # Count valid TTL cache entries
    current_time = time.time()
    valid_ttl_entries = 0
    expired_ttl_entries = 0
    
    for key, entry in osm_cache_with_ttl.items():
        if is_cache_valid(entry):
            valid_ttl_entries += 1
        else:
            expired_ttl_entries += 1
    
    return {
        "old_osm_cache_size": len(osm_cache),
        "ttl_cache_total": len(osm_cache_with_ttl),
        "ttl_cache_valid": valid_ttl_entries,
        "ttl_cache_expired": expired_ttl_entries,
        "cache_ttl_seconds": CACHE_TTL,
        "geohash_encode_cache_info": cached_geohash_encode.cache_info()._asdict(),
        "geohash_polygon_cache_info": cached_geohash_to_polygon.cache_info()._asdict()
    } 