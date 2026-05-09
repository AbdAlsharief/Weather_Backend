from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List

class ForecastDay(BaseModel):
    day: str
    date: str
    high: float
    low: float
    description: str


class WeatherBase(BaseModel):
    user_input_location: str
    resolved_location: str
    latitude: float
    longitude: float
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    temp: float
    condition: str
    humidity: Optional[int] = None
    wind_speed: Optional[float] = None
    uv_index: Optional[float] = None
    pressure: Optional[int] = None
    visibility: Optional[int] = None

class WeatherCreate(BaseModel):
    location: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v: Optional[datetime], info):
        if v and "start_date" in info.data and info.data["start_date"]:
            if v < info.data["start_date"]:
                raise ValueError("end_date must be greater than or equal to start_date")
        return v

class WeatherUpdate(BaseModel):
    user_input_location: str

class WeatherResponse(WeatherBase):
    id: int
    created_at: datetime
    forecast: Optional[List[ForecastDay]] = None

    class Config:
        from_attributes = True
