from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import json
import logging
from sqlalchemy import table, text
from typing import List

from api.database.connection import get_db
from api.schemas.country import (
    CountrySchemas, CountryRequest, CountryPricingResponse, UpdateCountryPricingRequest,
    RegionSchemas, RegionRequest, RegionPricingResponse, CreateRegionRequest, UpdateRegionRequest
)
from api.models.country import Country, Region

# Import processing functions
import sys
from pathlib import Path


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/country", tags=["country"])

def safe_getattr(obj, attr, default=None):
    """Safely get attribute from object, return default if not exists"""
    try:
        return getattr(obj, attr, default)
    except:
        return default

@router.get("/all")
async def get_all_countries(db: Session = Depends(get_db)):
    try:
        # Try using ORM first
        countries = db.query(Country).all()
        
        if countries:
            data = []
            for country in countries:
                data.append(
                    CountrySchemas(
                        id=country.id,
                        name=country.name,
                        table=safe_getattr(country, 'table', 'default_table'),
                        currency=safe_getattr(country, 'currency', 'USD'),
                        currency_symbol=safe_getattr(country, 'currency_symbol', '$'),
                        ukm_price=safe_getattr(country, 'ukm_price', 8000.0),
                        insurance=safe_getattr(country, 'insurance_per_dax_per_month', 132200.0),
                        dataplan=safe_getattr(country, 'dataplan_per_dax_per_month', 450000.0),
                        exchange_rate_to_usd=safe_getattr(country, 'exchange_rate_to_usd', 1.0),
                        created_at=safe_getattr(country, 'created_at', None),
                        updated_at=safe_getattr(country, 'updated_at', None)
                    )
                )
            return data
        else:
            # If no countries, return empty list
            return []
            
    except Exception as e:
        # If ORM fails, try raw SQL as fallback
        logger.warning(f"ORM query failed, trying raw SQL: {e}")
        try:
            query = text("SELECT * FROM country")
            result = db.execute(query)
            data = []
            for row in result:
                data.append(
                    CountrySchemas(
                        id=row.id,
                        name=row.name,
                        table=safe_getattr(row, 'table', 'default_table'),
                        currency=safe_getattr(row, 'currency', 'USD'),
                        currency_symbol=safe_getattr(row, 'currency_symbol', '$'),
                        ukm_price=safe_getattr(row, 'ukm_price', 8000.0),
                        insurance=safe_getattr(row, 'insurance_per_dax_per_month', 132200.0),
                        dataplan=safe_getattr(row, 'dataplan_per_dax_per_month', 450000.0),
                        exchange_rate_to_usd=safe_getattr(row, 'exchange_rate_to_usd', 1.0),
                        created_at=safe_getattr(row, 'created_at', None),
                        updated_at=safe_getattr(row, 'updated_at', None)
                    )
                )
            return data
        except Exception as e2:
            logger.error(f"Both ORM and raw SQL failed: {e2}")
            return []

@router.get("/pricing", response_model=List[CountryPricingResponse])
async def get_countries_with_pricing(db: Session = Depends(get_db)):
    """Get all countries with their pricing information for forecast calculations"""
    query = text(
        """
        select * from country
    """
    )
    result = db.execute(query)
    data = []
    for row in result:
        data.append(
            CountryPricingResponse(
                id=row.id,
                name=row.name,
                currency=row.currency,
                currency_symbol=row.currency_symbol,
                exchange_rate_to_usd=0.000063,
                regions=[]
            )
        )
    return data

            

