
import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="IoT Device Portal — Dark", page_icon="🛰️", layout="wide")
st.markdown('\n<style>\n.block-container { padding-top: 1rem; }\ndiv[data-testid="stMetric"] [data-testid="stMetricDelta"] { font-size: 0.9rem; }\n.badge { display:inline-block; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem; font-weight:600;\n         background:#1F2937; color:#E5E7EB; border:1px solid #374151; margin-right:6px; }\n.badge.ok { border-color:#14532D; color:#22C55E; }\n.badge.issue { border-color:#7C2D12; color:#F59E0B; }\n.badge.off { border-color:#7F1D1D; color:#F87171; }\n</style>\n', unsafe_allow_html=True)

@st.cache_data
def load_data():
    devices = pd.read_csv("data/devices.csv", parse_dates=["last_seen","install_date"])
    ts = pd.read_csv("data/installs_timeseries.csv", parse_dates=["install_date"])
    alerts = pd.read_csv("data/alerts.csv", parse_dates=["timestamp"])
    return devices, ts, alerts

devices, ts, alerts = load_data()

# Sidebar filters
st.sidebar.subheader("Filters")
region = st.sidebar.multiselect("Region", sorted(devices.region.unique()))
vtypes = st.sidebar.multiselect("Vehicle type", sorted(devices.vehicle_type.unique()))
status = st.sidebar.multiselect("Status", ["healthy","offline","issue"])
hours = st.sidebar.slider("Last seen within (hours)", 0, 48, 24)

df = devices.copy()
if region: df = df[df.region.isin(region)]
if vtypes: df = df[df.vehicle_type.isin(vtypes)]
if status: df = df[df.status.isin(status)]
if hours>0:
    cutoff = pd.Timestamp.now() - pd.Timedelta(hours=hours)
    df = df[df.last_seen >= cutoff]

# KPIs
c1, c2, c3, c4 = st.columns(4)
total = len(df); ok = int((df.status=="healthy").sum())
iss = int((df.status=="issue").sum()); off = int((df.status=="offline").sum())
c1.metric("Active Devices", total)
c2.metric("Healthy", ok)
c3.metric("Issues", iss)
c4.metric("Offline", off)

# Map + breakdown + alerts
left, right = st.columns([2.2, 1])
with left:
    st.subheader("Live Map")
    color_map = {"healthy":[34,197,94], "issue":[245,158,11], "offline":[248,113,113]}
    df_map = df.assign(color=df.status.map(color_map))
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_map,
        get_position='[lon, lat]',
        get_fill_color='color',
        get_radius=35,
        pickable=True,
    )
    tooltip = {
        "html": "<b>{device_id}</b><br>Vehicle: {vehicle_id}<br>Status: {status}<br>Issue: {issue_type}<br>Temp: {temperature_c}°C | Volt: {voltage_v}V",
        "style": {"backgroundColor":"rgba(9,13,25,0.95)","color":"white","fontSize":"12px"}
    }
    st.pydeck_chart(pdk.Deck(
        initial_view_state=pdk.ViewState(latitude=-6.2, longitude=106.85, zoom=9.4),
        layers=[layer], tooltip=tooltip, map_style=None
    ))

with right:
    st.subheader("Breakdown")
    colA, colB = st.columns(2)
    with colA:
        by_status = df.status.value_counts().rename_axis("status").reset_index(name="count")
        st.plotly_chart(px.pie(by_status, values="count", names="status", title="Health"), use_container_width=True)
    with colB:
        by_vtype = df.groupby("vehicle_type").size().reset_index(name="count")
        st.plotly_chart(px.bar(by_vtype, x="vehicle_type", y="count", title="By Vehicle"), use_container_width=True)
    st.markdown("**Recent Alerts**  " + "\
        <span class='badge ok'>healthy</span><span class='badge issue'>issue</span><span class='badge off'>offline</span>", unsafe_allow_html=True)
    st.dataframe(alerts.head(18), height=260, use_container_width=True)

st.divider()

# Growth
st.subheader("KDC Growth")
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(px.line(ts, x="install_date", y="cumulative", title="Cumulative Devices Installed"), use_container_width=True)
with col2:
    st.plotly_chart(px.bar(ts, x="install_date", y="added", title="New Devices per Day"), use_container_width=True)

st.divider()
st.subheader("Devices")
st.dataframe(
    df.sort_values("last_seen", ascending=False)[
        ["device_id","vehicle_id","vehicle_type","region","status","issue_type","last_seen","temperature_c","voltage_v","camera_inward_ok","camera_outward_ok","lat","lon"]
    ],
    use_container_width=True, height=420
)

st.caption("Dark theme demo with navy background and green/red/orange health accents. Data is synthetic.")
