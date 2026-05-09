import csv
import json
import os
import tempfile
import urllib.parse
from datetime import datetime
from typing import List

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.staticfiles import StaticFiles

import models
import schemas
import services
from database import engine, get_db

# Create the database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Weather App API",
    description="An API to fetch weather forecasts, generate AI insights, and manage historical search data.",
    version="1.0.0"
)

# Setup CORSMiddleware
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post(
    "/api/weather", 
    tags=["Weather"], 
    summary="Create Weather Report",
    description="Accepts a location string. Fetches location info, 5-day weather forecast, and generates an AI travel insight. Saves to DB and returns enriched discovery object."
)
async def create_weather_report(
    request: schemas.WeatherCreate,
    db: Session = Depends(get_db)
):
    # 1. Resolve Location
    location_data = await services.resolve_location(request.location)
    lat = location_data["lat"]
    lon = location_data["lon"]
    resolved_location = location_data["display_name"]
    
    # 2. Get Weather Data
    weather_data = await services.get_weather_data(lat, lon)
    temp = weather_data["average_temp"]
    condition = weather_data["primary_condition"]
    
    # 3. Generate AI Insight
    ai_insight = services.generate_ai_insight(temp, condition)
    
    # 4. Save to Database
    db_report = models.WeatherReport(
        user_input_location=request.location,
        resolved_location=resolved_location,
        latitude=lat,
        longitude=lon,
        start_date=request.start_date,
        end_date=request.end_date,
        temp=temp,
        condition=condition
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    # 5. Build Response
    encoded_query = urllib.parse.quote(f"{resolved_location} travel guide")
    discovery = {
        "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}",
        "youtube_travel_url": f"https://www.youtube.com/results?search_query={encoded_query}",
        "ai_insight": ai_insight
    }
    
    return {
        "report": schemas.WeatherResponse.model_validate(db_report),
        "discovery": discovery
    }

@app.get(
    "/api/history", 
    response_model=List[schemas.WeatherResponse], 
    tags=["History"],
    summary="Get Search History",
    description="Retrieves all historical weather requests saved in the database."
)
async def get_history(db: Session = Depends(get_db)):
    return db.query(models.WeatherReport).all()

@app.patch(
    "/api/history/{id}", 
    response_model=schemas.WeatherResponse, 
    tags=["History"],
    summary="Update Search History Record",
    description="Updates the user_input_location for an existing weather search record."
)
async def update_history(
    id: int, 
    update_data: schemas.WeatherUpdate, 
    db: Session = Depends(get_db)
):
    db_report = db.query(models.WeatherReport).filter(models.WeatherReport.id == id).first()
    if not db_report:
        raise HTTPException(status_code=404, detail="Record not found")
        
    db_report.user_input_location = update_data.user_input_location
    db.commit()
    db.refresh(db_report)
    return db_report

@app.delete(
    "/api/history/{id}", 
    status_code=status.HTTP_204_NO_CONTENT, 
    tags=["History"],
    summary="Delete Search History Record",
    description="Deletes a specific weather search record from the database."
)
async def delete_history(id: int, db: Session = Depends(get_db)):
    db_report = db.query(models.WeatherReport).filter(models.WeatherReport.id == id).first()
    if not db_report:
        raise HTTPException(status_code=404, detail="Record not found")
        
    db.delete(db_report)
    db.commit()
    return None

@app.get(
    "/api/export/{format}", 
    tags=["Export"],
    summary="Export Data",
    description="Export all database records in JSON or CSV format as a downloadable file."
)
async def export_data(format: str, db: Session = Depends(get_db)):
    if format not in ["json", "csv"]:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'json' or 'csv'.")
        
    records = db.query(models.WeatherReport).all()
    
    # We create a temporary file that will be deleted after the response is sent (if we were using background tasks, but standard OS temp dir usually cleans up)
    # FileResponse handles returning the file securely.
    fd, path = tempfile.mkstemp(suffix=f".{format}")
    
    if format == "json":
        data_list = [
            {
                "id": r.id,
                "user_input_location": r.user_input_location,
                "resolved_location": r.resolved_location,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "start_date": r.start_date.isoformat() if r.start_date else None,
                "end_date": r.end_date.isoformat() if r.end_date else None,
                "temp": r.temp,
                "condition": r.condition,
                "created_at": r.created_at.isoformat()
            }
            for r in records
        ]
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data_list, f, indent=4)
        
        return FileResponse(
            path=path, 
            media_type="application/json", 
            filename="weather_export.json"
        )
        
    elif format == "csv":
        with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
            if not records:
                # write empty csv if no records
                pass
            else:
                writer = csv.writer(f)
                # Header
                writer.writerow([
                    "id", "user_input_location", "resolved_location", 
                    "latitude", "longitude", "start_date", "end_date", 
                    "temp", "condition", "created_at"
                ])
                for r in records:
                    writer.writerow([
                        r.id, r.user_input_location, r.resolved_location,
                        r.latitude, r.longitude, 
                        r.start_date.isoformat() if r.start_date else "", 
                        r.end_date.isoformat() if r.end_date else "", 
                        r.temp, r.condition, r.created_at.isoformat()
                    ])
        
        return FileResponse(
            path=path, 
            media_type="text/csv", 
            filename="weather_export.csv"
        )

@app.get(
    "/api/health", 
    tags=["System"],
    summary="Health Check",
    description="Check the status of the database and external API connectivity."
)
async def health_check(db: Session = Depends(get_db)):
    health_status = {"status": "ok", "database": "unknown", "openweather_api": "unknown"}
    
    # 1. Check Database
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = "disconnected"
        health_status["status"] = "degraded"
        
    # 2. Check OpenWeather API (A simple lightweight request)
    try:
        async with services.httpx.AsyncClient() as client:
            url = f"{services.BASE_URL_GEO}/direct?q=London&limit=1&appid={services.OPENWEATHER_API_KEY}"
            response = await client.get(url, timeout=5.0)
            if response.status_code == 200:
                health_status["openweather_api"] = "connected"
            else:
                health_status["openweather_api"] = "invalid_key_or_error"
                health_status["status"] = "degraded"
    except Exception:
        health_status["openweather_api"] = "unreachable"
        health_status["status"] = "degraded"
        
    return health_status

# Serve Frontend
FRONTEND_DIR = "/home/abdelrahman/WeatherApp/Weather_Frontend/out"

if os.path.exists(FRONTEND_DIR):
    app.mount("/_next", StaticFiles(directory=f"{FRONTEND_DIR}/_next"), name="next")
    
    @app.get("/{full_path:path}", tags=["Frontend"])
    async def serve_frontend(full_path: str):
        # 1. Attempt to serve specific file if it exists in out
        file_path = os.path.join(FRONTEND_DIR, full_path)
        
        # Security check: Ensure file is within FRONTEND_DIR
        if not os.path.abspath(file_path).startswith(os.path.abspath(FRONTEND_DIR)):
             return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

        if os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # 2. Handle directories or extension-less paths (Next.js export style)
        # Check if full_path.html exists
        html_path = os.path.join(FRONTEND_DIR, f"{full_path}.html")
        if os.path.isfile(html_path):
            return FileResponse(html_path)
            
        # 3. Default to index.html for client-side routing
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
else:
    print(f"Warning: Frontend directory {FRONTEND_DIR} not found. UI will not be served.")

