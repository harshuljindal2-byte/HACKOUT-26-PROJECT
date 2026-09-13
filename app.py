import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import json
import urllib.request
import urllib.error

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Aerosolar | AI Predictive Maintenance",
    page_icon="Aerosolar",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# INITIALIZE SESSION STATE FOR FLEET ASSETS
# ==========================================
if 'solar_assets' not in st.session_state:
    st.session_state.solar_assets = [
        {"Asset_ID": "SOLAR-P101", "Type": "Solar Panel Array A", "Capacity_kW": 250, "Soiling_%": 15.0, "Temp_C": 42.0},
        {"Asset_ID": "SOLAR-P102", "Type": "Solar Panel Array B", "Capacity_kW": 250, "Soiling_%": 12.0, "Temp_C": 38.5},
        {"Asset_ID": "SOLAR-P103", "Type": "Solar Panel Array C", "Capacity_kW": 500, "Soiling_%": 28.0, "Temp_C": 52.0},
        {"Asset_ID": "SOLAR-P104", "Type": "Solar Panel Array D", "Capacity_kW": 500, "Soiling_%": 8.0, "Temp_C": 32.5},
    ]

if 'wind_assets' not in st.session_state:
    st.session_state.wind_assets = [
        {"Asset_ID": "WIND-T201", "Type": "2.5MW Wind Turbine #1", "Capacity_kW": 2500, "Vibration_Hz": 22.0, "Gearbox_Temp_C": 58.0},
        {"Asset_ID": "WIND-T202", "Type": "2.5MW Wind Turbine #2", "Capacity_kW": 2500, "Vibration_Hz": 54.0, "Gearbox_Temp_C": 62.0},
        {"Asset_ID": "WIND-T203", "Type": "2.5MW Wind Turbine #3", "Capacity_kW": 2500, "Vibration_Hz": 32.0, "Gearbox_Temp_C": 61.2},
    ]

if 'maintenance_history' not in st.session_state:
    st.session_state.maintenance_history = [
        {
            "Ticket_ID": "WO-8939", 
            "Asset_ID": "SOLAR-P103", 
            "Category": "Solar Array", 
            "Issue": "Hotspotting & Soiling (28.0%)", 
            "Priority": "HIGH", 
            "Status": "Resolved", 
            "Technician": "Team Alpha (PV Specialist)", 
            "Date": "2026-09-10 10:30"
        },
        {
            "Ticket_ID": "WO-8940", 
            "Asset_ID": "WIND-T202", 
            "Category": "Wind Turbine", 
            "Issue": "Bearing Lubrication & High Vib (54.0 Hz)", 
            "Priority": "WARNING", 
            "Status": "In Progress", 
            "Technician": "Team Bravo (Mechanical)", 
            "Date": "2026-09-11 14:15"
        },
        {
            "Ticket_ID": "WO-8941", 
            "Asset_ID": "SOLAR-P101", 
            "Category": "Solar Array", 
            "Issue": "Inverter DC Voltage Drift", 
            "Priority": "NORMAL", 
            "Status": "Scheduled", 
            "Technician": "Team Charlie (Electrical)", 
            "Date": "2026-09-12 09:00"
        },
    ]

# Default Environmental States
if 'solar_irradiance' not in st.session_state:
    st.session_state.solar_irradiance = 950.0
if 'solar_ambient_temp' not in st.session_state:
    st.session_state.solar_ambient_temp = 34.0
if 'wind_ambient_speed' not in st.session_state:
    st.session_state.wind_ambient_speed = 12.0
if 'wind_ambient_temp' not in st.session_state:
    st.session_state.wind_ambient_temp = 32.0

# Tariff Constant
POWER_TARIFF_RS = 4.50  # ₹ / kWh

# ==========================================
# PHYSICS & ANOMALY EVALUATION ENGINE
# ==========================================
def evaluate_solar_fleet():
    solar_rows = []
    total_rev_loss = 0.0
    
    for item in st.session_state.solar_assets:
        soiling = float(item["Soiling_%"])
        temp = float(item["Temp_C"])
        cap = float(item["Capacity_kW"])
        
        # Physics STC temperature derating (-0.4% per °C above 25°C)
        temp_above_stc = max(0.0, temp - 25.0)
        stc_loss_pct = round(temp_above_stc * 0.4, 1)
        soiling_loss_pct = round(soiling * 0.6, 1)
        
        total_loss_pct = min(65.0, stc_loss_pct + soiling_loss_pct)
        eff_pct = round(max(35.0, 100.0 - total_loss_pct), 1)
        
        # Irradiance factor
        irrad_factor = st.session_state.solar_irradiance / 1000.0
        expected_power = round(cap * irrad_factor, 1)
        actual_power = round(expected_power * (eff_pct / 100.0), 1)
        power_loss_kw = round(max(0.0, expected_power - actual_power), 1)
        
        # Calculate daily loss (5 peak sun hours)
        daily_loss_rs = round(power_loss_kw * 5.0 * POWER_TARIFF_RS, 2)
        total_rev_loss += daily_loss_rs
        
        # Electrical metrics
        current_a = round((actual_power * 1000) / (400 * 1.732), 1)
        voltage_v = 400.0
        
        # Health status
        if soiling > 40.0 or temp > 60.0:
            status = "CRITICAL"
            health_score = max(20, int(100 - (soiling * 0.8 + temp * 0.5)))
        elif soiling > 22.0 or temp > 48.0:
            status = "WARNING"
            health_score = max(55, int(100 - (soiling * 0.6 + temp * 0.4)))
        else:
            status = "NORMAL"
            health_score = max(85, int(100 - (soiling * 0.3 + temp * 0.2)))
            
        solar_rows.append({
            "Asset_ID": item["Asset_ID"],
            "Type": item["Type"],
            "Capacity_kW": cap,
            "Soiling_%": soiling,
            "Temp_C": temp,
            "STC_Loss_%": stc_loss_pct,
            "Efficiency_%": eff_pct,
            "Expected_kW": expected_power,
            "Power_kW": actual_power,
            "Power_Loss_kW": power_loss_kw,
            "Current_A": current_a,
            "Voltage_V": voltage_v,
            "Daily_Loss_₹": daily_loss_rs,
            "Health_Score": health_score,
            "Status": status
        })
        
    return pd.DataFrame(solar_rows), total_rev_loss

