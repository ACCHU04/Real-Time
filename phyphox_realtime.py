import requests
import time
import uuid
import numpy as np
import database as db

# ============================================================
# CONFIGURATION
# ============================================================

PHYPHOX_URL = "http://192.168.1.3:8080"
SESSION_ID  = uuid.uuid4().hex[:8]
POLL_SEC    = 1

# Tracks last inserted timestamp per sensor so we only insert new rows
last_t = {
    "linear_acc": -1,
    "gyroscope":  -1,
    "light":      -1,
    "magnetic":   -1,
    "proximity":  -1,
    "attitude":   -1,
    "gravity":    -1,
}

total_rows = 0

print("=" * 60)
print("     PHYPHOX MULTI-SENSOR REAL-TIME ANALYTICS")
print("=" * 60)
print(f"Session ID : {SESSION_ID}")
print("Connecting to PostgreSQL...")

try:
    conn = db.get_connection()
    print("PostgreSQL : Connected OK")
except Exception as e:
    print(f"PostgreSQL : FAILED — {e}")
    raise SystemExit(1)

print("\nWaiting for phyphox measurement...\n")


# ============================================================
# HELPERS
# ============================================================

def fetch():
    """Pull all sensor buffers from phyphox in one HTTP request."""
    r = requests.get(
        f"{PHYPHOX_URL}/get",
        params={
            # Linear acceleration
            "lin_time": "full", "linX": "full", "linY": "full", "linZ": "full",
            # Gyroscope
            "gyr_time": "full", "gyrX": "full", "gyrY": "full", "gyrZ": "full",
            # Light
            "light_time": "full", "light": "full",
            # Magnetic field
            "mag_time": "full", "magX": "full", "magY": "full", "magZ": "full",
            # Proximity
            "prox_time": "full", "prox": "full",
            # Attitude (yaw/pitch/roll share same implicit time)
            "yaw": "full", "pitch": "full", "roll": "full",
            # Gravity
            "graT": "full", "graX": "full", "graY": "full", "graZ": "full",
        },
        timeout=5
    )
    r.raise_for_status()
    return r.json()


def buf(data, key):
    """Safely extract a buffer list from the phyphox response."""
    return data.get("buffer", {}).get(key, {}).get("buffer", [])


def new_vector_rows(times, xs, ys, zs, sensor_key):
    """Return only rows newer than last_t[sensor_key] with magnitude computed."""
    rows = []
    for i, t in enumerate(times):
        if t > last_t[sensor_key]:
            mag = float(np.sqrt(xs[i]**2 + ys[i]**2 + zs[i]**2))
            rows.append({"time": t, "x": xs[i], "y": ys[i], "z": zs[i], "magnitude": mag})
    return rows


def new_scalar_rows(times, values, sensor_key):
    """Return only rows newer than last_t[sensor_key] for scalar sensors."""
    rows = []
    for i, t in enumerate(times):
        if t > last_t[sensor_key]:
            rows.append({"time": t, "scalar": values[i]})
    return rows


def print_sensor(label, rows, value_key="magnitude"):
    if not rows:
        return
    vals = np.array([r[value_key] for r in rows])
    print(
        f"{label:<8} | New: {len(rows):4d} | "
        f"Current: {vals[-1]:8.4f} | "
        f"Avg: {np.mean(vals):8.4f} | "
        f"Peak: {np.max(vals):8.4f}"
    )


def save_sensor(sensor_type, rows, value_key="magnitude"):
    """Insert rows into DB and write a metrics snapshot."""
    global total_rows
    if not rows:
        return
    db.insert_sensor_batch(conn, SESSION_ID, sensor_type, rows)
    vals = np.array([r[value_key] for r in rows])
    db.insert_metrics(conn, SESSION_ID, sensor_type, {
        "sample_count": len(rows),
        "avg_value":    float(np.mean(vals)),
        "peak_value":   float(np.max(vals)),
        "std_value":    float(np.std(vals)),
    })
    total_rows += len(rows)


# ============================================================
# MAIN LOOP
# ============================================================

