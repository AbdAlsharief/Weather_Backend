from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from database import Base

class WeatherReport(Base):
    __tablename__ = "weather_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_input_location = Column(String, index=True)
    resolved_location = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    temp = Column(Float)
    condition = Column(String)
    humidity = Column(Integer, nullable=True)
    wind_speed = Column(Float, nullable=True)
    uv_index = Column(Float, nullable=True)
    pressure = Column(Integer, nullable=True)
    visibility = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
