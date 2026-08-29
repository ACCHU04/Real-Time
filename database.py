import psycopg2
import psycopg2.extras

# ─────────────────────────────────────────────
# Connection settings
# ─────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "phyphox_db",
    "user":     "postgres",
    "password": "Acchu@04"
}


def get_connection():
    """Open and return a new database connection."""
    return psycopg2.connect(**DB_CONFIG)


def insert_sensor_batch(conn, session_id: str, sensor_type: str, rows: list[dict]):
    """
    Bulk-insert sensor readings.

    Each row dict must have:
        time, x, y, z, magnitude   (for vector sensors)
      OR
        time, scalar                (for scalar sensors like light / proximity)
    """
    if not rows:
        return

    records = []
    for row in rows:
        records.append((
            session_id,
            sensor_type,
            row["time"],
            row.get("x"),
            row.get("y"),
            row.get("z"),
            row.get("magnitude"),
            row.get("scalar"),
        ))

    sql = """
        INSERT INTO sensor_readings
            (session_id, sensor_type, sensor_time, x, y, z, magnitude, scalar)
        VALUES %s
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, records, page_size=500)
    conn.commit()


def insert_metrics(conn, session_id: str, sensor_type: str, metrics: dict):
    """
    Insert one metrics snapshot per poll cycle.

    metrics dict must have: sample_count, avg_value, peak_value, std_value
    """
    sql = """
        INSERT INTO session_metrics
            (session_id, sensor_type, sample_count, avg_value, peak_value, std_value)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    with conn.cursor() as cur:
        cur.execute(sql, (
            session_id,
            sensor_type,
            metrics["sample_count"],
            metrics["avg_value"],
            metrics["peak_value"],
            metrics["std_value"],
        ))
    conn.commit()


def get_recent_readings(conn, sensor_type: str, n: int = 300) -> list[dict]:
    """Return last N readings for a given sensor type."""
    sql = """
        SELECT sensor_time, x, y, z, magnitude, scalar
        FROM sensor_readings
        WHERE sensor_type = %s
        ORDER BY id DESC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (sensor_type, n))
        rows = cur.fetchall()
    return [dict(r) for r in reversed(rows)]


def get_session_list(conn, limit: int = 10) -> list[dict]:
    """Return the most recent sessions with per-sensor stats."""
    sql = """
        SELECT
            session_id,
            sensor_type,
            COUNT(*)                                   AS readings,
            ROUND(AVG(COALESCE(magnitude, scalar))::numeric, 3) AS avg_val,
            ROUND(MAX(COALESCE(magnitude, scalar))::numeric, 3) AS peak_val,
            MIN(recorded_at)::text                     AS started
        FROM sensor_readings
        GROUP BY session_id, sensor_type
        ORDER BY MIN(recorded_at) DESC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (limit,))
        return [dict(r) for r in cur.fetchall()]


def get_live_stats(conn, sensor_type: str, session_id: str | None = None) -> dict:
    """Return aggregate stats for a sensor type (optionally scoped to session)."""
    where = "WHERE sensor_type = %s"
    params = [sensor_type]
    if session_id:
        where += " AND session_id = %s"
        params.append(session_id)

    sql = f"""
        SELECT
            COUNT(*)                                           AS total,
            ROUND(AVG(COALESCE(magnitude, scalar))::numeric, 4) AS avg_val,
            ROUND(MAX(COALESCE(magnitude, scalar))::numeric, 4) AS peak_val,
            ROUND(MIN(COALESCE(magnitude, scalar))::numeric, 4) AS min_val,
            ROUND(STDDEV(COALESCE(magnitude, scalar))::numeric, 4) AS std_val
        FROM sensor_readings
        {where}
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return dict(cur.fetchone())
