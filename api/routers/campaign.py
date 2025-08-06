from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import json
import logging
from sqlalchemy import table, text

from api.database.connection import get_db
from api.schemas.campaign import CampaignSchemas
from api.models.campaign import Campaign

# Import processing functions
import sys
from pathlib import Path


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaign", tags=["campaign"])

@router.get("/all")
async def get_all_campaigns(db: Session = Depends(get_db)):
    query = text(
        """
        select * from campaign
    """
    )
    result = db.execute(query)
    data = []
    for row in result:
        data.append(
            CampaignSchemas(
                id=row.id,
                campaign_name=row.campaign_name,
                country=row.country,
                city=row.city,
                ukm_plan=row.ukm_plan,
                ukm_actual=row.ukm_actual,
                persentase_ukm_actual=row.persentase_ukm_actual
            )
        )
    return data


@router.get("/names")
async def get_campaign_names(db: Session = Depends(get_db)):
    """Get all campaign names for dropdown selection"""
    query = text(
        """
        select id, campaign_name from campaign 
        order by campaign_name
        """
    )
    result = db.execute(query)
    data = []
    for row in result:
        data.append({
            "id": row.id,
            "campaign_name": row.campaign_name
        })
    return data


@router.get("/{id}")
async def get_all_campaigns_id(id: int, db: Session = Depends(get_db)):
    query = text(
        """
        select * from campaign
        where id = :id
    """
    )
    result = db.execute(query, {"id": id})
    data = []
    for row in result:
        data.append(
            CampaignSchemas(
                id=row.id,
                campaign_name=row.campaign_name,
                country=row.country,
                city=row.city,
                ukm_plan=row.ukm_plan,
                ukm_actual=row.ukm_actual,
                persentase_ukm_actual=row.persentase_ukm_actual
            )
        )
    return data