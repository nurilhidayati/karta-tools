from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from api.database.connection import Base

class Boundary(Base):
    """
    Generic boundary model that can represent countries, regions, or other administrative divisions
    """
    __tablename__ = "boundary"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    table = Column(String(255), index=True)  # Table name for geographic data
  