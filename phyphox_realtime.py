import requests
import time
import uuid
import numpy as np
import database as db

PHYPHOX_URL = "http://192.168.1.3:8080"

# Unique ID for this recording session
SESSION_ID = uuid.uuid4().hex[:8]

last_time = -1
total_inserted = 0

print("======================================")
print("   PHYPHOX REAL-TIME SENSOR ANALYTICS")
print("======================================")
print(f"Session ID : {SESSION_ID}")
print("Connecting to PostgreSQL...")

try:
    conn = db.get_connection()
    print("PostgreSQL  : Connected OK")
except Exception as e:
    print(f"PostgreSQL  : FAILED — {e}")
    print("Fix database.py credentials and retry.")
    raise SystemExit(1)

print("Waiting for phyphox measurement...\n")

while True:

    try:
        response = requests.get(
            f"{PHYPHOX_URL}/get",
            params={
                "acc_time": "full",
                "accX":     "full",
                "accY":     "full",
                "accZ":     "full",
                "acc":      "full"
            },
            timeout=5
        )
        response.raise_for_status()
        data = response.json()

        measuring = data["status"]["measuring"]
        buffers   = data.get("buffer", {})

        if not measuring:
            print("Waiting for phyphox measurement to start...")
            time.sleep(1)
            continue

        # ── Pull buffers ───────────────────────────────────────────
        times      = buffers.get("acc_time", {}).get("buffer", [])
        x_values   = buffers.get("accX",     {}).get("buffer", [])
        y_values   = buffers.get("accY",     {}).get("buffer", [])
        z_values   = buffers.get("accZ",     {}).get("buffer", [])
        abs_values = buffers.get("acc",      {}).get("buffer", [])

        if not times:
            print("No sensor data yet...")
            time.sleep(1)
            continue

        # ── Find new readings since last poll ──────────────────────
        new_rows = [
            {
                "time":     times[i],
                "x":        x_values[i],
                "y":        y_values[i],
                "z":        z_values[i],
                "absolute": abs_values[i],
            }
            for i, t in enumerate(times)
            if t > last_time
        ]

        if not new_rows:
            time.sleep(1)
            continue

        last_time = new_rows[-1]["time"]

        # ── Analytics ─────────────────────────────────────────────
        absolute = np.array([r["absolute"] for r in new_rows])

        metrics = {
            "sample_count": len(new_rows),
            "current":      float(absolute[-1]),
            "average":      float(np.mean(absolute)),
            "peak":         float(np.max(absolute)),
            "minimum":      float(np.min(absolute)),
            "std_dev":      float(np.std(absolute)),
        }

        # ── Write to PostgreSQL ────────────────────────────────────
        db.insert_readings(conn, SESSION_ID, new_rows)
        db.insert_metrics(conn, SESSION_ID, metrics)
        total_inserted += len(new_rows)

        # ── Console output ─────────────────────────────────────────
        print(
            f"[{SESSION_ID}] "
            f"New: {metrics['sample_count']:4d} | "
            f"Current: {metrics['current']:6.3f} | "
            f"Avg: {metrics['average']:6.3f} | "
            f"Peak: {metrics['peak']:6.3f} | "
            f"Std: {metrics['std_dev']:6.3f} | "
            f"DB total: {total_inserted:,}"
        )

        time.sleep(1)

    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
        time.sleep(2)

    except KeyboardInterrupt:
        summary = db.get_session_summary(conn, SESSION_ID)
        print(f"\n{'─'*50}")
        print(f"Session {SESSION_ID} complete")
        print(f"  Total readings : {summary['total_readings']:,}")
        print(f"  Average acc    : {summary['avg_acc']} m/s²")
        print(f"  Peak acc       : {summary['peak_acc']} m/s²")
        print(f"  Min acc        : {summary['min_acc']} m/s²")
        print(f"{'─'*50}")
        conn.close()
        break

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(2)