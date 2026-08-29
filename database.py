import psycopg2
import psycopg2.extras

# ─────────────────────────────────────────────
# Connection settings — update password here
# ─────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "phyphox_db",
    "user":     "postgres",
    "password": "YOUR_POSTGRES_PASSWORD"
}


def get_connection():
    """Open and return a new database connection."""
    return psycopg2.connect(**DB_CONFIG)


def insert_readings(conn, session_id: str, rows: list[dict]):
    """
    Bulk-insert raw sensor readings into sensor_readings.

    Each row dict must have keys:
        time, x, y, z, absolute
    """
    if not rows:
        return

    records = [
        (
            session_id,
            row["time"],
            row["x"],
            row["y"],
            row["z"],
            row["absolute"],
        )
        for row in rows
    ]

    sql = """
        INSERT INTO sensor_readings
            (session_id, sensor_time, acc_x, acc_y, acc_z, absolute_acceleration)
        VALUES %s
    """

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, sql, records, page_size=500)
    conn.commit()


def insert_metrics(conn, session_id: str, metrics: dict):
    """
    Insert one analytics snapshot into sensor_metrics.

    metrics dict must have keys:
        sample_count, average, peak, minimum, std_dev
    """
    sql = """
        INSERT INTO sensor_metrics
            (session_id, sample_count,
             average_acceleration, peak_acceleration,
             minimum_acceleration, std_acceleration)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    with conn.cursor() as cur:
        cur.execute(sql, (
            session_id,
            metrics["sample_count"],
            metrics["average"],
            metrics["peak"],
            metrics["minimum"],
            metrics["std_dev"],
        ))
    conn.commit()


def get_session_summary(conn, session_id: str) -> dict:
    """Return aggregate stats for a session from the database."""
    sql = """
        SELECT
            COUNT(*)                        AS total_readings,
            ROUND(AVG(absolute_acceleration)::numeric, 4) AS avg_acc,
            ROUND(MAX(absolute_acceleration)::numeric, 4) AS peak_acc,
            ROUND(MIN(absolute_acceleration)::numeric, 4) AS min_acc
        FROM sensor_readings
        WHERE session_id = %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (session_id,))
        return dict(cur.fetchone())