def evaluate_wind_fleet():
    wind_rows = []
    total_rev_loss = 0.0
    
    for item in st.session_state.wind_assets:
        vib = float(item["Vibration_Hz"])
        g_temp = float(item["Gearbox_Temp_C"])
        cap = float(item["Capacity_kW"])
        
        rpm = round(max(0.0, 18.0 - (vib * 0.04)), 1)
        oil_press = round(max(1.2, 4.5 - (g_temp * 0.03)), 2)
        
        # Smart Weather Filter logic
        if g_temp > 82.0 or vib > 75.0:
            status = "CRITICAL"
            derate_factor = 0.60
            health_score = max(15, int(100 - (vib * 0.6 + g_temp * 0.5)))
        elif vib > 48.0 or g_temp > 68.0:
            if st.session_state.wind_ambient_speed >= 18.0 and g_temp <= 66.0:
                status = "NORMAL (Gust Filtered)"
                derate_factor = 0.0
                health_score = 88
            else:
                status = "WARNING"
                derate_factor = 0.30
                health_score = max(50, int(100 - (vib * 0.4 + g_temp * 0.3)))
        else:
            status = "NORMAL"
            derate_factor = 0.0
            health_score = max(85, int(100 - (vib * 0.2 + g_temp * 0.2)))
            
        daily_loss_rs = round(cap * derate_factor * 12.0 * POWER_TARIFF_RS, 2)
        total_rev_loss += daily_loss_rs
        
        wind_rows.append({
            "Asset_ID": item["Asset_ID"],
            "Type": item["Type"],
            "Capacity_kW": cap,
            "Vibration_Hz": vib,
            "Gearbox_Temp_C": g_temp,
            "RPM": rpm,
            "Oil_Pressure_bar": oil_press,
            "Daily_Loss_₹": daily_loss_rs,
            "Health_Score": health_score,
            "Status": status
        })
        
    return pd.DataFrame(wind_rows), total_rev_loss

# ==========================================
# LIVE GEMINI API CALLER
# ==========================================
def call_gemini_api(api_key: str, prompt_text: str) -> str:
    clean_key = str(api_key).strip().strip('"').strip("'").strip()
    if not clean_key:
        return "⚠️ API Error: Key is empty or formatted incorrectly."

    # Current supported active Gemini models (2026 specification)
    valid_models = ["gemini-1.5-flash", "gemini-2.5-flash", "gemini-3.6-flash", "gemini-1.5-pro"]
    
    # Method 1: Official google.generativeai SDK if available
    try:
        import google.generativeai as genai
        genai.configure(api_key=clean_key)
        for m in valid_models:
            try:
                model = genai.GenerativeModel(m)
                res = model.generate_content(prompt_text)
                if res and hasattr(res, "text") and res.text:
                    return res.text
            except Exception:
                continue
    except Exception:
        pass

    # Method 2: Direct REST API with 'x-goog-api-key' Header
    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }]
    }
    data = json.dumps(payload).encode('utf-8')
    
    primary_error = ""
    last_error = ""
    
    for m in valid_models:
        for api_ver in ["v1beta", "v1"]:
            attempts = [
                (
                    f"https://generativelanguage.googleapis.com/{api_ver}/models/{m}:generateContent",
                    {'Content-Type': 'application/json', 'x-goog-api-key': clean_key}
                ),
                (
                    f"https://generativelanguage.googleapis.com/{api_ver}/models/{m}:generateContent?key={clean_key}",
                    {'Content-Type': 'application/json'}
                )
            ]
            
            for url, headers in attempts:
                req = urllib.request.Request(url, data=data, headers=headers)
                try:
                    with urllib.request.urlopen(req, timeout=12) as response:
                        res_body = response.read().decode('utf-8')
                        res_json = json.loads(res_body)
                        if 'candidates' in res_json and len(res_json['candidates']) > 0:
                            cand = res_json['candidates'][0]
                            if 'content' in cand and 'parts' in cand['content']:
                                parts = cand['content']['parts']
                                if len(parts) > 0 and 'text' in parts[0]:
                                    return parts[0]['text']
                except urllib.error.HTTPError as he:
                    try:
                        err_body = he.read().decode('utf-8')
                        err_json = json.loads(err_body)
                        msg = err_json.get('error', {}).get('message', he.reason)
                    except Exception:
                        msg = he.reason
                    
                    err_str = f"HTTP {he.code}: {msg}"
                    
                    # Stop immediately on key auth/permission failures
                    if he.code in (400, 401, 403):
                        return f"⚠️ **Gemini API Key Error ({he.code})**: {msg}"
                    
                    # Ignore 404 for deprecated models and keep checking next model
                    if he.code == 404:
                        continue
                        
                    if not primary_error:
                        primary_error = f"{m}: {err_str}"
                    last_error = err_str
                except Exception as e:
                    err_str = str(e)
                    if not primary_error:
                        primary_error = f"{m}: {err_str}"
                    last_error = err_str

    final_err = primary_error if primary_error else last_error
    return f"⚠️ **Gemini API Call Status**: {final_err}"

# ==========================================
# SIDEBAR CONTROLS
# ==========================================
st.sidebar.title("Aerosolar")
st.sidebar.caption("AI Predictive Maintenance Fleet Platform")
st.sidebar.markdown("---")

st.sidebar.subheader("Site Selection")
site = st.sidebar.selectbox(
    "Energy Complex", 
    [
        "Gujarat Hybrid Energy Park (Site Beta)",
        "Rajasthan Solar & Wind Complex (Site Alpha)"
    ],
    key="sb_site_select"
)

st.sidebar.markdown("---")
st.sidebar.subheader("Data Pipeline")
ingestion_mode = st.sidebar.radio(
    "Data Ingestion Stream", 
    [
        "Simulated IoT Stream", 
        "Live MQTT Industrial Feed (Requires physical IoT sensors & real-time telemetry data)"
    ],
    key="sb_data_pipeline"
)

if "Live MQTT" in ingestion_mode:
    st.sidebar.success("Connected: `mqtt.aerosolar-fleet.io:1883`")
    st.sidebar.caption("Topic: `renewable/farm1/telemetry` | QoS 1 (Requires connected physical hardware sensors and active data stream)")

st.sidebar.markdown("---")
use_ai_api = st.sidebar.checkbox("Enable Live Gemini AI Diagnostics", value=False, key="sb_use_ai_api")
api_key = ""

