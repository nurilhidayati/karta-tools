from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import json
import logging
from sqlalchemy import table, text

from api.database.connection import get_db
from api.schemas.boundary import (BoundarySchemas, BoundaryRequest)
from api.models.boundary import Boundary

# Import processing functions
import sys
from pathlib import Path


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/boundary", tags=["boundary"])

@router.get("/all")
async def get_all_countries(db: Session = Depends(get_db)):
    query = text(
        """
        select * from boundary
    """
    )
    result = db.execute(query)
    data = []
    for row in result:
        data.append(
            BoundarySchemas(
                id=row.id,
                name=row.name,
                table=row.table
            )
        )
    return data


@router.get("/{id}")
async def get_all_countries(id: int, db: Session = Depends(get_db)):
    query = text(
        """
        select * from boundary
        where id = :id
    """
    )
    result = db.execute(query, {"id": id})
    data = []
    for row in result:
        data.append(
            BoundarySchemas(
                id=row.id,
                name=row.name,
                table=row.table
            )
        )
    return data


@router.post("/", tags=["🗺️ Boundary by Country"])
def get_boundary_by_country(req: BoundaryRequest, db: Session = Depends(get_db)):
    # 1. Cari informasi tabel dari boundary
    boundary = db.query(Boundary).filter(Boundary.id == req.country_id).first()
    if not boundary:
        raise HTTPException(status_code=404, detail="Boundary not found")

    # 2. Ambil nama tabel dari kolom 'table'
    table_name = boundary.table

    # 3. Buat query dinamis ke tabel tersebut
    query = text(f"SELECT * FROM {table_name}")
    result = db.execute(query)
    # 4. Ubah ke format list of dicts
    columns = result.keys()
    data = [dict(zip(columns, row)) for row in result.fetchall()]

    return {"table": table_name, "rows": data}