while True:
    try:
        data     = fetch()
        status   = data["status"]
        measuring = status["measuring"]

        if not measuring:
            print("Waiting for measurement to start...")
            time.sleep(POLL_SEC)
            continue

        # ── Linear Acceleration ──────────────────────────────
        lin_t = buf(data, "lin_time")
        lin_x = buf(data, "linX")
        lin_y = buf(data, "linY")
        lin_z = buf(data, "linZ")
        lin_rows = new_vector_rows(lin_t, lin_x, lin_y, lin_z, "linear_acc")
        if lin_rows:
            last_t["linear_acc"] = lin_rows[-1]["time"]
        print_sensor("LIN_ACC", lin_rows)
        save_sensor("linear_acc", lin_rows)

        # ── Gyroscope ────────────────────────────────────────
        gyr_t = buf(data, "gyr_time")
        gyr_x = buf(data, "gyrX")
        gyr_y = buf(data, "gyrY")
        gyr_z = buf(data, "gyrZ")
        gyr_rows = new_vector_rows(gyr_t, gyr_x, gyr_y, gyr_z, "gyroscope")
        if gyr_rows:
            last_t["gyroscope"] = gyr_rows[-1]["time"]
        print_sensor("GYRO", gyr_rows)
        save_sensor("gyroscope", gyr_rows)

        # ── Light ─────────────────────────────────────────────
        lgt_t = buf(data, "light_time")
        lgt_v = buf(data, "light")
        lgt_rows = new_scalar_rows(lgt_t, lgt_v, "light")
        if lgt_rows:
            last_t["light"] = lgt_rows[-1]["time"]
        print_sensor("LIGHT", lgt_rows, "scalar")
        save_sensor("light", lgt_rows, "scalar")

        # ── Magnetic Field ────────────────────────────────────
        mag_t = buf(data, "mag_time")
        mag_x = buf(data, "magX")
        mag_y = buf(data, "magY")
        mag_z = buf(data, "magZ")
        mag_rows = new_vector_rows(mag_t, mag_x, mag_y, mag_z, "magnetic")
        if mag_rows:
            last_t["magnetic"] = mag_rows[-1]["time"]
        print_sensor("MAGNETIC", mag_rows)
        save_sensor("magnetic", mag_rows)

        # ── Proximity ─────────────────────────────────────────
        prx_t = buf(data, "prox_time")
        prx_v = buf(data, "prox")
        prx_rows = new_scalar_rows(prx_t, prx_v, "proximity")
        if prx_rows:
            last_t["proximity"] = prx_rows[-1]["time"]
        print_sensor("PROXIMITY", prx_rows, "scalar")
        save_sensor("proximity", prx_rows, "scalar")

        # ── Attitude (yaw / pitch / roll) ─────────────────────
        # phyphox returns these as parallel arrays; we use index as time proxy
        yaw   = buf(data, "yaw")
        pitch = buf(data, "pitch")
        roll  = buf(data, "roll")
        if yaw and pitch and roll:
            # Fake timestamps using array index so last_t logic works
            n = min(len(yaw), len(pitch), len(roll))
            att_rows = []
            for i in range(n):
                t_proxy = float(i)
                if t_proxy > last_t["attitude"]:
                    att_rows.append({
                        "time": t_proxy,
                        "x": yaw[i], "y": pitch[i], "z": roll[i],
                        "magnitude": float(np.sqrt(yaw[i]**2 + pitch[i]**2 + roll[i]**2))
                    })
            if att_rows:
                last_t["attitude"] = att_rows[-1]["time"]
            print_sensor("ATTITUDE", att_rows)
            save_sensor("attitude", att_rows)

        # ── Gravity ───────────────────────────────────────────
        gra_t = buf(data, "graT")
        gra_x = buf(data, "graX")
        gra_y = buf(data, "graY")
        gra_z = buf(data, "graZ")
        gra_rows = new_vector_rows(gra_t, gra_x, gra_y, gra_z, "gravity")
        if gra_rows:
            last_t["gravity"] = gra_rows[-1]["time"]
        print_sensor("GRAVITY", gra_rows)
        save_sensor("gravity", gra_rows)

        print(f"  → DB total rows: {total_rows:,}")
        print()
        time.sleep(POLL_SEC)

    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
        time.sleep(2)

    except KeyboardInterrupt:
        print(f"\n{'─'*60}")
        print(f"Session {SESSION_ID} complete — {total_rows:,} total rows written.")
        print(f"{'─'*60}")
        conn.close()
        break

    except Exception as e:
        print(f"Error: {e}")
        import traceback; traceback.print_exc()
        time.sleep(2)