def get_gemini_api_key() -> str:
    # Key name variations to look for across secrets and env
    KEY_NAMES = [
        "GEMINI_API_KEY", "gemini_api_key",
        "GOOGLE_API_KEY", "google_api_key",
        "GEMINI_KEY", "gemini_key",
        "API_KEY", "api_key"
    ]

    def clean(val):
        if not val:
            return ""
        return str(val).strip().strip('"').strip("'").strip()

    # 1. Check Streamlit Secrets (Flat & Nested)
    try:
        if hasattr(st, "secrets"):
            for kn in KEY_NAMES:
                if kn in st.secrets:
                    res = clean(st.secrets[kn])
                    if res:
                        return res
            for sec_name in st.secrets:
                try:
                    sec = st.secrets[sec_name]
                    if isinstance(sec, dict) or hasattr(sec, "get"):
                        for kn in KEY_NAMES:
                            val = sec.get(kn) if hasattr(sec, "get") else None
                            res = clean(val)
                            if res:
                                return res
                except Exception:
                    pass
    except Exception:
        pass

    # 2. Check OS Environment Variables
    import os
    for kn in KEY_NAMES:
        res = clean(os.environ.get(kn, ""))
        if res:
            return res

    # 3. Direct Local File Scanner (.streamlit/secrets.toml, .env, secrets.txt, etc.)
    import os, re
    possible_paths = [
        ".streamlit/secrets.toml",
        ".streamlit/secrets.toml.txt",
        ".streamlit/secrets.txt",
        "secrets.toml",
        "secrets.txt",
        ".env",
        ".env.local"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                for kn in KEY_NAMES:
                    for line in content.splitlines():
                        if "=" in line and kn.lower() in line.lower() and not line.strip().startswith("#"):
                            parts = line.split("=", 1)
                            if len(parts) == 2 and parts[0].strip().lower() == kn.lower():
                                res = clean(parts[1])
                                if res:
                                    return res
            except Exception:
                pass

    return ""

if use_ai_api:
    api_key = get_gemini_api_key()
    if api_key:
        st.sidebar.success("⚡ Live Gemini AI Key Active")
    else:
        st.sidebar.warning("⚠️ No GEMINI_API_KEY detected in .streamlit/secrets.toml or environment variables.\n\nRunning in Offline Expert Engine Mode.")

# ==========================================
# UNIVERSAL THEME-ADAPTIVE STYLING & BANNER
# ==========================================
dark_banner_url = "https://images.unsplash.com/photo-1466611653911-95081537e5b7?auto=format&fit=crop&w=1920&q=80"
light_banner_url = "https://images.unsplash.com/photo-1508514177221-188b1cf16e9d?auto=format&fit=crop&w=1920&q=80"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }}
    
    [data-testid="stAppViewContainer"] {{
        background-color: var(--background-color) !important;
        color: var(--text-color) !important;
    }}
    
    [data-testid="stHeader"] {{
        background-color: rgba(0, 0, 0, 0);
    }}
    
    section[data-testid="stSidebar"] {{
        background-color: var(--secondary-background-color) !important;
        color: var(--text-color) !important;
    }}
    
    /* Dynamic Theme-Adaptive Banner Styling */
    .top-header-banner {{
        background-color: var(--secondary-background-color) !important;
        background-image: linear-gradient(135deg, var(--secondary-background-color), var(--background-color)), url('https://images.unsplash.com/photo-1466611653911-95081537e5b7?auto=format&fit=crop&w=1920&q=80') !important;
        background-blend-mode: soft-light !important;
        background-size: cover !important;
        background-position: center !important;
        border-radius: 12px !important;
        padding: 1.8rem 2rem !important;
        margin-bottom: 1.5rem !important;
        border: 1px solid rgba(128, 128, 128, 0.25) !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08) !important;
    }}
    .top-header-banner .main-header {{
        color: var(--text-color) !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        margin-bottom: 0.15rem !important;
    }}
    .top-header-banner .sub-header {{
        color: var(--text-color) !important;
        opacity: 0.85 !important;
        font-size: 0.92rem !important;
        margin-bottom: 0 !important;
    }}
    
    /* Universal Cards & Containers */
    .calc-card, .metric-container, .diag-card, div[data-testid="stMetric"], div[data-testid="stMetricContainer"] {{
        background-color: var(--secondary-background-color) !important;
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
        padding: 0.85rem 0.9rem !important;
        color: var(--text-color) !important;
        box-sizing: border-box !important;
        min-height: 105px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
    }}
    
    div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] * {{
        color: var(--text-color) !important;
        opacity: 0.85;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.03em !important;
        margin-bottom: 0.25rem !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        width: 100% !important;
        line-height: 1.25 !important;
    }}
    
    div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] * {{
        color: var(--text-color) !important;
        font-size: 1.35rem !important;
        font-weight: 700 !important;
        line-height: 1.25 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }}
    
    div[data-testid="stMetricDelta"], div[data-testid="stMetricDelta"] * {{
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        margin-top: 0.2rem !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }}
    
    
    /* Equal Height Column Containers */
    [data-testid="stColumn"] {{
        display: flex !important;
        flex-direction: column !important;
    }}
    [data-testid="stColumn"] > div {{
        flex: 1 !important;
        display: flex !important;
        flex-direction: column !important;
    }}
    [data-testid="stColumn"] [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stColumn"] [data-testid="stContainer"] {{
        height: 100% !important;
        flex: 1 !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: space-between !important;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        background-color: var(--secondary-background-color) !important;
        border-radius: 8px;
        padding: 4px;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# MAIN DASHBOARD TOP HEADER BANNER
# ==========================================
st.markdown(f"""
<div class="top-header-banner">
    <div class="main-header">Aerosolar: Fleet Monitoring & Intelligence</div>
    <div class="sub-header">Real-time Telemetry, Predictive Anomaly Engine & Financial Loss Analysis | Site: <b>{site}</b></div>
</div>
""", unsafe_allow_html=True)

# Evaluate Fleets
df_solar, solar_rev_loss = evaluate_solar_fleet()
df_wind, wind_rev_loss = evaluate_wind_fleet()

total_assets = len(df_solar) + len(df_wind)
solar_critical = (df_solar['Status'] == 'CRITICAL').sum()
solar_warning = (df_solar['Status'] == 'WARNING').sum()
wind_critical = (df_wind['Status'] == 'CRITICAL').sum()
wind_warning = (df_wind['Status'] == 'WARNING').sum()

total_critical = int(solar_critical + wind_critical)
total_warning = int(solar_warning + wind_warning)
gust_filtered_count = int((df_wind['Status'] == 'NORMAL (Gust Filtered)').sum())
optimal_count = total_assets - total_critical - total_warning - gust_filtered_count

total_daily_rev_loss = int(solar_rev_loss + wind_rev_loss)
total_power_output_kw = round(df_solar['Power_kW'].sum() + (len(df_wind) * 2125.0), 1)

# KPI Metrics Row
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric(label="Total Fleet Assets", value=f"{total_assets}")
with col2:
    st.metric(label="Active Fleet Output", value=f"{total_power_output_kw:,.0f} kW")
with col3:
    st.metric(label="Optimal / Filtered", value=f"{optimal_count + gust_filtered_count}", delta=f"{gust_filtered_count} Filtered" if gust_filtered_count > 0 else None)
with col4:
    st.metric(label="Flagged Anomalies", value=f"{total_warning + total_critical}", delta=f"-{total_warning + total_critical} Action Required" if (total_warning + total_critical) > 0 else "Nominal", delta_color="inverse")
with col5:
    st.metric(label="Est. Daily Loss", value=f"₹{total_daily_rev_loss:,}", delta_color="inverse")


    # # TABS NAVIGATION
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Solar Operations", 
    "Wind Operations", 
    "AI Diagnostic Assistant", 
    "Performance Analytics & ROI",
    "Asset Control & Inspector", 
    "Maintenance Logs"
])

# Helper for pandas table formatting
def apply_status_style(styler):
    def highlight_status(val):
        if val == 'CRITICAL':
            return 'background-color: rgba(220, 38, 38, 0.15); color: #DC2626; font-weight: 600;'
        elif val == 'WARNING':
            return 'background-color: rgba(217, 119, 6, 0.15); color: #D97706; font-weight: 600;'
        elif val == 'NORMAL (Gust Filtered)':
            return 'background-color: rgba(2, 132, 199, 0.15); color: #0284C7; font-weight: 600;'
        return 'background-color: rgba(22, 163, 74, 0.15); color: #16A34A; font-weight: 600;'
    
    if hasattr(styler, 'map'):
        return styler.map(highlight_status, subset=['Status'])
    else:
        return styler.applymap(highlight_status, subset=['Status'])

