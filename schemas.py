from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional

class WeatherBase(BaseModel):
    user_input_location: str
    resolved_location: str
    latitude: float
    longitude: float
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    temp: float
    condition: str

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

    class Config:
        from_attributes = True
