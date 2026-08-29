import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import psycopg2
import psycopg2.extras
import streamlit as st

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="phyphox Multi-Sensor Analytics",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background: #080c18; color: #e2e8f0; }

/* KPI card */
.kpi-card {
    background: linear-gradient(135deg, #111827 0%, #0d1220 100%);
    border: 1px solid #1e2a45;
    border-radius: 14px;
    padding: 16px 18px;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    transition: border-color 0.2s, transform 0.15s;
    height: 100%;
}
.kpi-card:hover { border-color: #4f6ef7; transform: translateY(-2px); }
.kpi-label {
    font-size: 10px; font-weight: 600;
    letter-spacing: 1.4px; text-transform: uppercase;
    color: #4a5568; margin-bottom: 6px;
}
.kpi-value { font-size: 26px; font-weight: 700; color: #f0f4ff; line-height: 1.1; }
.kpi-unit  { font-size: 11px; color: #4a5568; margin-top: 3px; }
.kpi-sub   { font-size: 11px; color: #718096; margin-top: 4px; }

/* Sensor section header */
.sensor-header {
    display: flex; align-items: center; gap: 10px;
    font-size: 13px; font-weight: 600;
    letter-spacing: 1.2px; text-transform: uppercase;
    color: #4f6ef7;
    margin: 28px 0 10px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #1a2035;
}

/* Activity pill */
.pill {
    display: inline-block;
    padding: 6px 16px;
    border-radius: 999px;
    font-size: 12px; font-weight: 600;
    letter-spacing: 0.8px;
}
.pill-green  { background:#0d2a1a; border:1px solid #2d6a4a; color:#68d391; }
.pill-yellow { background:#2a2200; border:1px solid #6a5200; color:#f6e05e; }
.pill-orange { background:#2a1800; border:1px solid #6a3800; color:#f6ad55; }
.pill-red    { background:#2a0e0e; border:1px solid #6a2020; color:#fc8181; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
div[data-testid="stDecoration"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATABASE
# ============================================================

DB_CONFIG = {
    "host":     "localhost",
    "dbname":   "phyphox_db",
    "user":     "postgres",
    "password": "Acchu@04",
    "port":     5432,
}

@st.cache_resource
def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def qdf(sql, params=None):
    """Run a query and return a DataFrame."""
    try:
        conn = get_conn()
        return pd.read_sql_query(sql, conn, params=params)
    except Exception:
        # Reconnect once on failure
        st.cache_resource.clear()
        conn = get_conn()
        return pd.read_sql_query(sql, conn, params=params)

# ============================================================
# DATA FETCHERS
# ============================================================

SENSORS = ["linear_acc", "gyroscope", "light", "magnetic", "proximity", "attitude", "gravity"]

SENSOR_META = {
    "linear_acc": {"label": "Linear Acceleration", "icon": "📐", "unit": "m/s²",  "col": "#4f6ef7", "value": "magnitude"},
    "gyroscope":  {"label": "Gyroscope",            "icon": "🌀", "unit": "rad/s", "col": "#f687b3", "value": "magnitude"},
    "light":      {"label": "Light",                "icon": "💡", "unit": "lux",   "col": "#f6e05e", "value": "scalar"},
    "magnetic":   {"label": "Magnetic Field",        "icon": "🧲", "unit": "µT",   "col": "#68d391", "value": "magnitude"},
    "proximity":  {"label": "Proximity",             "icon": "📏", "unit": "cm",   "col": "#fc8181", "value": "scalar"},
    "attitude":   {"label": "Attitude (Yaw/Pitch/Roll)", "icon": "🛸", "unit": "rad","col": "#63b3ed", "value": "magnitude"},
    "gravity":    {"label": "Gravity",               "icon": "🌍", "unit": "m/s²", "col": "#a78bfa", "value": "magnitude"},
}

def get_recent(sensor_type, n=300):
    val_col = SENSOR_META[sensor_type]["value"]
    df = qdf("""
        SELECT sensor_time, x, y, z, magnitude, scalar
        FROM sensor_readings
        WHERE sensor_type = %s
        ORDER BY id DESC
        LIMIT %s
    """, (sensor_type, n))
    return df.sort_values("sensor_time").reset_index(drop=True)

def get_live_kpis(sensor_type):
    val_col = "COALESCE(magnitude, scalar)"
    row = qdf(f"""
        SELECT
            COUNT(*)                              AS total,
            ROUND(AVG({val_col})::numeric, 4)     AS avg_val,
            ROUND(MAX({val_col})::numeric, 4)     AS peak_val,
            ROUND(MIN({val_col})::numeric, 4)     AS min_val,
            ROUND(STDDEV({val_col})::numeric, 4)  AS std_val
        FROM sensor_readings
        WHERE sensor_type = %s
    """, (sensor_type,))
    return row.iloc[0] if not row.empty else None

def get_sessions():
    return qdf("""
        SELECT
            session_id,
            sensor_type,
            COUNT(*)                                        AS readings,
            ROUND(AVG(COALESCE(magnitude, scalar))::numeric,3) AS avg_val,
            ROUND(MAX(COALESCE(magnitude, scalar))::numeric,3) AS peak_val,
            MIN(recorded_at)::text                          AS started
        FROM sensor_readings
        GROUP BY session_id, sensor_type
        ORDER BY MIN(recorded_at) DESC
        LIMIT 35
    """)

# ============================================================
# PLOTLY THEME
# ============================================================

PLOT_BG  = "#0b0f1e"
PAPER_BG = "#080c18"
GRID_COL = "#141c32"
FONT_COL = "#4a5568"

def hex_to_rgba(hex_color: str, alpha: float = 0.08) -> str:
    """Convert '#rrggbb' + alpha float to 'rgba(r,g,b,a)' for Plotly."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def base_layout(height=260, xtitle="Time (s)", ytitle=""):
    return dict(
        plot_bgcolor=PLOT_BG,
        paper_bgcolor=PAPER_BG,
        font=dict(color=FONT_COL, family="Inter", size=11),
        margin=dict(l=8, r=8, t=30, b=8),
        height=height,
        xaxis=dict(
            title=xtitle, gridcolor=GRID_COL,
            zerolinecolor=GRID_COL, tickfont=dict(color=FONT_COL),
        ),
        yaxis=dict(
            title=ytitle, gridcolor=GRID_COL,
            zerolinecolor=GRID_COL, tickfont=dict(color=FONT_COL),
        ),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#718096")),
    )

def line_chart(df, x_col, y_cols, colors, names, height=260, fill_first=True):
    fig = go.Figure()
    for i, (yc, color, name) in enumerate(zip(y_cols, colors, names)):
        if yc not in df.columns:
            continue
        s = df[yc].dropna()
        if s.empty:
            continue
        fig.add_trace(go.Scatter(
            x=df[x_col], y=df[yc],
            mode="lines",
            line=dict(color=color, width=1.5),
            fill="tozeroy" if (i == 0 and fill_first) else "none",
            fillcolor=hex_to_rgba(color, 0.07) if (i == 0 and fill_first) else None,
            name=name,
        ))
    fig.update_layout(**base_layout(height=height))
    return fig

# ============================================================
# HEADER
# ============================================================

st.markdown("""
<div style="padding:6px 0 20px 0;">
  <div style="font-size:26px;font-weight:700;color:#f0f4ff;letter-spacing:-0.5px;">
    📡 phyphox <span style="color:#4f6ef7;">Multi-Sensor Analytics</span>
  </div>
  <div style="font-size:12px;color:#4a5568;margin-top:4px;">
    Real-time · 7 sensors · phyphox → Python → PostgreSQL → Streamlit
  </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# LOAD DATA
# ============================================================

all_data = {}
all_kpis = {}

has_any_data = False

for s in SENSORS:
    df  = get_recent(s, 300)
    kpi = get_live_kpis(s)
    all_data[s] = df
    all_kpis[s] = kpi
    if not df.empty:
        has_any_data = True

if not has_any_data:
    st.warning("⏳ No sensor data yet. Start **My Experiment** in phyphox and run `phyphox_realtime.py`.")

# ============================================================
# KPI STRIP — one card per sensor
# ============================================================

cols = st.columns(7)
for i, sensor in enumerate(SENSORS):
    meta = SENSOR_META[sensor]
    kpi  = all_kpis[sensor]
    df   = all_data[sensor]
    vcol = meta["value"]

    current = float(df[vcol].iloc[-1]) if (not df.empty and vcol in df.columns and df[vcol].notna().any()) else None
    avg_val = float(kpi["avg_val"]) if (kpi is not None and kpi["avg_val"] is not None) else None

    val_str = f"{current:.3f}" if current is not None else "—"
    avg_str = f"avg {avg_val:.3f}" if avg_val is not None else ""

    cols[i].markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">{meta['icon']} {meta['label'].split('(')[0].strip()}</div>
      <div class="kpi-value" style="color:{meta['col']};">{val_str}</div>
      <div class="kpi-unit">{meta['unit']}</div>
      <div class="kpi-sub">{avg_str}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ============================================================
# LINEAR ACCELERATION
# ============================================================

meta = SENSOR_META["linear_acc"]
st.markdown(f'<div class="sensor-header">{meta["icon"]} {meta["label"]}</div>', unsafe_allow_html=True)

df = all_data["linear_acc"]
if not df.empty:
    c1, c2 = st.columns([2, 1])
    with c1:
        fig = line_chart(df, "sensor_time", ["magnitude"], [meta["col"]], ["Magnitude"])
        kpi = all_kpis["linear_acc"]
        if kpi is not None and kpi["avg_val"] is not None:
            fig.add_hline(y=float(kpi["avg_val"]), line_dash="dot",
                          line_color="#f6ad55",
                          annotation_text=f"avg {float(kpi['avg_val']):.3f}",
                          annotation_font_color="#f6ad55")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig2 = line_chart(df, "sensor_time",
                          ["x", "y", "z"],
                          ["#fc8181", "#68d391", "#63b3ed"],
                          ["X", "Y", "Z"], fill_first=False)
        st.plotly_chart(fig2, use_container_width=True)
else:
    st.caption("No data yet for Linear Acceleration.")

# ============================================================
# GYROSCOPE
# ============================================================

meta = SENSOR_META["gyroscope"]
st.markdown(f'<div class="sensor-header">{meta["icon"]} {meta["label"]}</div>', unsafe_allow_html=True)

df = all_data["gyroscope"]
if not df.empty:
    c1, c2 = st.columns([2, 1])
    with c1:
        fig = line_chart(df, "sensor_time", ["magnitude"], [meta["col"]], ["Angular rate"])
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig2 = line_chart(df, "sensor_time",
                          ["x", "y", "z"],
                          ["#fc8181", "#68d391", "#63b3ed"],
                          ["X", "Y", "Z"], fill_first=False)
        st.plotly_chart(fig2, use_container_width=True)
else:
    st.caption("No data yet for Gyroscope.")

# ============================================================
# MAGNETIC FIELD  +  GRAVITY  (side by side)
# ============================================================

col_mag, col_grav = st.columns(2)

with col_mag:
    meta = SENSOR_META["magnetic"]
    st.markdown(f'<div class="sensor-header">{meta["icon"]} {meta["label"]}</div>', unsafe_allow_html=True)
    df = all_data["magnetic"]
    if not df.empty:
        fig = line_chart(df, "sensor_time", ["magnitude"], [meta["col"]], ["Magnitude"])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No data yet.")

with col_grav:
    meta = SENSOR_META["gravity"]
    st.markdown(f'<div class="sensor-header">{meta["icon"]} {meta["label"]}</div>', unsafe_allow_html=True)
    df = all_data["gravity"]
    if not df.empty:
        fig = line_chart(df, "sensor_time", ["magnitude"], [meta["col"]], ["Magnitude (≈9.81)"])
        fig.add_hline(y=9.81, line_dash="dot", line_color="#718096",
                      annotation_text="9.81 m/s²", annotation_font_color="#718096")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No data yet.")

# ============================================================
# ATTITUDE  (Yaw / Pitch / Roll)
# ============================================================

meta = SENSOR_META["attitude"]
st.markdown(f'<div class="sensor-header">{meta["icon"]} {meta["label"]}</div>', unsafe_allow_html=True)
df = all_data["attitude"]
if not df.empty:
    fig = line_chart(df, "sensor_time",
                     ["x", "y", "z"],
                     ["#63b3ed", "#68d391", "#f687b3"],
                     ["Yaw", "Pitch", "Roll"], height=240, fill_first=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("No data yet for Attitude.")

# ============================================================
# LIGHT  +  PROXIMITY  (side by side)
# ============================================================

col_light, col_prox = st.columns(2)

with col_light:
    meta = SENSOR_META["light"]
    st.markdown(f'<div class="sensor-header">{meta["icon"]} {meta["label"]}</div>', unsafe_allow_html=True)
    df = all_data["light"]
    if not df.empty:
        fig = line_chart(df, "sensor_time", ["scalar"], [meta["col"]], ["Lux"], height=220)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No data yet.")

with col_prox:
    meta = SENSOR_META["proximity"]
    st.markdown(f'<div class="sensor-header">{meta["icon"]} {meta["label"]}</div>', unsafe_allow_html=True)
    df = all_data["proximity"]
    if not df.empty:
        fig = line_chart(df, "sensor_time", ["scalar"], [meta["col"]], ["Distance (cm)"], height=220)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No data yet.")

# ============================================================
# RECENT SESSIONS TABLE
# ============================================================

st.markdown('<div class="sensor-header">📋 Recent Sessions</div>', unsafe_allow_html=True)
sessions_df = get_sessions()
if not sessions_df.empty:
    st.dataframe(
        sessions_df.rename(columns={
            "session_id":  "Session",
            "sensor_type": "Sensor",
            "readings":    "Readings",
            "avg_val":     "Avg",
            "peak_val":    "Peak",
            "started":     "Started",
        }),
        use_container_width=True,
        hide_index=True,
        height=280,
    )

# ============================================================
# FOOTER + AUTO-REFRESH
# ============================================================

st.markdown("""
<div style="text-align:center;color:#1e2a45;font-size:11px;
            margin-top:32px;padding-top:16px;border-top:1px solid #111827;">
  phyphox Multi-Sensor Analytics · auto-refreshes every second
</div>
""", unsafe_allow_html=True)

time.sleep(1)
st.rerun()
