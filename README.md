# phyphox Real-Time Analytics

Real-time smartphone sensor data pipeline using **phyphox → Python → PostgreSQL → Streamlit**.

## Architecture

```
📱 Phone (phyphox)
      │  Wi-Fi
      ▼
🐍 Python  ──→  real-time analytics (avg, peak, std, RMS)
      │
      ▼
🐘 PostgreSQL
      │
      ▼
📊 Streamlit Dashboard  (auto-refresh every second)
```

## Project Structure

```
phyphox-realtime-analytics/
├── phyphox_realtime.py   # Sensor collector + analytics + DB writer
├── database.py           # PostgreSQL connection helpers
├── dashboard.py          # Streamlit live dashboard
├── analytics.py          # (analytics module — upcoming)
├── setup_db.sql          # Database + table creation script
├── requirements.txt      # Python dependencies
└── README.md
```

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. PostgreSQL
Create the database and tables:
```bash
psql -U postgres -c "CREATE DATABASE phyphox_db;"
psql -U postgres -d phyphox_db -f setup_db.sql
```

### 3. Configure credentials
In `database.py` and `dashboard.py`, set your PostgreSQL password:
```python
"password": "YOUR_POSTGRES_PASSWORD"
```

### 4. Configure phyphox IP
In `phyphox_realtime.py`, set your phone's IP:
```python
PHYPHOX_URL = "http://<YOUR_PHONE_IP>:8080"
```

### 5. Run

**Terminal 1 — data collector:**
```bash
python phyphox_realtime.py
```

**Terminal 2 — dashboard:**
```bash
streamlit run dashboard.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

## Database Schema

### `sensor_readings`
Raw accelerometer data from phyphox (X, Y, Z, absolute acceleration).

### `sensor_metrics`
Per-batch analytics computed by Python (average, peak, min, std deviation).

## Requirements
- Python 3.11+
- PostgreSQL 18
- phyphox app on Android/iOS
- Both devices on the same Wi-Fi network
