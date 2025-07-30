from tokenize import Name
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from api.database.connection  import Base

class Country(Base):
    __tablename__ = "country"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    table = Column(String(255), index=True)
    currency = Column(String(10), default="USD")
    currency_symbol = Column(String(5), default="$")
    ukm_price = Column(Float, default=8000.0)
    insurance_per_dax_per_month = Column(Float, default=132200.0)
    dataplan_per_dax_per_month = Column(Float, default=450000.0)
    exchange_rate_to_usd = Column(Float, default=1.0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationship to regions
    regions = relationship("Region", back_populates="country")

class Region(Base):
    __tablename__ = "region"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    country_id = Column(Integer, ForeignKey("country.id"))
    
    # Regional pricing adjustments (multipliers)
    ukm_price_multiplier = Column(Float, default=1.0)
    insurance_multiplier = Column(Float, default=1.0)
    dataplan_multiplier = Column(Float, default=1.0)
    
    # Additional regional costs
    regional_overhead = Column(Float, default=0.0)
    transportation_cost = Column(Float, default=0.0)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationship back to country
    country = relationship("Country", back_populates="regions")
   