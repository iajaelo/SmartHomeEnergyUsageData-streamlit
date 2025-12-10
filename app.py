# app.py - Smart Home Energy & Environment Dashboard
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# -------------------------- Page Config --------------------------
st.set_page_config(
    page_title="Smart Home Monitor",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Smart Home Energy Usage Dashboard")
st.markdown("### Real-time Temperature • Humidity • Light • Energy • Motion Detection")

# -------------------------- Load Data --------------------------
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("./smart_home_energy_usage_dataset.csv")
    except:
        uploaded = st.file_uploader(
            "Upload your smart home data (CSV)",
            type=["csv"],
            help="Expected columns: Home_ID, DateTime, Temperature_C, Humidity_%, Light_Lux, Motion_Sensor, Room, energy columns..."
        )
        if uploaded is None:
            st.info("Upload `smart_home_data.csv` to begin")
            st.stop()
        df = pd.read_csv(uploaded)
    return df

df = load_data()

# -------------------------- Data Preprocessing --------------------------
df['DateTime'] = pd.to_datetime(df['DateTime'])
df = df.sort_values('DateTime')

# Extract date & time
df['Date'] = df['DateTime'].dt.date
df['Time'] = df['DateTime'].dt.strftime('%H:%M')
df['Hour'] = df['DateTime'].dt.hour
df['Day'] = df['DateTime'].dt.day_name()

# Total energy (if not already present)
energy_cols = ['Appliance_Usage_kWh', 'HVAC_Usage_kWh', 'Water_Heater_kWh']
for col in energy_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

if 'Total_Energy_kWh' not in df.columns:
    df['Total_Energy_kWh'] = df[energy_cols].sum(axis=1)

st.success(f"Loaded {len(df):,} sensor readings • {df['DateTime'].min().date()} to {df['DateTime'].max().date()}")

# -------------------------- Sidebar Filters --------------------------
st.sidebar.header("Filters")

# Room selector
rooms = ['All'] + sorted(df['Room'].unique().tolist())
selected_room = st.sidebar.selectbox("Select Room", rooms)

# Date range
date_range = st.sidebar.date_input(
    "Date Range",
    value=(df['DateTime'].min().date(), df['DateTime'].max().date()),
    min_value=df['DateTime'].min().date(),
    max_value=df['DateTime'].max().date()
)

# Motion filter
motion_filter = st.sidebar.radio("Motion Sensor", ["All", "Active Only", "Inactive Only"])

# Apply filters
data = df.copy()
if selected_room != 'All':
    data = data[data['Room'] == selected_room]

data = data[
    (data['DateTime'].dt.date >= date_range[0]) &
    (data['DateTime'].dt.date <= date_range[1])
]

if motion_filter == "Active Only":
    data = data[data['Motion_Sensor'] == 'Active']
elif motion_filter == "Inactive Only":
    data = data[data['Motion_Sensor'] == 'Inactive']

if data.empty:
    st.warning("No data matches your filters.")
    st.stop()

# -------------------------- Key Metrics --------------------------
latest = data.sort_values('DateTime').groupby('Room').last().reset_index()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Energy Today", f"{data['Total_Energy_kWh'].sum():.1f} kWh")
with col2:
    st.metric("Active Rooms", data[data['Motion_Sensor'] == 'Active']['Room'].nunique())
with col3:
    avg_temp = data['Temperature_C'].mean()
    st.metric("Avg Temperature", f"{avg_temp:.1f}°C")
with col4:
    avg_hum = data['Humidity_%'].mean()
    st.metric("Avg Humidity", f"{avg_hum:.1f}%")

st.markdown("---")

# -------------------------- Chart 1: Energy Usage Over Time --------------------------
st.subheader("Total Energy Consumption Over Time")
fig1 = px.area(
    data, x='DateTime', y='Total_Energy_kWh',
    color='Room' if selected_room == 'All' else None,
    title="Energy Usage (kWh) - Stacked by Room",
    labels={'Total_Energy_kWh': 'Energy (kWh)'}
)
fig1.update_layout(height=500)
st.plotly_chart(fig1, use_container_width=True)

# -------------------------- Chart 2: Temperature & Humidity Dual Axis --------------------------
st.subheader("Temperature & Humidity Trends")
fig2 = go.Figure()

fig2.add_trace(go.Scatter(
    x=data['DateTime'], y=data['Temperature_C'],
    name='Temperature (°C)', yaxis='y', line=dict(color='red')
))
fig2.add_trace(go.Scatter(
    x=data['DateTime'], y=data['Humidity_%'],
    name='Humidity (%)', yaxis='y2', line=dict(color='blue')
))

fig2.update_layout(
    title="Temperature & Humidity Over Time",
    yaxis=dict(title="Temperature (°C)", titlefont=dict(color="red"), tickfont=dict(color="red")),
    yaxis2=dict(title="Humidity (%)", titlefont=dict(color="blue"), tickfont=dict(color="blue"),
                overlaying="y", side="right"),
    height=500, hovermode='x unified'
)
st.plotly_chart(fig2, use_container_width=True)

# -------------------------- Chart 3: Motion Activity Heatmap --------------------------
st.subheader("Motion Activity by Hour & Room")
motion_pivot = data.pivot_table(
    index='Hour', columns='Room', values='Motion_Sensor',
    aggfunc=lambda x: (x == 'Active').sum(), fill_value=0
)

fig3 = px.imshow(
    motion_pivot.values,
    x=motion_pivot.columns,
    y=motion_pivot.index,
    labels=dict(color="Motion Events"),
    color_continuous_scale="Viridis",
    title="Motion Sensor Triggers by Hour of Day"
)
fig3.update_layout(height=500)
st.plotly_chart(fig3, use_container_width=True)

# -------------------------- Chart 4: Room Comparison (Box Plots) --------------------------
st.subheader("Energy & Environment by Room")
tab1, tab2 = st.tabs(["Energy Usage", "Comfort Levels"])

with tab1:
    fig4a = px.box(data, x='Room', y='Total_Energy_kWh', color='Room',
                   title="Total Energy Consumption by Room")
    st.plotly_chart(fig4a, use_container_width=True)

with tab2:
    col_a, col_b = st.columns(2)
    with col_a:
        fig_temp = px.box(data, x='Room', y='Temperature_C', color='Room',
                          title="Temperature Distribution")
        st.plotly_chart(fig_temp, use_container_width=True)
    with col_b:
        fig_hum = px.box(data, x='Room', y='Humidity_%', color='Room',
                         title="Humidity Distribution")
        st.plotly_chart(fig_hum, use_container_width=True)

# -------------------------- Live Table --------------------------
st.markdown("---")
st.subheader("Latest Sensor Readings")
latest_readings = data.sort_values('DateTime', ascending=False).head(20)
display_cols = ['DateTime', 'Home_ID', 'Room', 'Temperature_C', 'Humidity_%',
                'Light_Lux', 'Total_Energy_kWh', 'Motion_Sensor']

st.dataframe(
    latest_readings[display_cols].round(2),
    use_container_width=True,
    hide_index=True
)

# Download
csv = data.to_csv(index=False)
st.download_button("Download filtered data", csv, "smart_home_filtered.csv", "text/csv")