# ------------------------------------------
# TAB 1: SOLAR OPERATIONS
# ------------------------------------------
with tab1:
    st.subheader("Solar PV Operations & Environmental Control")
    
    s_col_env, s_col_tbl = st.columns([1, 2])
    
    with s_col_env:
        with st.container(border=True):
            st.markdown("#### Solar Environmental Controls")
            st.session_state.solar_irradiance = st.slider(
                "Irradiance (W/m²)", min_value=200.0, max_value=1200.0, 
                value=float(st.session_state.solar_irradiance), step=25.0,
                key="tab1_irradiance_slider"
            )
            st.session_state.solar_ambient_temp = st.slider(
                "Ambient Temp (°C)", min_value=15.0, max_value=55.0, 
                value=float(st.session_state.solar_ambient_temp), step=1.0,
                key="tab1_temp_slider"
            )
            st.caption("Physics Derating: -0.4% efficiency per °C above 25°C STC standard.")
        
    with s_col_tbl:
        df_solar, solar_rev_loss = evaluate_solar_fleet()
        st.dataframe(apply_status_style(df_solar.style), use_container_width=True)
        
    st.markdown("---")
    
    col_s_g1, col_s_g2 = st.columns(2)
    with col_s_g1:
        with st.container(border=True):
            st.markdown("##### **Solar Generation vs Derating Loss (kW)**")
            fig_solar_pwr = px.bar(
                df_solar, x="Asset_ID", y=["Power_kW", "Power_Loss_kW"],
                labels={"value": "Power (kW)", "variable": "Component"},
                color_discrete_map={"Power_kW": "#22C55E", "Power_Loss_kW": "#EF4444"},
                height=300
            )
            fig_solar_pwr.update_layout(
                font_family="Inter", 
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_solar_pwr, use_container_width=True)
        
    with col_s_g2:
        with st.container(border=True):
            st.markdown("##### ️ **Solar Thermal Derating: Efficiency vs Temperature (°C)**")
            fig_solar_eff = px.scatter(
                df_solar, x="Temp_C", y="Efficiency_%", size="Capacity_kW", color="Status",
                color_discrete_map={"NORMAL": "#22C55E", "WARNING": "#F59E0B", "CRITICAL": "#EF4444"},
                labels={"Temp_C": "Cell Temp (°C)", "Efficiency_%": "Efficiency (%)"},
                height=300
            )
            fig_solar_eff.add_vline(x=25.0, line_dash="dash", line_color="#0284C7", annotation_text="STC 25°C Baseline")
            fig_solar_eff.update_layout(
                font_family="Inter", 
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_solar_eff, use_container_width=True)

# ------------------------------------------
# TAB 2: WIND OPERATIONS
# ------------------------------------------
with tab2:
    st.subheader("Wind Turbine Operations & Weather Filter")
    
    w_col_env, w_col_tbl = st.columns([1, 2])
    
    with w_col_env:
        with st.container(border=True):
            st.markdown("#### Wind Environmental Controls")
            st.session_state.wind_ambient_speed = st.slider(
                "Ambient Wind Speed (m/s)", min_value=5.0, max_value=32.0, 
                value=float(st.session_state.wind_ambient_speed), step=0.5,
                key="tab2_wind_speed_slider"
            )
            st.session_state.wind_ambient_temp = st.slider(
                "Ambient Temp (°C)", min_value=15.0, max_value=50.0, 
                value=float(st.session_state.wind_ambient_temp), step=1.0,
                key="tab2_wind_temp_slider"
            )
            
            if st.session_state.wind_ambient_speed >= 18.0:
                st.info(f"Smart Weather Filter Active: Wind speed ({st.session_state.wind_ambient_speed} m/s) suppresses false alarms for high gust vibration.")
        
    with w_col_tbl:
        df_wind, wind_rev_loss = evaluate_wind_fleet()
        st.dataframe(apply_status_style(df_wind.style), use_container_width=True)
        
    st.markdown("---")
    
    col_w_g1, col_w_g2 = st.columns(2)
    with col_w_g1:
        with st.container(border=True):
            st.markdown("##### ️ **Wind Stress Matrix: Vibration (Hz) vs Gearbox Temp (°C)**")
            fig_wind_stress = px.scatter(
                df_wind, x="Vibration_Hz", y="Gearbox_Temp_C", color="Status", size="Capacity_kW",
                color_discrete_map={"NORMAL": "#22C55E", "NORMAL (Gust Filtered)": "#0284C7", "WARNING": "#F59E0B", "CRITICAL": "#EF4444"},
                height=300
            )
            fig_wind_stress.add_hline(y=68.0, line_dash="dot", line_color="#F59E0B", annotation_text="Warning (68°C)")
            fig_wind_stress.add_hline(y=82.0, line_dash="dot", line_color="#EF4444", annotation_text="Critical (82°C)")
            fig_wind_stress.update_layout(
                font_family="Inter", 
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_wind_stress, use_container_width=True)
        
    with col_w_g2:
        with st.container(border=True):
            st.markdown("##### ️ **Turbine Mechanical State: Rotor RPM & Oil Pressure**")
            fig_wind_mech = make_subplots(specs=[[{"secondary_y": True}]])
            fig_wind_mech.add_trace(
                go.Bar(x=df_wind["Asset_ID"], y=df_wind["RPM"], name="Rotor Speed (RPM)", marker_color="#0284C7"),
                secondary_y=False
            )
            fig_wind_mech.add_trace(
                go.Scatter(x=df_wind["Asset_ID"], y=df_wind["Oil_Pressure_bar"], name="Oil Pressure (bar)", mode="lines+markers", line=dict(color="#F59E0B", width=3)),
                secondary_y=True
            )
            fig_wind_mech.update_layout(
                font_family="Inter",
                xaxis_title="Wind Turbine Asset ID",
                legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
                margin=dict(l=20, r=20, t=20, b=60),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=300
            )
            fig_wind_mech.update_yaxes(title_text="Rotor Speed (RPM)", secondary_y=False)
            fig_wind_mech.update_yaxes(title_text="Oil Pressure (bar)", secondary_y=True)
            st.plotly_chart(fig_wind_mech, use_container_width=True)

