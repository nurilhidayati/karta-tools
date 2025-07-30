# Example fix if some fields can be null
from typing import Optional, Dict, Any
from pydantic import BaseModel

class BoundarySchemas(BaseModel):
    id: int
    name: Optional[str]
    table: Optional[str]

class BoundaryRequest(BaseModel):
    country_id: int

class BoundaryDataResponse(BaseModel):
    message: Optional[str] = None
    rows: Optional[list[Dict[str, Any]]] = None
