import time
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import psycopg2
import streamlit as st

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="phyphox Live Analytics",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# CUSTOM CSS — Premium dark theme
# ============================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: #0a0e1a;
    color: #e2e8f0;
}

/* KPI cards */
.kpi-card {
    background: linear-gradient(135deg, #1a1f35 0%, #12172a 100%);
    border: 1px solid #2d3748;
    border-radius: 16px;
    padding: 20px 24px;
    text-align: center;
    box-shadow: 0 4px 24px rgba(0,0,0,0.3);
    transition: border-color 0.2s;
}
.kpi-card:hover { border-color: #4f6ef7; }
.kpi-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #718096;
    margin-bottom: 8px;
}
.kpi-value {
    font-size: 32px;
    font-weight: 700;
    color: #e2e8f0;
    line-height: 1;
}
.kpi-unit {
    font-size: 12px;
    color: #718096;
    margin-top: 4px;
}

/* Activity badge */
.activity-low  { background: #1a3a2a; border: 1px solid #2d6a4a; color: #68d391; border-radius: 8px; padding: 10px 18px; display:inline-block; font-weight:600; }
.activity-med  { background: #3a2e1a; border: 1px solid #6a4e2d; color: #f6ad55; border-radius: 8px; padding: 10px 18px; display:inline-block; font-weight:600; }
.activity-high { background: #3a1a1a; border: 1px solid #6a2d2d; color: #fc8181; border-radius: 8px; padding: 10px 18px; display:inline-block; font-weight:600; }

/* Section headers */
.section-header {
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #4f6ef7;
    margin: 28px 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #1e2540;
}

/* Divider */
hr { border-color: #1e2540 !important; }

/* Hide Streamlit branding */
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# DATABASE CONFIG
# ============================================================

DB_CONFIG = {
    "host":     "localhost",
    "dbname":   "phyphox_db",
    "user":     "postgres",
    "password": "YOUR_POSTGRES_PASSWORD",
    "port":     5432,
}


@st.cache_resource
def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def query(sql, params=None):
    conn = get_connection()
    return pd.read_sql_query(sql, conn, params=params)


# ============================================================
# DATA FETCHERS
# ============================================================

def get_metrics():
    return query("""
        SELECT
            COUNT(*)                             AS total_samples,
            ROUND(AVG(absolute_acceleration)::numeric, 4) AS avg_acc,
            ROUND(MAX(absolute_acceleration)::numeric, 4) AS peak_acc,
            ROUND(MIN(absolute_acceleration)::numeric, 4) AS min_acc,
            ROUND(STDDEV(absolute_acceleration)::numeric, 4) AS std_acc,
            ROUND(
                SQRT(AVG(absolute_acceleration * absolute_acceleration))::numeric, 4
            )                                    AS rms_acc
        FROM sensor_readings
    """)


def get_recent(n=600):
    df = query("""
        SELECT sensor_time, acc_x, acc_y, acc_z, absolute_acceleration
        FROM sensor_readings
        ORDER BY id DESC
        LIMIT %s
    """, params=(n,))
    return df.sort_values("sensor_time").reset_index(drop=True)


def get_session_list():
    return query("""
        SELECT
            session_id,
            COUNT(*)                        AS readings,
            ROUND(MAX(absolute_acceleration)::numeric, 3) AS peak,
            ROUND(AVG(absolute_acceleration)::numeric, 3) AS avg,
            MIN(recorded_at)::text          AS started
        FROM sensor_readings
        GROUP BY session_id
        ORDER BY MIN(recorded_at) DESC
        LIMIT 10
    """)


# ============================================================
# HEADER
# ============================================================

st.markdown("""
<div style="padding: 8px 0 24px 0;">
  <div style="font-size:28px; font-weight:700; color:#e2e8f0; letter-spacing:-0.5px;">
    📱 phyphox <span style="color:#4f6ef7;">Live Analytics</span>
  </div>
  <div style="font-size:13px; color:#718096; margin-top:4px;">
    Real-time smartphone acceleration · phyphox → Python → PostgreSQL → Streamlit
  </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# LOAD DATA
# ============================================================

try:
    metrics_df = get_metrics()
    df         = get_recent(600)
    sessions   = get_session_list()
except Exception as e:
    st.error(f"Database error: {e}")
    st.stop()

# Scalar metrics
total   = int(metrics_df["total_samples"].iloc[0] or 0)
avg_acc = float(metrics_df["avg_acc"].iloc[0] or 0)
peak    = float(metrics_df["peak_acc"].iloc[0] or 0)
min_acc = float(metrics_df["min_acc"].iloc[0] or 0)
std_acc = float(metrics_df["std_acc"].iloc[0] or 0)
rms_acc = float(metrics_df["rms_acc"].iloc[0] or 0)
current = float(df["absolute_acceleration"].iloc[-1]) if not df.empty else 0.0

# ============================================================
# KPI CARDS — row 1
# ============================================================

c1, c2, c3, c4, c5, c6 = st.columns(6)

cards = [
    (c1, "Current",  f"{current:.3f}", "m/s²"),
    (c2, "Average",  f"{avg_acc:.3f}", "m/s²"),
    (c3, "Peak",     f"{peak:.3f}",    "m/s²"),
    (c4, "RMS",      f"{rms_acc:.3f}", "m/s²"),
    (c5, "Std Dev",  f"{std_acc:.3f}", "m/s²"),
    (c6, "Samples",  f"{total:,}",     "total"),
]

for col, label, value, unit in cards:
    col.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-unit">{unit}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ============================================================
# ACTIVITY LEVEL
# ============================================================

if current < 0.5:
    badge_class = "activity-low"
    activity    = "STATIONARY  ·  Light / No movement"
    emoji       = "🟢"
elif current < 2.0:
    badge_class = "activity-med"
    activity    = "MODERATE  ·  Normal movement"
    emoji       = "🟡"
elif current < 8.0:
    badge_class = "activity-high"
    activity    = "ACTIVE  ·  Running / Vigorous movement"
    emoji       = "🔴"
else:
    badge_class = "activity-high"
    activity    = "INTENSE  ·  Impact / Strong shake"
    emoji       = "⚡"

st.markdown(f"""
<div class="{badge_class}">
  {emoji}&nbsp;&nbsp;{activity}&nbsp;&nbsp;·&nbsp;&nbsp;{current:.3f} m/s²
</div>
""", unsafe_allow_html=True)

# ============================================================
# PLOTLY THEME
# ============================================================

PLOT_BG   = "#0d1120"
PAPER_BG  = "#0a0e1a"
GRID_COL  = "#1e2540"
FONT_COL  = "#718096"

layout_base = dict(
    plot_bgcolor  = PLOT_BG,
    paper_bgcolor = PAPER_BG,
    font          = dict(color=FONT_COL, family="Inter"),
    margin        = dict(l=12, r=12, t=36, b=12),
    xaxis = dict(gridcolor=GRID_COL, zerolinecolor=GRID_COL),
    yaxis = dict(gridcolor=GRID_COL, zerolinecolor=GRID_COL),
    legend = dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0")),
)

# ============================================================
# CHART 1 — Absolute acceleration
# ============================================================

st.markdown('<div class="section-header">Absolute Acceleration · last 600 readings</div>',
            unsafe_allow_html=True)

if not df.empty:
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=df["sensor_time"], y=df["absolute_acceleration"],
        mode="lines",
        line=dict(color="#4f6ef7", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(79,110,247,0.08)",
        name="Absolute acc",
    ))
    # Avg reference line
    fig1.add_hline(y=avg_acc, line_dash="dot",
                   line_color="#f6ad55", annotation_text=f"avg {avg_acc:.3f}",
                   annotation_font_color="#f6ad55")
    fig1.update_layout(
        **layout_base,
        height=320,
        xaxis_title="Time (s)",
        yaxis_title="m/s²",
        title=dict(text="", x=0),
    )
    st.plotly_chart(fig1, use_container_width=True)

# ============================================================
# CHART 2 — X / Y / Z components
# ============================================================

st.markdown('<div class="section-header">X / Y / Z Components</div>',
            unsafe_allow_html=True)

if not df.empty:
    fig2 = go.Figure()
    colors = {"acc_x": "#fc8181", "acc_y": "#68d391", "acc_z": "#63b3ed"}
    labels = {"acc_x": "X", "acc_y": "Y", "acc_z": "Z"}
    for col, color in colors.items():
        fig2.add_trace(go.Scatter(
            x=df["sensor_time"], y=df[col],
            mode="lines",
            line=dict(color=color, width=1.2),
            name=labels[col],
        ))
    fig2.update_layout(
        **layout_base,
        height=300,
        xaxis_title="Time (s)",
        yaxis_title="m/s²",
    )
    st.plotly_chart(fig2, use_container_width=True)

# ============================================================
# CHART 3 — Acceleration distribution histogram
# ============================================================

col_hist, col_sessions = st.columns([1, 1])

with col_hist:
    st.markdown('<div class="section-header">Acceleration Distribution</div>',
                unsafe_allow_html=True)
    if not df.empty:
        fig3 = go.Figure()
        fig3.add_trace(go.Histogram(
            x=df["absolute_acceleration"],
            nbinsx=40,
            marker_color="#4f6ef7",
            marker_line=dict(color="#0a0e1a", width=0.5),
            opacity=0.85,
            name="Distribution",
        ))
        fig3.update_layout(
            **layout_base,
            height=280,
            xaxis_title="Acceleration (m/s²)",
            yaxis_title="Count",
            bargap=0.05,
        )
        st.plotly_chart(fig3, use_container_width=True)

# ============================================================
# SESSION TABLE
# ============================================================

with col_sessions:
    st.markdown('<div class="section-header">Recent Sessions</div>',
                unsafe_allow_html=True)
    if not sessions.empty:
        st.dataframe(
            sessions.rename(columns={
                "session_id": "Session",
                "readings":   "Readings",
                "peak":       "Peak m/s²",
                "avg":        "Avg m/s²",
                "started":    "Started",
            }),
            use_container_width=True,
            hide_index=True,
            height=280,
        )

# ============================================================
# LATEST READINGS TABLE
# ============================================================

st.markdown('<div class="section-header">Latest Readings</div>',
            unsafe_allow_html=True)

if not df.empty:
    tail = df.tail(10).copy()
    tail.columns = ["Time (s)", "X", "Y", "Z", "Absolute"]
    for c in ["X","Y","Z","Absolute"]:
        tail[c] = tail[c].map("{:.4f}".format)
    tail["Time (s)"] = tail["Time (s)"].map("{:.3f}".format)
    st.dataframe(tail, use_container_width=True, hide_index=True)

# ============================================================
# FOOTER + AUTO-REFRESH
# ============================================================

st.markdown("""
<div style="text-align:center; color:#2d3748; font-size:11px; margin-top:32px; padding-top:16px; border-top:1px solid #1e2540;">
  phyphox Real-Time Analytics · refreshes every second
</div>
""", unsafe_allow_html=True)

time.sleep(1)
st.rerun()