# ------------------------------------------
# TAB 3: AI DIAGNOSTIC ASSISTANT
# ------------------------------------------
with tab3:
    st.subheader("Generative AI Maintenance Diagnostic Engine")
    st.write("Select an asset from the dedicated Solar or Wind diagnostics tab to generate multi-modal root cause analysis, threshold comparisons, and automated work orders.")
    
    diag_solar_tab, diag_wind_tab = st.tabs(["️ Solar Asset Diagnostics", "️ Wind Asset Diagnostics"])
    
    with diag_solar_tab:
        solar_asset_list = df_solar["Asset_ID"].tolist()
        selected_solar_id = st.selectbox("Select Solar Array:", solar_asset_list, key="sel_solar_diag")
        solar_row = df_solar[df_solar["Asset_ID"] == selected_solar_id].iloc[0]
        
        st.markdown(f"#### Asset Status: `{solar_row['Status']}` | Health Score: **{solar_row['Health_Score']}/100**")
        
        d_s_col1, d_s_col2 = st.columns([2, 1])
        with d_s_col1:
            with st.container(border=True):
                st.markdown("##### Live Telemetry & Engineering Context")
                st.write(f"- **Irradiance**: {st.session_state.solar_irradiance} W/m² | **Cell Surface Temp**: {solar_row['Temp_C']}°C")
                st.write(f"- **Soiling Rate**: {solar_row['Soiling_%']}% | **STC Thermal Loss**: -{solar_row['STC_Loss_%']}%")
                st.write(f"- **Current Output**: {solar_row['Current_A']} A @ {solar_row['Voltage_V']} V DC | **Delivered Power**: {solar_row['Power_kW']} kW (Loss: {solar_row['Power_Loss_kW']} kW)")
            
            # Threshold chart for solar
            solar_thresh_df = pd.DataFrame([
                {"Metric": "Soiling (%)", "Value": solar_row['Soiling_%'], "Warning_Limit": 22.0, "Critical_Limit": 40.0},
                {"Metric": "Temp (°C)", "Value": solar_row['Temp_C'], "Warning_Limit": 48.0, "Critical_Limit": 60.0}
            ])
            with st.container(border=True):
                st.markdown(f"##### **Telemetry vs Safety Limits ({selected_solar_id})**")
                fig_s_thresh = px.bar(
                    solar_thresh_df, x="Value", y="Metric", orientation="h", text="Value", height=200
                )
                fig_s_thresh.update_layout(
                    font_family="Inter", 
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig_s_thresh, use_container_width=True)
            
        with d_s_col2:
            with st.container(border=True):
                st.markdown("##### Financial Exposure")
                st.metric("Est. Daily Loss", f"₹{int(solar_row['Daily_Loss_₹']):,}")
                st.metric("30-Day Financial Risk", f"₹{int(solar_row['Daily_Loss_₹'] * 30):,}")
                st.caption("Tariff Basis: ₹4.50/kWh @ 5 Peak Sun Hours")
            
        if st.button("Generate Solar AI Diagnostic Report", key="btn_ai_solar"):
            with st.spinner("Calling Gemini API & Analyzing Inverter Logs..."):
                prompt_solar = f"""Act as a Chief Solar PV Reliability Engineer.
Analyze anomaly on Solar Array {selected_solar_id}:
- Soiling Rate: {solar_row['Soiling_%']}%
- Cell Temperature: {solar_row['Temp_C']}°C
- STC Thermal Loss: {solar_row['STC_Loss_%']}%
- Delivered Power: {solar_row['Power_kW']} kW (Expected: {solar_row['Expected_kW']} kW)
- Health Score: {solar_row['Health_Score']}/100

Provide:
1) Precise Root Cause Analysis (2 concise sentences)
2) 3-Step Field Technician Dispatch Checklist
3) Recommended Safety Equipment & Replacement Components
4) Estimated Financial Loss in INR per day"""

                if use_ai_api and api_key:
                    ai_out = call_gemini_api(api_key, prompt_solar)
                    if ai_out.startswith("⚠️"):
                        st.warning(ai_out)
                        st.markdown("---")
                        st.markdown("### 🤖 Rule-Based Expert Engine Diagnostic Output")
                        show_solar_fallback = True
                    else:
                        st.markdown("### 🌟 Live Gemini API Diagnostic Result")
                        st.write(ai_out)
                        show_solar_fallback = False
                else:
                    show_solar_fallback = True

                if show_solar_fallback:
                    st.markdown("### Automated AI Diagnostic Report")
                    res_s1, res_s2 = st.columns([2, 1])
                    with res_s1:
                        st.markdown("#### **1. Root Cause Identification**")
                        st.write(f"Elevated particulate soiling ({solar_row['Soiling_%']}%) and thermal cell expansion ({solar_row['Temp_C']}°C) are inducing string mismatching and thermal hotspotting. STC thermal derating accounts for a {solar_row['STC_Loss_%']}% efficiency drop.")
                        st.markdown("#### **2. Technician Dispatch Checklist**")
                        st.markdown("1. **Step 1**: Deploy microfiber automated cleaning robot to clear glass dust array.")
                        st.markdown("2. **Step 2**: Perform thermal imaging check on string junction boxes to identify bypass diode degradation.")
                        st.markdown("3. **Step 3**: Re-balance DC string inverter input channels and verify VOC voltage stability.")
                        st.markdown("#### **3. Required Equipment & Parts**")
                        st.write("- Dry Microfiber Solar Panel Washing Unit")
                        st.write("- FLIR Thermal Imaging Camera & Replacement Bypass Diodes")
                    with res_s2:
                        st.error(f"Priority: **{solar_row['Status']} DISPATCH**")
                        st.metric("Est. Daily Loss", f"₹{int(solar_row['Daily_Loss_₹']):,}")
                        st.metric("30-Day Risk", f"₹{int(solar_row['Daily_Loss_₹'] * 30):,}")
                        st.metric("Health Score", f"{solar_row['Health_Score']}/100")
                        st.caption("Recommended Dispatch Window: Within 12 Hours")
                        if st.button("Dispatch WhatsApp Work Order", key="wo_solar_btn"):
                            new_wo_id = f"WO-{np.random.randint(9000, 9999)}"
                            st.session_state.maintenance_history.insert(0, {
                                "Ticket_ID": new_wo_id,
                                "Asset_ID": selected_solar_id,
                                "Category": "Solar Array",
                                "Issue": f"Hotspotting & Soiling ({solar_row['Soiling_%']}%)",
                                "Priority": "HIGH" if solar_row['Status'] == "CRITICAL" else "WARNING",
                                "Status": "In Progress",
                                "Technician": "Team Alpha (PV Specialist)",
                                "Date": datetime.now().strftime("%Y-%m-%d %H:%M")
                            })
                            st.success(f"Work Order {new_wo_id} dispatched to Lead Technician for {selected_solar_id}!")

    with diag_wind_tab:
        wind_asset_list = df_wind["Asset_ID"].tolist()
        selected_wind_id = st.selectbox("Select Wind Turbine:", wind_asset_list, key="sel_wind_diag")
        wind_row = df_wind[df_wind["Asset_ID"] == selected_wind_id].iloc[0]
        
        st.markdown(f"#### Asset Status: `{wind_row['Status']}` | Health Score: **{wind_row['Health_Score']}/100**")
        
        d_w_col1, d_w_col2 = st.columns([2, 1])
        with d_w_col1:
            with st.container(border=True):
                st.markdown("##### Live Telemetry & Engineering Context")
                st.write(f"- **Nacelle Vibration**: {wind_row['Vibration_Hz']} Hz | **Gearbox Temp**: {wind_row['Gearbox_Temp_C']}°C")
                st.write(f"- **Rotor Speed**: {wind_row['RPM']} RPM | **Hydraulic Oil Pressure**: {wind_row['Oil_Pressure_bar']} bar")
                st.write(f"- **Ambient Wind Speed**: {st.session_state.wind_ambient_speed} m/s | **Weather Filter**: {'Active (Gust Suppressed)' if 'Gust' in wind_row['Status'] else 'Standard Monitoring'}")
            
            wind_thresh_df = pd.DataFrame([
                {"Metric": "Vibration (Hz)", "Value": wind_row['Vibration_Hz'], "Warning_Limit": 48.0, "Critical_Limit": 75.0},
                {"Metric": "Gearbox Temp (°C)", "Value": wind_row['Gearbox_Temp_C'], "Warning_Limit": 68.0, "Critical_Limit": 82.0}
            ])
            with st.container(border=True):
                st.markdown(f"##### **Telemetry vs Safety Limits ({selected_wind_id})**")
                fig_w_thresh = px.bar(
                    wind_thresh_df, x="Value", y="Metric", orientation="h", text="Value", height=200
                )
                fig_w_thresh.update_layout(
                    font_family="Inter", 
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig_w_thresh, use_container_width=True)
            
        with d_w_col2:
            with st.container(border=True):
                st.markdown("##### Financial Exposure")
                st.metric("Est. Daily Loss", f"₹{int(wind_row['Daily_Loss_₹']):,}")
                st.metric("30-Day Financial Risk", f"₹{int(wind_row['Daily_Loss_₹'] * 30):,}")
                st.caption("Tariff Basis: ₹4.50/kWh @ 12 Operational Hours")
            
        if st.button("Generate Wind AI Diagnostic Report", key="btn_ai_wind"):
            with st.spinner("Calling Gemini API & Analyzing Nacelle Vibration Spectrum..."):
                prompt_wind = f"""Act as a Chief Wind Turbine Mechanical Engineer.
Analyze anomaly on Wind Turbine {selected_wind_id}:
- Nacelle Vibration: {wind_row['Vibration_Hz']} Hz
- Gearbox Temperature: {wind_row['Gearbox_Temp_C']}°C
- Rotor RPM: {wind_row['RPM']} RPM
- Oil Pressure: {wind_row['Oil_Pressure_bar']} bar
- Ambient Wind Speed: {st.session_state.wind_ambient_speed} m/s
- Health Score: {wind_row['Health_Score']}/100

Provide:
1) Precise Mechanical Root Cause (2 concise sentences)
2) 3-Step Urgent Field Maintenance Action Plan
3) Required Heavy Repair Tools & Spare Bearing Parts
4) Estimated Financial Loss in INR per day"""

                if use_ai_api and api_key:
                    ai_out = call_gemini_api(api_key, prompt_wind)
                    if ai_out.startswith("⚠️"):
                        st.warning(ai_out)
                        st.markdown("---")
                        st.markdown("### 🤖 Rule-Based Expert Engine Diagnostic Output")
                        show_wind_fallback = True
                    else:
                        st.markdown("### 🌟 Live Gemini API Diagnostic Result")
                        st.write(ai_out)
                        show_wind_fallback = False
                else:
                    show_wind_fallback = True

                if show_wind_fallback:
                    st.markdown("### Automated AI Diagnostic Report")
                    res_w1, res_w2 = st.columns([2, 1])
                    with res_w1:
                        st.markdown("#### **1. Root Cause Identification**")
                        st.write(f"Mechanical bearing friction and main high-speed drive shaft resonance (Vibration: {wind_row['Vibration_Hz']} Hz, Gearbox Temp: {wind_row['Gearbox_Temp_C']}°C). Elevated temperature confirms physical bearing scuffing rather than a transient wind gust.")
                        st.markdown("#### **2. Technician Action Plan**")
                        st.markdown("1. **Step 1**: Curtail turbine output to idling speed (8 RPM) to prevent shaft lockup.")
                        st.markdown("2. **Step 2**: Take gear oil sample for metal particulate debris analysis and perform oil flush.")
                        st.markdown("3. **Step 3**: Re-torque gearbox mounting bolts and inspect high-speed shaft roller bearings.")
                        st.markdown("#### **3. Required Equipment & Parts**")
                        st.write("- ISO VG 320 Synthetic Gear Lubricant (50L)")
                        st.write("- SKF Spherical Roller Bearing & Hydraulic Torque Wrench")
                    with res_w2:
                        st.error(f"Priority: **{wind_row['Status']} DISPATCH**")
                        st.metric("Est. Daily Loss", f"₹{int(wind_row['Daily_Loss_₹']):,}")
                        st.metric("30-Day Risk", f"₹{int(wind_row['Daily_Loss_₹'] * 30):,}")
                        st.metric("Health Score", f"{wind_row['Health_Score']}/100")
                        st.caption("Recommended Dispatch Window: Within 6 Hours")
                        if st.button("Dispatch WhatsApp Work Order", key="wo_wind_btn"):
                            new_wo_id = f"WO-{np.random.randint(9000, 9999)}"
                            st.session_state.maintenance_history.insert(0, {
                                "Ticket_ID": new_wo_id,
                                "Asset_ID": selected_wind_id,
                                "Category": "Wind Turbine",
                                "Issue": f"Bearing Wear & High Vib ({wind_row['Vibration_Hz']} Hz)",
                                "Priority": "HIGH" if wind_row['Status'] == "CRITICAL" else "WARNING",
                                "Status": "In Progress",
                                "Technician": "Team Bravo (Mechanical)",
                                "Date": datetime.now().strftime("%Y-%m-%d %H:%M")
                            })
                            st.success(f"Work Order {new_wo_id} dispatched to Lead Technician for {selected_wind_id}!")

