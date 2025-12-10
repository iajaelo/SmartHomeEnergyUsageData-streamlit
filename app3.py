# app.py - Smart Home Energy Dashboard (ULTRA-FIXED VERSION)
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Page Config
st.set_page_config(page_title="Smart Home Energy Monitor", page_icon="house", layout="wide")

st.title("Smart Home Energy Usage Dashboard")
st.markdown("### Temperature • Humidity • Light • Energy • Motion Detection")

# Load Data (with error handling)
@st.cache_data(ttl=3600)
def load_data():
    try:
        df = pd.read_csv("smart_home_energy_usage_dataset.csv")
        source = "file"
    except:
        st.warning("File not found—upload below.")
        uploaded = st.file_uploader("Upload CSV", type="csv")
        if uploaded is None:
            st.stop()
        df = pd.read_csv(uploaded)
        source = "upload"
    return df

df_raw = load_data()
st.success(f"Loaded {len(df_raw)} rows")

# Safe Preprocessing
try:
    df = df_raw.copy()
    df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
    df = df.dropna(subset=['DateTime']).sort_values('DateTime').reset_index(drop=True)
    
    df['Date'] = df['DateTime'].dt.date
    df['Hour'] = df['DateTime'].dt.hour
    
    # Safe energy calc
    energy_cols = [col for col in ['Appliance_Usage_kWh', 'HVAC_Usage_kWh', 'Water_Heater_kWh'] if col in df.columns]
    for col in energy_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    if energy_cols:
        df['Total_Energy_kWh'] = df[energy_cols].sum(axis=1, skipna=True).fillna(0)
    else:
        df['Total_Energy_kWh'] = 0  # Fallback if no energy cols
    
    # Ensure required cols exist
    for col in ['Temperature_C', 'Humidity_%', 'Motion_Sensor', 'Room']:
        if col not in df.columns:
            st.error(f"Missing column: {col}")
            st.stop()
    
except Exception as e:
    st.error(f"Data processing error: {e}")
    st.stop()

# Filters
st.sidebar.header("Filters")
rooms = ['All'] + sorted(df['Room'].unique())
selected_room = st.sidebar.selectbox("Room", rooms)

date_range = st.sidebar.date_input("Date Range", (df['Date'].min(), df['Date'].max()))

motion_filter = st.sidebar.radio("Motion", ["All", "Active Only", "Inactive Only"])

# Apply Filters (safe)
data = df[(df['Date'] >= date_range[0]) & (df['Date'] <= date_range[1])].copy()

if selected_room != 'All':
    data = data[data['Room'] == selected_room]

if motion_filter == "Active Only":
    data = data[data['Motion_Sensor'] == 'Active']
elif motion_filter == "Inactive Only":
    data = data[data['Motion_Sensor'] == 'Inactive']

if len(data) == 0:
    st.warning("No data after filters. Try broadening them.")
    st.stop()

# Metrics (safe calcs)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Energy", f"{data['Total_Energy_kWh'].sum():.2f} kWh")
c2.metric("Active Readings", len(data[data['Motion_Sensor']=='Active']))
c3.metric("Avg Temp", f"{data['Temperature_C'].mean():.1f}°C")
c4.metric("Avg Humidity", f"{data['Humidity_%'].mean():.1f}%")

st.markdown("---")

# Chart 1: Energy Over Time
st.subheader("Energy Consumption Over Time")
fig1 = px.area(data, x='DateTime', y='Total_Energy_kWh', color='Room', title="Energy by Room")
st.plotly_chart(fig1, use_container_width=True)

# FIXED Dual-Axis Chart (compatible with all Plotly versions)
st.subheader("Temperature & Humidity")
if len(data) > 0:
    fig2 = go.Figure()
    
    fig2.add_trace(go.Scatter(
        x=data['DateTime'], 
        y=data['Temperature_C'].fillna(np.nan), 
        name="Temperature (°C)", 
        line=dict(color="#FF6B6B"), 
        yaxis="y"
    ))
    
    fig2.add_trace(go.Scatter(
        x=data['DateTime'], 
        y=data['Humidity_%'].fillna(np.nan), 
        name="Humidity (%)", 
        line=dict(color="#4ECDC4"), 
        yaxis="y2"
    ))
    
    fig2.update_layout(
        title="Comfort Trends",
        height=500,
        hovermode="x unified",
        # Safe axis config
        yaxis_title="Temperature (°C)",
        yaxis=dict(titlefont_color="#FF6B6B", tickfont_color="#FF6B6B"),
        yaxis2=dict(
            title="Humidity (%)",
            overlaying="y",
            side="right",
            titlefont_color="#4ECDC4",
            tickfont_color="#4ECDC4"
        )
    )
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No data for chart")

# Chart 3: Motion Heatmap
st.subheader("Motion Heatmap")
pivot = data.pivot_table(
    index='Hour', 
    columns='Room', 
    values='Motion_Sensor', 
    aggfunc=lambda x: (x == 'Active').sum() if len(x) > 0 else 0, 
    fill_value=0
)
if not pivot.empty:
    fig3 = px.imshow(
        pivot.values, 
        x=pivot.columns, 
        y=pivot.index, 
        color_continuous_scale="Blues", 
        title="Motion by Hour & Room"
    )
    st.plotly_chart(fig3, use_container_width=True)

# Room Comparison Tabs
st.subheader("Room Insights")
tab1, tab2 = st.tabs(["Energy", "Comfort"])

with tab1:
    if 'Total_Energy_kWh' in data.columns:
        st.plotly_chart(px.box(data, x='Room', y='Total_Energy_kWh', color='Room'), use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(px.box(data, x='Room', y='Temperature_C', color='Room'), use_container_width=True)
    with col2:
        st.plotly_chart(px.box(data, x='Room', y='Humidity_%', color='Room'), use_container_width=True)

# Table (safe column select)
st.markdown("---")
st.subheader("Latest Data")
cols = ['DateTime', 'Home_ID', 'Room', 'Temperature_C', 'Humidity_%', 'Motion_Sensor']
if 'Light_Lux' in data.columns:
    cols.insert(-1, 'Light_Lux')
if 'Total_Energy_kWh' in data.columns:
    cols.insert(-1, 'Total_Energy_kWh')

latest_df = data[cols].sort_values('DateTime', ascending=False).head(20).round(2)
st.dataframe(latest_df, use_container_width=True, hide_index=True)

# Download
st.download_button("Download Filtered CSV", data.to_csv(index=False), "filtered_data.csv")

