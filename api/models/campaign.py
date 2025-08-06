from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from api.database.connection import Base

class Campaign(Base):
    """
    Generic boundary model that can represent countries, regions, or other administrative divisions
    """
    __tablename__ = "campaign"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_name = Column(String(255), index=True, nullable=False)
    country = Column(String(255), index=True) 
    city = Column(String(255), index=True)
    ukm_plan = Column(Float, default=1.0)
    ukm_actual = Column(Float, default=1.0)
    persentase_ukm_actual = Column(Float, default=1.0)