# ------------------------------------------
# TAB 4: PERFORMANCE ANALYTICS & ROI
# ------------------------------------------
with tab4:
    st.subheader("Performance Analytics & Financial ROI Intelligence")
    st.write("Detailed financial modeling, 5-year ROI projections, and customizable tariff scenario planning.")
    
    # Key Summary Cards
    roi_kpi1, roi_kpi2, roi_kpi3, roi_kpi4 = st.columns(4)
    with roi_kpi1:
        st.metric(label="5-Year Net ROI Savings", value="₹76.5 Lakhs", delta="+312% ROI")
    with roi_kpi2:
        st.metric(label="O&M Cost Reduction", value="66%", delta="-₹12.3 Lakhs/Yr")
    with roi_kpi3:
        st.metric(label="Unplanned Downtime", value="85 Hrs/Yr", delta="-81% Reduction")
    with roi_kpi4:
        st.metric(label="Estimated Payback", value="3.5 Months", delta="Instant Value")
        
    st.markdown("---")
    
    # 5-Year Financial Comparison Chart
    col_roi1, col_roi2 = st.columns([1.6, 1])
    
    with col_roi1:
        with st.container(border=True):
            st.markdown("##### **5-Year Cumulative Financial ROI Projection (Lakhs ₹)**")
            years = ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"]
            reactive_costs = [18.5, 37.0, 55.5, 74.0, 92.5]  # Lakhs ₹
            predictive_costs = [6.0, 12.0, 18.0, 24.0, 30.0]  # Lakhs ₹
            net_savings = [12.5, 25.0, 37.5, 50.0, 62.5]     # Lakhs ₹
            
            fig_roi_main = go.Figure()
            fig_roi_main.add_trace(go.Bar(
                x=years, y=reactive_costs, name="Reactive Maintenance Cost", marker_color="#EF4444",
                text=[f"₹{v:.1f}L" for v in reactive_costs], textposition="auto"
            ))
            fig_roi_main.add_trace(go.Bar(
                x=years, y=predictive_costs, name="Aerosolar Predictive Cost", marker_color="#0284C7",
                text=[f"₹{v:.1f}L" for v in predictive_costs], textposition="auto"
            ))
            fig_roi_main.add_trace(go.Scatter(
                x=years, y=net_savings, name="Cumulative Net Savings",
                line=dict(color="#22C55E", width=3, dash="solid"), mode="lines+markers+text",
                text=[f"₹{v:.1f}L" for v in net_savings], textposition="top center"
            ))
            
            fig_roi_main.update_layout(
                barmode="group",
                font_family="Inter",
                xaxis=dict(title="Timeline Projection", showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
                yaxis=dict(title="Financial Amount (Lakhs ₹)", showgrid=True, gridcolor="rgba(128,128,128,0.15)", range=[0, 115]),
                legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5, font=dict(size=11)),
                margin=dict(l=20, r=20, t=20, b=70),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=380
            )
            st.plotly_chart(fig_roi_main, use_container_width=True)
        
    with col_roi2:
        st.markdown("#### Comparative O&M Metrics")
        roi_metrics_table = pd.DataFrame({
            "Metric": ["Unplanned Downtime", "Annual O&M Cost", "Asset Lifespan", "Catastrophic Failure Rate"],
            "Reactive Strategy": ["450 Hours/Yr", "₹18.5 Lakhs/Yr", "15 Years", "8.5%"],
            "Aerosolar AI": ["85 Hours/Yr", "₹6.2 Lakhs/Yr", "22 Years", "0.8%"],
            "Net Impact": ["-81%", "-66%", "+46%", "-90%"]
        })
        st.table(roi_metrics_table)
        
    st.markdown("---")
    
    # Interactive ROI Calculator
    st.markdown("#### Interactive Custom Scenario & Tariff Simulator")
    st.caption("Adjust custom power tariffs and farm capacity parameters to project financial savings.")
    
    sim_col1, sim_col2, sim_col3 = st.columns(3)
    with sim_col1:
        sim_tariff = st.slider("Power Tariff Rate (₹/kWh)", min_value=2.5, max_value=8.5, value=4.5, step=0.25, key="roi_tariff_slider")
    with sim_col2:
        sim_capacity_mw = st.slider("Total Farm Capacity (MW)", min_value=1.0, max_value=50.0, value=10.0, step=1.0, key="roi_cap_slider")
    with sim_col3:
        sim_prevent_pct = st.slider("Target Failure Prevention Rate (%)", min_value=40.0, max_value=95.0, value=80.0, step=5.0, key="roi_prevent_slider")
        
    # Projected Annual Savings Calculation
    est_annual_gen_mwh = sim_capacity_mw * 1000 * 4.5 * 365 / 1000  # MWh/yr
    est_annual_loss_mwh = est_annual_gen_mwh * 0.08               # 8% baseline losses
    saved_mwh = est_annual_loss_mwh * (sim_prevent_pct / 100.0)
    saved_lakhs_rs = round((saved_mwh * 1000 * sim_tariff) / 100000.0, 2)
    payback_months = round(max(1.2, 12.0 * (5.0 / saved_lakhs_rs)), 1)
    
    calc_res1, calc_res2, calc_res3 = st.columns(3)
    with calc_res1:
        st.metric(label="Projected Annual Energy Saved", value=f"{int(saved_mwh):,} MWh")
    with calc_res2:
        st.metric(label="Projected Annual Revenue Recovered", value=f"₹{saved_lakhs_rs} Lakhs")
    with calc_res3:
        st.metric(label="Estimated Payback Period", value=f"{payback_months} Months")

