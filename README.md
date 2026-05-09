# 🌦️ Weather Backend - Atmospheric AI

High-performance FastAPI service designed for the PM Accelerator Weather Dashboard. This backend handles meteorological data persistence, complex location resolution, and real-time synchronization with OpenWeather APIs.

## 🚀 Key Features
- **Data Persistence**: Integrated SQLite database using SQLAlchemy for full historical weather tracking.
- **Advanced Geocoding**: Custom service to resolve locations from strings or direct GPS coordinates (lat, lon).
- **Pydantic Validation**: Strict schema enforcement for data integrity and technical assessment compliance.
- **CORS Support**: Pre-configured for seamless integration with the Next.js frontend.

## 🛠️ Tech Stack
- **Framework**: FastAPI
- **Database**: SQLite / SQLAlchemy
- **HTTP Client**: HTTPX (Asynchronous requests)
- **Validation**: Pydantic v2
- **Environment**: Python 3.10+

## 📦 API Overview

### 📍 Resolve Location
`GET /resolve-location?query={location}`
Resolves a human-readable query or coordinates into a structured `LocationResult`.

### 📊 Fetch Weather
`GET /fetch-weather?location={loc}&start_date={s}&end_date={e}`
Fetches real-time and historical data for a specific time range.

### 📜 Weather History
`GET /history`
Retrieves all persisted reports from the local SQLite database.

## ⚙️ Setup Instructions

1. **Environment Setup**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **API Keys**:
   Create a `.env` file in this directory and add your OpenWeather key:
   ```env
   OPENWEATHER_API_KEY=your_key_here
   ```

3. **Run Server**:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

## 🏗️ Architecture
- `main.py`: Application entry point and API route definitions.
- `database.py`: SQLAlchemy engine, session, and base model configuration.
- `models.py`: Database table schemas (SQLAlchemy).
- `schemas.py`: Request/Response data structures (Pydantic).
- `services.py`: Core logic for external API integration and geocoding.
