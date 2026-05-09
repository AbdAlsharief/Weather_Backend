import os
import httpx
from fastapi import HTTPException
from collections import Counter
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

if not OPENWEATHER_API_KEY:
    raise ValueError("OPENWEATHER_API_KEY is not set in the environment or .env file")
    
BASE_URL_GEO = "http://api.openweathermap.org/geo/1.0"
BASE_URL_WEATHER = "http://api.openweathermap.org/data/2.5"

async def resolve_location(query: str) -> dict:
    """
    Resolve location using OpenWeather Geocoding API.
    Handles City names, Zip codes, or Landmarks.
    """
    async with httpx.AsyncClient() as client:
        # Check if the query is coordinates (lat,lon)
        if "," in query:
            parts = [p.strip() for p in query.split(",")]
            if len(parts) == 2:
                try:
                    lat = float(parts[0])
                    lon = float(parts[1])
                    # Get the name using reverse geocoding
                    reverse_url = f"{BASE_URL_GEO}/reverse?lat={lat}&lon={lon}&limit=1&appid={OPENWEATHER_API_KEY}"
                    rev_resp = await client.get(reverse_url)
                    display_name = query
                    if rev_resp.status_code == 200 and rev_resp.json():
                        data = rev_resp.json()[0]
                        display_name = f"{data.get('name')}, {data.get('country')}"
                    
                    return {
                        "lat": lat,
                        "lon": lon,
                        "display_name": display_name
                    }
                except ValueError:
                    pass # Not coordinates, proceed to other checks

        # First, check if the query looks like a zip code (e.g., digits or format 'zip,country')
        # We will attempt the zip endpoint if it contains numbers and no spaces, otherwise direct endpoint
        is_zip = any(char.isdigit() for char in query) and "," in query

        if is_zip:
            # Try zip endpoint: /geo/1.0/zip?zip={zip code},{country code}&appid={API key}
            url = f"{BASE_URL_GEO}/zip?zip={query}&appid={OPENWEATHER_API_KEY}"
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                return {
                    "lat": data.get("lat"),
                    "lon": data.get("lon"),
                    "display_name": data.get("name")
                }

        # Fallback to direct endpoint for city names / landmarks
        url = f"{BASE_URL_GEO}/direct?q={query}&limit=1&appid={OPENWEATHER_API_KEY}"
        response = await client.get(url)

        if response.status_code == 200 and response.json():
            data = response.json()[0]
            display_name = f"{data.get('name')}"
            if data.get("state"):
                display_name += f", {data.get('state')}"
            if data.get("country"):
                display_name += f", {data.get('country')}"

            return {
                "lat": data.get("lat"),
                "lon": data.get("lon"),
                "display_name": display_name
            }

        raise HTTPException(
            status_code=404,
            detail="Location not found. Please try a more specific name or Zip Code."
        )

async def get_weather_data(lat: float, lon: float) -> dict:
    """
    Get weather data using OpenWeather 5-Day Forecast API.
    Extracts average temperature and primary weather condition.
    """
    url = f"{BASE_URL_WEATHER}/forecast?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to fetch weather data from OpenWeather API."
            )

        data = response.json()
        forecast_list = data.get("list", [])
        
        if not forecast_list:
            raise HTTPException(status_code=404, detail="No forecast data available.")

        # Calculate average temperature
        total_temp = sum(item["main"]["temp"] for item in forecast_list)
        average_temp = total_temp / len(forecast_list)

        # Determine primary weather condition (most common across the 5 days)
        conditions = [item["weather"][0]["main"] for item in forecast_list if item.get("weather")]
        primary_condition = Counter(conditions).most_common(1)[0][0] if conditions else "Unknown"

        # Process 5-day forecast (simplified to daily high/low)
        daily_data = {}
        for item in forecast_list:
            date_str = item.get("dt_txt").split(" ")[0]
            if date_str not in daily_data:
                daily_data[date_str] = {"temps": [], "conditions": []}
            daily_data[date_str]["temps"].append(item["main"]["temp"])
            daily_data[date_str]["conditions"].append(item["weather"][0]["main"])

        final_forecast = []
        for date_str in sorted(daily_data.keys())[:5]:
            day_data = daily_data[date_str]
            high = max(day_data["temps"])
            low = min(day_data["temps"])
            primary = Counter(day_data["conditions"]).most_common(1)[0][0]
            day_name = datetime.strptime(date_str, "%Y-%m-%d").strftime("%a").upper()
            
            final_forecast.append({
                "day": day_name,
                "date": date_str,
                "high": round(high, 1),
                "low": round(low, 1),
                "description": primary
            })

        return {
            "average_temp": round(average_temp, 2),
            "primary_condition": primary_condition,
            "humidity": forecast_list[0]["main"]["humidity"],
            "wind_speed": forecast_list[0]["wind"]["speed"],
            "pressure": forecast_list[0]["main"]["pressure"],
            "visibility": forecast_list[0]["visibility"],
            "forecast": final_forecast
        }