# ------------------------------------------
# TAB 5: ASSET CONTROL & INSPECTOR
# ------------------------------------------
with tab5:
    st.subheader("Asset Telemetry Inspector & Live Parameter Editor")
    st.write("Select an individual asset to view and adjust its telemetry parameters directly, or add a new asset to the fleet.")
    
    insp_col1, insp_col2 = st.columns([1, 1])
    
    with insp_col1:
        st.markdown("#### Inspect & Adjust Asset")
        
        all_solar_ids = [item["Asset_ID"] for item in st.session_state.solar_assets]
        all_wind_ids = [item["Asset_ID"] for item in st.session_state.wind_assets]
        selected_asset_id = st.selectbox("Select Asset to Adjust:", all_solar_ids + all_wind_ids, key="sel_insp_asset")
        
        if "SOLAR" in selected_asset_id:
            asset_idx = next(i for i, item in enumerate(st.session_state.solar_assets) if item["Asset_ID"] == selected_asset_id)
            current_item = st.session_state.solar_assets[asset_idx]
            
            st.info(f"Editing Solar Array: **{current_item['Type']}** ({current_item['Capacity_kW']} kW)")
            
            new_soiling = st.slider(f"Soiling Level for {selected_asset_id} (%)", 0.0, 80.0, float(current_item["Soiling_%"]), 1.0, key="insp_soiling_slider")
            new_temp = st.slider(f"Surface Temp for {selected_asset_id} (°C)", 20.0, 80.0, float(current_item["Temp_C"]), 0.5, key="insp_temp_slider")
            
            if st.button("Apply Sensor Updates", key="btn_update_solar"):
                st.session_state.solar_assets[asset_idx]["Soiling_%"] = new_soiling
                st.session_state.solar_assets[asset_idx]["Temp_C"] = new_temp
                st.success(f"Updated telemetry for {selected_asset_id}!")
                st.rerun()
                
        else:
            asset_idx = next(i for i, item in enumerate(st.session_state.wind_assets) if item["Asset_ID"] == selected_asset_id)
            current_item = st.session_state.wind_assets[asset_idx]
            
            st.info(f"Editing Wind Turbine: **{current_item['Type']}** ({current_item['Capacity_kW']} kW)")
            
            new_vib = st.slider(f"Vibration for {selected_asset_id} (Hz)", 5.0, 120.0, float(current_item["Vibration_Hz"]), 1.0, key="insp_vib_slider")
            new_gtemp = st.slider(f"Gearbox Temp for {selected_asset_id} (°C)", 30.0, 105.0, float(current_item["Gearbox_Temp_C"]), 0.5, key="insp_gtemp_slider")
            
            if st.button("Apply Sensor Updates", key="btn_update_wind"):
                st.session_state.wind_assets[asset_idx]["Vibration_Hz"] = new_vib
                st.session_state.wind_assets[asset_idx]["Gearbox_Temp_C"] = new_gtemp
                st.success(f"Updated telemetry for {selected_asset_id}!")
                st.rerun()

    with insp_col2:
        st.markdown("#### Add New Asset to Fleet")
        with st.form("add_asset_form"):
            asset_category = st.radio("Asset Category", ["Solar Array", "Wind Turbine"], key="add_asset_cat")
            new_id = st.text_input("Asset ID", value=f"SOLAR-P10{len(st.session_state.solar_assets)+1}" if asset_category == "Solar Array" else f"WIND-T20{len(st.session_state.wind_assets)+1}", key="add_asset_id")
            new_type = st.text_input("Asset Description / Name", value="Solar Array Section E" if asset_category == "Solar Array" else "3.0MW Wind Turbine #4", key="add_asset_type")
            new_cap = st.number_input("Capacity (kW)", min_value=100, max_value=5000, value=300 if asset_category == "Solar Array" else 2500, key="add_asset_cap")
            
            submitted = st.form_submit_button("Add Asset")
            if submitted:
                if asset_category == "Solar Array":
                    st.session_state.solar_assets.append({
                        "Asset_ID": new_id, "Type": new_type, "Capacity_kW": new_cap, "Soiling_%": 10.0, "Temp_C": 35.0
                    })
                else:
                    st.session_state.wind_assets.append({
                        "Asset_ID": new_id, "Type": new_type, "Capacity_kW": new_cap, "Vibration_Hz": 20.0, "Gearbox_Temp_C": 55.0
                    })
                st.success(f"Successfully added {new_id} to the fleet!")
                st.rerun()

