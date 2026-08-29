-- ============================================
-- phyphox Real-Time Analytics - Database Setup
-- ============================================

-- Create database (run separately if needed)
-- CREATE DATABASE phyphox_db;

-- Connect to the database before running the rest:
-- \c phyphox_db

-- --------------------------------------------
-- Table 1: Raw sensor readings from phyphox
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS sensor_readings (
    id              BIGSERIAL PRIMARY KEY,
    session_id      VARCHAR(100),
    sensor_time     DOUBLE PRECISION,
    recorded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acc_x           DOUBLE PRECISION,
    acc_y           DOUBLE PRECISION,
    acc_z           DOUBLE PRECISION,
    absolute_acceleration DOUBLE PRECISION
);

-- Index for fast session-based queries
CREATE INDEX IF NOT EXISTS idx_sensor_readings_session
    ON sensor_readings (session_id);

CREATE INDEX IF NOT EXISTS idx_sensor_readings_time
    ON sensor_readings (sensor_time);

-- --------------------------------------------
-- Table 2: Computed analytics per batch
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS sensor_metrics (
    id                    BIGSERIAL PRIMARY KEY,
    session_id            VARCHAR(100),
    recorded_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sample_count          INTEGER,
    average_acceleration  DOUBLE PRECISION,
    peak_acceleration     DOUBLE PRECISION,
    minimum_acceleration  DOUBLE PRECISION,
    std_acceleration      DOUBLE PRECISION
);

-- Index for fast session-based queries
CREATE INDEX IF NOT EXISTS idx_sensor_metrics_session
    ON sensor_metrics (session_id);

-- --------------------------------------------
-- Verify
-- --------------------------------------------
SELECT 'sensor_readings' AS table_name, COUNT(*) AS rows FROM sensor_readings
UNION ALL
SELECT 'sensor_metrics',                COUNT(*)           FROM sensor_metrics;