@router.get("/pricing/{country_id}", response_model=CountryPricingResponse)
async def get_country_pricing(country_id: int, db: Session = Depends(get_db)):
    """Get pricing information for a specific country"""
    try:
        country = db.query(Country).filter(Country.id == country_id).first()
        
        if not country:
            raise HTTPException(status_code=404, detail="Country not found")
        
        return CountryPricingResponse(
            id=country.id,
            name=country.name,
            currency=safe_getattr(country, 'currency', 'USD'),
            currency_symbol=safe_getattr(country, 'currency_symbol', '$'),
            ukm_price=safe_getattr(country, 'ukm_price', 8000.0),
            insurance=safe_getattr(country, 'insurance_per_dax_per_month', 132200.0),
            dataplan=safe_getattr(country, 'dataplan_per_dax_per_month', 450000.0),
            exchange_rate_to_usd=safe_getattr(country, 'exchange_rate_to_usd', 1.0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting country pricing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get country pricing: {str(e)}")

@router.put("/pricing/{country_id}", response_model=CountryPricingResponse)
async def update_country_pricing(
    country_id: int, 
    pricing_data: UpdateCountryPricingRequest,
    db: Session = Depends(get_db)
):
    """Update pricing information for a specific country"""
    try:
        country = db.query(Country).filter(Country.id == country_id).first()
        
        if not country:
            raise HTTPException(status_code=404, detail="Country not found")
        
        # Update only provided fields
        if pricing_data.currency is not None:
            if hasattr(country, 'currency'):
                country.currency = pricing_data.currency
        if pricing_data.currency_symbol is not None:
            if hasattr(country, 'currency_symbol'):
                country.currency_symbol = pricing_data.currency_symbol
        if pricing_data.ukm_price is not None:
            if hasattr(country, 'ukm_price'):
                country.ukm_price = pricing_data.ukm_price
        if pricing_data.insurance is not None:
            if hasattr(country, 'insurance_per_dax_per_month'):
                country.insurance_per_dax_per_month = pricing_data.insurance
        if pricing_data.dataplan is not None:
            if hasattr(country, 'dataplan_per_dax_per_month'):
                country.dataplan_per_dax_per_month = pricing_data.dataplan
        if pricing_data.exchange_rate_to_usd is not None:
            if hasattr(country, 'exchange_rate_to_usd'):
                country.exchange_rate_to_usd = pricing_data.exchange_rate_to_usd
        
        db.commit()
        db.refresh(country)
        
        return CountryPricingResponse(
            id=country.id,
            name=country.name,
            currency=safe_getattr(country, 'currency', 'USD'),
            currency_symbol=safe_getattr(country, 'currency_symbol', '$'),
            ukm_price=safe_getattr(country, 'ukm_price', 8000.0),
            insurance=safe_getattr(country, 'insurance_per_dax_per_month', 132200.0),
            dataplan=safe_getattr(country, 'dataplan_per_dax_per_month', 450000.0),
            exchange_rate_to_usd=safe_getattr(country, 'exchange_rate_to_usd', 1.0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating country pricing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update country pricing: {str(e)}")

# ========== REGION ENDPOINTS ==========

@router.get("/regions", response_model=List[RegionPricingResponse])
async def get_all_regions_with_pricing(db: Session = Depends(get_db)):
    """Get all regions with calculated pricing information"""
    try:
        regions = db.query(Region).join(Country).all()
        
        pricing_data = []
        for region in regions:
            country = region.country
            
            # Calculate regional prices
            regional_ukm_price = (country.ukm_price or 8000.0) * (region.ukm_price_multiplier or 1.0)
            regional_insurance = (country.insurance_per_dax_per_month or 132200.0) * (region.insurance_multiplier or 1.0)
            regional_dataplan = (country.dataplan_per_dax_per_month or 450000.0) * (region.dataplan_multiplier or 1.0)
            
            pricing_data.append(RegionPricingResponse(
                id=region.id,
                name=region.name,
                country_id=region.country_id,
                country_name=country.name,
                currency=safe_getattr(country, 'currency', 'USD'),
                currency_symbol=safe_getattr(country, 'currency_symbol', '$'),
                regional_ukm_price=regional_ukm_price,
                regional_insurance=regional_insurance,
                regional_dataplan=regional_dataplan,
                regional_overhead=region.regional_overhead or 0.0,
                transportation_cost=region.transportation_cost or 0.0,
                exchange_rate_to_usd=safe_getattr(country, 'exchange_rate_to_usd', 1.0)
            ))
        
        return pricing_data
        
    except Exception as e:
        logger.error(f"Error getting all regions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get regions: {str(e)}")

@router.get("/regions/country/{country_id}", response_model=List[RegionPricingResponse])
async def get_regions_by_country(country_id: int, db: Session = Depends(get_db)):
    """Get all regions for a specific country with pricing"""
    try:
        country = db.query(Country).filter(Country.id == country_id).first()
        if not country:
            raise HTTPException(status_code=404, detail="Country not found")
        
        regions = db.query(Region).filter(Region.country_id == country_id).all()
        
        pricing_data = []
        for region in regions:
            # Calculate regional prices
            regional_ukm_price = (country.ukm_price or 8000.0) * (region.ukm_price_multiplier or 1.0)
            regional_insurance = (country.insurance_per_dax_per_month or 132200.0) * (region.insurance_multiplier or 1.0)
            regional_dataplan = (country.dataplan_per_dax_per_month or 450000.0) * (region.dataplan_multiplier or 1.0)
            
            pricing_data.append(RegionPricingResponse(
                id=region.id,
                name=region.name,
                country_id=region.country_id,
                country_name=country.name,
                currency=safe_getattr(country, 'currency', 'USD'),
                currency_symbol=safe_getattr(country, 'currency_symbol', '$'),
                regional_ukm_price=regional_ukm_price,
                regional_insurance=regional_insurance,
                regional_dataplan=regional_dataplan,
                regional_overhead=region.regional_overhead or 0.0,
                transportation_cost=region.transportation_cost or 0.0,
                exchange_rate_to_usd=safe_getattr(country, 'exchange_rate_to_usd', 1.0)
            ))
        
        return pricing_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting regions by country: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get regions for country: {str(e)}")

@router.get("/regions/{region_id}", response_model=RegionPricingResponse)
async def get_region_pricing(region_id: int, db: Session = Depends(get_db)):
    """Get pricing information for a specific region"""
    try:
        region = db.query(Region).join(Country).filter(Region.id == region_id).first()
        
        if not region:
            raise HTTPException(status_code=404, detail="Region not found")
        
        country = region.country
        
        # Calculate regional prices
        regional_ukm_price = (country.ukm_price or 8000.0) * (region.ukm_price_multiplier or 1.0)
        regional_insurance = (country.insurance_per_dax_per_month or 132200.0) * (region.insurance_multiplier or 1.0)
        regional_dataplan = (country.dataplan_per_dax_per_month or 450000.0) * (region.dataplan_multiplier or 1.0)
        
        return RegionPricingResponse(
            id=region.id,
            name=region.name,
            country_id=region.country_id,
            country_name=country.name,
            currency=safe_getattr(country, 'currency', 'USD'),
            currency_symbol=safe_getattr(country, 'currency_symbol', '$'),
            regional_ukm_price=regional_ukm_price,
            regional_insurance=regional_insurance,
            regional_dataplan=regional_dataplan,
            regional_overhead=region.regional_overhead or 0.0,
            transportation_cost=region.transportation_cost or 0.0,
            exchange_rate_to_usd=safe_getattr(country, 'exchange_rate_to_usd', 1.0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting region pricing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get region pricing: {str(e)}")

@router.post("/regions", response_model=RegionSchemas)
async def create_region(region_data: CreateRegionRequest, db: Session = Depends(get_db)):
    """Create a new region"""
    try:
        # Check if country exists
        country = db.query(Country).filter(Country.id == region_data.country_id).first()
        if not country:
            raise HTTPException(status_code=404, detail="Country not found")
        
        # Create new region
        region = Region(
            name=region_data.name,
            country_id=region_data.country_id,
            ukm_price_multiplier=region_data.ukm_price_multiplier,
            insurance_multiplier=region_data.insurance_multiplier,
            dataplan_multiplier=region_data.dataplan_multiplier,
            regional_overhead=region_data.regional_overhead,
            transportation_cost=region_data.transportation_cost
        )
        
        db.add(region)
        db.commit()
        db.refresh(region)
        
        return RegionSchemas(
            id=region.id,
            name=region.name,
            country_id=region.country_id,
            ukm_price_multiplier=region.ukm_price_multiplier,
            insurance_multiplier=region.insurance_multiplier,
            dataplan_multiplier=region.dataplan_multiplier,
            regional_overhead=region.regional_overhead,
            transportation_cost=region.transportation_cost,
            created_at=region.created_at,
            updated_at=region.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating region: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create region: {str(e)}")

@router.put("/regions/{region_id}", response_model=RegionSchemas)
async def update_region(region_id: int, region_data: UpdateRegionRequest, db: Session = Depends(get_db)):
    """Update region information"""
    try:
        region = db.query(Region).filter(Region.id == region_id).first()
        
        if not region:
            raise HTTPException(status_code=404, detail="Region not found")
        
        # Update only provided fields
        if region_data.name is not None:
            region.name = region_data.name
        if region_data.ukm_price_multiplier is not None:
            region.ukm_price_multiplier = region_data.ukm_price_multiplier
        if region_data.insurance_multiplier is not None:
            region.insurance_multiplier = region_data.insurance_multiplier
        if region_data.dataplan_multiplier is not None:
            region.dataplan_multiplier = region_data.dataplan_multiplier
        if region_data.regional_overhead is not None:
            region.regional_overhead = region_data.regional_overhead
        if region_data.transportation_cost is not None:
            region.transportation_cost = region_data.transportation_cost
        
        db.commit()
        db.refresh(region)
        
        return RegionSchemas(
            id=region.id,
            name=region.name,
            country_id=region.country_id,
            ukm_price_multiplier=region.ukm_price_multiplier,
            insurance_multiplier=region.insurance_multiplier,
            dataplan_multiplier=region.dataplan_multiplier,
            regional_overhead=region.regional_overhead,
            transportation_cost=region.transportation_cost,
            created_at=region.created_at,
            updated_at=region.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating region: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update region: {str(e)}")

@router.delete("/regions/{region_id}")
async def delete_region(region_id: int, db: Session = Depends(get_db)):
    """Delete a region"""
    try:
        region = db.query(Region).filter(Region.id == region_id).first()
        
        if not region:
            raise HTTPException(status_code=404, detail="Region not found")
        
        db.delete(region)
        db.commit()
        
        return {"message": f"Region '{region.name}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting region: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete region: {str(e)}")

@router.get("/{id}")
async def get_country_by_id(id: int, db: Session = Depends(get_db)):
    try:
        country = db.query(Country).filter(Country.id == id).first()
        if not country:
            raise HTTPException(status_code=404, detail="Country not found")
        
        return CountrySchemas(
            id=country.id,
            name=country.name,
            table=safe_getattr(country, 'table', 'default_table'),
            currency=safe_getattr(country, 'currency', 'USD'),
            currency_symbol=safe_getattr(country, 'currency_symbol', '$'),
            ukm_price=safe_getattr(country, 'ukm_price', 8000.0),
            insurance=safe_getattr(country, 'insurance_per_dax_per_month', 132200.0),
            dataplan=safe_getattr(country, 'dataplan_per_dax_per_month', 450000.0),
            exchange_rate_to_usd=safe_getattr(country, 'exchange_rate_to_usd', 1.0),
            created_at=safe_getattr(country, 'created_at', None),
            updated_at=safe_getattr(country, 'updated_at', None)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting country by id: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get country: {str(e)}")

@router.post("/", tags=["🗺️ Boundary by Country"])
def get_boundary_by_country(req: CountryRequest, db: Session = Depends(get_db)):
    try:
        # 1. Get country information
        country = db.query(Country).filter(Country.id == req.country_id).first()
        if not country:
            raise HTTPException(status_code=404, detail="Country not found")

        # 2. Get table name from country's 'table' column
        table = safe_getattr(country, 'table', None)
        
        if not table or table == 'default_table':
            # Return message if no valid table is configured
            logger.warning(f"No valid boundary table configured for country {country.name} (ID: {country.id})")
            return {
                "table": table or "no_table", 
                "rows": [],
                "message": f"No boundary data table configured for {country.name}. Please configure the boundary data table in the country settings."
            }

        # 3. Check if boundary table exists
        try:
            check_query = text("SELECT 1 FROM information_schema.tables WHERE table_name = :table_name")
            table_exists = db.execute(check_query, {"table_name": table}).fetchone()
            
            if not table_exists:
                logger.warning(f"Boundary table '{table}' does not exist for country {country.name}")
                return {
                    "table": table, 
                    "rows": [],
                    "message": f"Boundary data table '{table}' not found for {country.name}. Please contact administrator to set up the boundary data."
                }
        except Exception as table_check_error:
            logger.warning(f"Could not check if boundary table exists: {table_check_error}")
            # Continue with the original query attempt

        # 4. Query the boundary table
        try:
            query = text(f"SELECT * FROM {table}")
            result = db.execute(query)
            columns = result.keys()
            
            # Convert rows to dictionaries with proper data type handling
            boundary_data = []
            for row in result.fetchall():
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Handle different PostgreSQL data types
                    if value is not None:
                        if hasattr(value, 'decode'):  # Handle bytes
                            try:
                                row_dict[col] = value.decode('utf-8')
                            except:
                                row_dict[col] = str(value)
                        else:
                            row_dict[col] = value
                    else:
                        row_dict[col] = None
                boundary_data.append(row_dict)

            if not boundary_data:
                return {
                    "table": table, 
                    "rows": [],
                    "message": f"No boundary data found in table '{table}' for {country.name}."
                }

            logger.info(f"Successfully retrieved {len(boundary_data)} boundary records from table '{table}' for {country.name}")
            return {
                "table": table, 
                "rows": boundary_data,
                "country_name": country.name,
                "country_id": country.id
            }

        except Exception as query_error:
            logger.error(f"Error querying boundary table '{table}': {query_error}")
            if "does not exist" in str(query_error).lower() or "no such table" in str(query_error).lower():
                return {
                    "table": table, 
                    "rows": [],
                    "message": f"Boundary data table '{table}' not found for {country.name}. Please contact administrator."
                }
            else:
                raise HTTPException(status_code=500, detail=f"Failed to query boundary data: {str(query_error)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting boundary by country: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get boundary data: {str(e)}")