# ------------------------------------------
# TAB 6: MAINTENANCE LOGS & DISPATCH MANAGEMENT
# ------------------------------------------
with tab6:
    st.subheader("Interactive Maintenance History & Dispatch Management Center")
    st.write("Track live dispatch logs, filter historical work orders, update repair statuses, or dispatch new field work orders.")
    
    # Convert history into DataFrame
    df_history = pd.DataFrame(st.session_state.maintenance_history)
    
    # Top KPI Metrics for Maintenance
    total_tickets = len(df_history)
    in_prog_count = (df_history['Status'] == 'In Progress').sum()
    scheduled_count = (df_history['Status'] == 'Scheduled').sum()
    resolved_count = (df_history['Status'] == 'Resolved').sum()
    
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.metric(label="Total Work Orders", value=f"{total_tickets}")
    with m_col2:
        st.metric(label="Active Dispatches", value=f"{in_prog_count + scheduled_count}", delta=f"{in_prog_count} In Progress")
    with m_col3:
        st.metric(label="Resolved Work Orders", value=f"{resolved_count}", delta=f"{resolved_count}/{total_tickets} Closed")
    with m_col4:
        st.metric(label="Avg Field Response", value="3.8 Hours", delta="-42% vs Industry")
        
    st.markdown("---")
    
    # Interactive Filter Toolbar
    st.markdown("#### Filter & Search Maintenance Logs")
    f_col1, f_col2, f_col3 = st.columns([1, 1, 1.5])
    
    with f_col1:
        filter_status = st.selectbox("Filter by Status", ["All Statuses", "In Progress", "Scheduled", "Resolved"], key="hist_filter_status")
    with f_col2:
        filter_category = st.selectbox("Filter by Category", ["All Categories", "Solar Array", "Wind Turbine"], key="hist_filter_category")
    with f_col3:
        search_query = st.text_input("Search (Ticket ID, Asset, Technician)", value="", key="hist_search_input")
        
    # Apply Filters
    df_filtered = df_history.copy()
    if filter_status != "All Statuses":
        df_filtered = df_filtered[df_filtered["Status"] == filter_status]
    if filter_category != "All Categories":
        df_filtered = df_filtered[df_filtered["Category"] == filter_category]
    if search_query:
        query_lower = search_query.lower()
        df_filtered = df_filtered[
            df_filtered["Ticket_ID"].str.lower().str.contains(query_lower) |
            df_filtered["Asset_ID"].str.lower().str.contains(query_lower) |
            df_filtered["Technician"].str.lower().str.contains(query_lower) |
            df_filtered["Issue"].str.lower().str.contains(query_lower)
        ]
        
    st.dataframe(df_filtered, use_container_width=True)
    
    # Download CSV Button
    csv_data = df_filtered.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=" Download Maintenance History CSV",
        data=csv_data,
        file_name=f"aerosolar_maintenance_logs_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        key="download_logs_csv"
    )
    
    st.markdown("---")
    
    # Ticket Status Update & Manual WO Creation Forms
    m_action_col1, m_action_col2 = st.columns(2)
    
    with m_action_col1:
        with st.container(border=True):
            st.markdown("#### ️ Update Work Order Status")
            all_ticket_ids = df_history["Ticket_ID"].tolist()
            if all_ticket_ids:
                sel_ticket = st.selectbox("Select Ticket to Update:", all_ticket_ids, key="sel_wo_ticket")
                ticket_idx = df_history[df_history["Ticket_ID"] == sel_ticket].index[0]
                ticket_item = df_history.iloc[ticket_idx]
                
                st.info(f"**Ticket**: `{ticket_item['Ticket_ID']}` | **Asset**: `{ticket_item['Asset_ID']}` | **Current Status**: `{ticket_item['Status']}`")
                
                cur_status_idx = ["In Progress", "Scheduled", "Resolved"].index(ticket_item['Status']) if ticket_item['Status'] in ["In Progress", "Scheduled", "Resolved"] else 0
                new_status = st.radio("Update Status:", ["In Progress", "Scheduled", "Resolved"], index=cur_status_idx, horizontal=True, key="sel_wo_status_radio")
                
                if st.button("Update Work Order Status", key="btn_update_wo_status"):
                    st.session_state.maintenance_history[ticket_idx]["Status"] = new_status
                    st.success(f"Successfully updated `{sel_ticket}` status to **{new_status}**!")
                    st.rerun()

    with m_action_col2:
        with st.container(border=True):
            st.markdown("#### Manually Log Field Work Order")
            with st.form("manual_wo_form"):
                wo_asset_type = st.radio("Asset Category", ["Solar Array", "Wind Turbine"], key="wo_form_cat")
                solar_ids = [item["Asset_ID"] for item in st.session_state.solar_assets]
                wind_ids = [item["Asset_ID"] for item in st.session_state.wind_assets]
                wo_asset_id = st.selectbox("Select Asset ID", solar_ids if wo_asset_type == "Solar Array" else wind_ids, key="wo_form_asset")
                
                wo_issue = st.text_input("Issue Description", value="Inverter Junction Box Overheating Inspection", key="wo_form_issue")
                wo_tech = st.text_input("Assigned Technician Team", value="Team Alpha (Electrical)", key="wo_form_tech")
                wo_priority = st.selectbox("Priority Level", ["NORMAL", "WARNING", "HIGH", "CRITICAL"], key="wo_priority_select")
                
                submitted_wo = st.form_submit_button(" Create & Dispatch Work Order")
                if submitted_wo:
                    new_id = f"WO-{np.random.randint(9000, 9999)}"
                    st.session_state.maintenance_history.insert(0, {
                        "Ticket_ID": new_id,
                        "Asset_ID": wo_asset_id,
                        "Category": wo_asset_type,
                        "Issue": wo_issue,
                        "Priority": wo_priority,
                        "Status": "In Progress",
                        "Technician": wo_tech,
                        "Date": datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    st.success(f"Created & Dispatched Work Order **{new_id}** for `{wo_asset_id}`!")
                    st.rerun()
