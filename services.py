import os
import httpx
from fastapi import HTTPException
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "your_api_key_here")
BASE_URL_GEO = "http://api.openweathermap.org/geo/1.0"
BASE_URL_WEATHER = "http://api.openweathermap.org/data/2.5"

async def resolve_location(query: str) -> dict:
    """
    Resolve location using OpenWeather Geocoding API.
    Handles City names, Zip codes, or Landmarks.
    """
    async with httpx.AsyncClient() as client:
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

        return {
            "average_temp": round(average_temp, 2),
            "primary_condition": primary_condition
        }

def generate_ai_insight(temp: float, condition: str) -> str:
    """
    Generate a travel tip or precaution based on temperature and weather condition.
    """
    insights = []

    # Temperature-based insights
    if temp > 30:
        insights.append("Extreme heat—stay hydrated and avoid midday sun.")
    elif temp > 25:
        insights.append("Warm weather—perfect for outdoor activities, but don't forget sunscreen.")
    elif temp < 0:
        insights.append("Freezing temperatures—dress in heavy layers to prevent frostbite.")
    elif temp < 10:
        insights.append("Cold weather—make sure to bring a warm coat.")
    else:
        insights.append("Mild temperatures—comfortable for most activities.")

    # Condition-based insights
    condition_lower = condition.lower()
    if "rain" in condition_lower or "drizzle" in condition_lower:
        insights.append("Expect rain; carrying an umbrella and wearing waterproof shoes is highly recommended.")
    elif "snow" in condition_lower:
        insights.append("Snowy conditions—drive carefully and wear winter boots.")
    elif "thunderstorm" in condition_lower:
        insights.append("Thunderstorms expected—seek shelter indoors and avoid open areas.")
    elif "clear" in condition_lower:
        insights.append("Clear skies ahead—great visibility and weather for sightseeing.")
    elif "cloud" in condition_lower:
        insights.append("Cloudy conditions—good for photos without harsh shadows, though a light jacket might help.")

    return " ".join(insights)
