# phyphox Multi-Sensor Real-Time Analytics

Real-time smartphone sensor data pipeline using **phyphox → Python → PostgreSQL → Streamlit**.

Streams **7 sensors simultaneously** from a custom phyphox experiment:
Gyroscope, Linear Acceleration, Light, Magnetic Field, Proximity, Attitude, Gravity.

## Architecture

```
📱 Phone (phyphox — My Experiment)
      │  Wi-Fi (HTTP polling)
      ▼
🐍 Python  ──→  magnitude + analytics (avg, peak, std) per sensor
      │
      ▼
🐘 PostgreSQL  (unified sensor_readings table)
      │
      ▼
📊 Streamlit Dashboard  (auto-refresh every second)
```

## Sensors

| Sensor | Buffers | Output |
|---|---|---|
| Linear Acceleration | lin_time, linX/Y/Z | magnitude + XYZ |
| Gyroscope | gyr_time, gyrX/Y/Z | rotation rate + XYZ |
| Light | light_time, light | lux (scalar) |
| Magnetic Field | mag_time, magX/Y/Z | magnitude + XYZ |
| Proximity | prox_time, prox | distance cm (scalar) |
| Attitude | yaw, pitch, roll | orientation angles |
| Gravity | graT, graX/Y/Z | magnitude ≈ 9.81 m/s² |

## Project Structure

```
phyphox-realtime-analytics/
├── phyphox_realtime.py   # Multi-sensor collector + DB writer
├── database.py           # PostgreSQL connection + query helpers
├── dashboard.py          # Streamlit live dashboard (7 sensor panels)
├── setup_db.sql          # Database schema (run once)
├── requirements.txt      # Python dependencies
└── README.md
```

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create the database
```bash
psql -U postgres -c "CREATE DATABASE phyphox_db;"
```

### 3. Apply the schema
```bash
psql -U postgres -d phyphox_db -f setup_db.sql
```

### 4. Configure credentials
In `database.py` and `dashboard.py`, set your PostgreSQL password:
```python
"password": "YOUR_POSTGRES_PASSWORD"
```

### 5. Set your phone's IP
In `phyphox_realtime.py`:
```python
PHYPHOX_URL = "http://<YOUR_PHONE_IP>:8080"
```

Find your phone's IP in phyphox: **experiment menu → Allow remote access**.

### 6. Configure phyphox
On your phone, create a custom experiment called **"My Experiment"** with these sensors enabled:
- Gyroscope
- Linear Acceleration
- Light
- Magnetic Field
- Proximity
- Attitude
- Gravity

### 7. Run

**Terminal 1 — data collector:**
```bash
python phyphox_realtime.py
```

**Terminal 2 — Streamlit dashboard:**
```bash
streamlit run dashboard.py
```

Open **http://localhost:8501** in your browser.

## Database Schema

### `sensor_readings`
One row per sensor sample. `sensor_type` column distinguishes sensors.

| Column | Type | Description |
|---|---|---|
| session_id | TEXT | UUID per run |
| sensor_type | TEXT | `linear_acc`, `gyroscope`, `light`, etc. |
| sensor_time | FLOAT | Timestamp from phyphox (seconds) |
| x, y, z | FLOAT | Vector components (NULL for scalar sensors) |
| magnitude | FLOAT | √(x²+y²+z²) for vector sensors |
| scalar | FLOAT | Raw value for light / proximity |

### `session_metrics`
One analytics snapshot per poll cycle per sensor (avg, peak, std).

## Requirements
- Python 3.11+
- PostgreSQL 14+
- phyphox app on Android/iOS
- Phone and PC on the same Wi-Fi network
