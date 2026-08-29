-- ============================================================
-- PHYPHOX MULTI-SENSOR SCHEMA
-- Run: psql -U postgres -d phyphox_db -f setup_db.sql
-- ============================================================

-- Drop old tables if they exist
DROP TABLE IF EXISTS sensor_metrics CASCADE;
DROP TABLE IF EXISTS sensor_readings CASCADE;
DROP TABLE IF EXISTS session_metrics CASCADE;

-- ============================================================
-- READINGS — one row per sensor sample
-- sensor_type: 'linear_acc' | 'gyroscope' | 'light' |
--              'magnetic' | 'proximity' | 'attitude' | 'gravity'
-- ============================================================

CREATE TABLE sensor_readings (
    id          BIGSERIAL PRIMARY KEY,
    session_id  TEXT             NOT NULL,
    sensor_type TEXT             NOT NULL,
    sensor_time DOUBLE PRECISION NOT NULL,
    x           DOUBLE PRECISION,   -- NULL for scalar sensors
    y           DOUBLE PRECISION,
    z           DOUBLE PRECISION,
    magnitude   DOUBLE PRECISION,   -- sqrt(x²+y²+z²) for vector sensors
    scalar      DOUBLE PRECISION,   -- lux / proximity for scalar sensors
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_readings_session_sensor
    ON sensor_readings (session_id, sensor_type);

CREATE INDEX idx_readings_sensor_time
    ON sensor_readings (sensor_time);

-- ============================================================
-- SESSION METRICS — one snapshot per poll per sensor type
-- ============================================================

CREATE TABLE session_metrics (
    id            BIGSERIAL PRIMARY KEY,
    session_id    TEXT             NOT NULL,
    sensor_type   TEXT             NOT NULL,
    sample_count  INT,
    avg_value     DOUBLE PRECISION,
    peak_value    DOUBLE PRECISION,
    std_value     DOUBLE PRECISION,
    recorded_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_metrics_session
    ON session_metrics (session_id, sensor_type);
