# app.py - Smart Home Energy Dashboard (DEPLOYMENT-FIXED VERSION)
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# -------------------------- Page Config --------------------------
st.set_page_config(
    page_title="Smart Home Energy Monitor",
    page_icon="house",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Smart Home Energy Usage Dashboard")
st.markdown("### Temperature • Humidity • Light • Energy • Motion Detection")

# -------------------------- Load Data --------------------------
@st.cache_data(ttl=3600)
def load_data():
    try:
        df = pd.read_csv("smart_home_energy_usage_dataset.csv")
        source = "smart_home_energy_usage_dataset.csv"
    except FileNotFoundError:
        st.warning("Dataset not found. Upload below.")
        uploaded = st.file_uploader("Upload your smart home CSV", type=["csv"])
        if uploaded is None:
            st.info("Waiting for upload...")
            st.stop()
        df = pd.read_csv(uploaded)
        source = "uploaded file"
    return df, source

df, source = load_data()

# -------------------------- Preprocessing --------------------------
df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
df = df.dropna(subset=['DateTime']).sort_values('DateTime').reset_index(drop=True)

df['Date'] = df['DateTime'].dt.date
df['Hour'] = df['DateTime'].dt.hour

energy_cols = ['Appliance_Usage_kWh', 'HVAC_Usage_kWh', 'Water_Heater_kWh']
for col in energy_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
df['Total_Energy_kWh'] = df[energy_cols].sum(axis=1, skipna=True)

st.success(f"Loaded **{len(df):,}** rows • {df['DateTime'].min().date()} → {df['DateTime'].max().date()}")

# -------------------------- Filters --------------------------
st.sidebar.header("Filters")
rooms = ['All'] + sorted(df['Room'].unique().tolist())
selected_room = st.sidebar.selectbox("Room", rooms)

date_range = st.sidebar.date_input(
    "Date Range",
    value=(df['DateTime'].min().date(), df['DateTime'].max().date()),
    min_value=df['DateTime'].min().date(),
    max_value=df['DateTime'].max().date()
)

motion_filter = st.sidebar.radio("Motion", ["All", "Active Only", "Inactive Only"], horizontal=True)

# -------------------------- Apply Filters --------------------------
data = df.copy()
if selected_room != 'All':
    data = data[data['Room'] == selected_room]

data = data[(data['Date'] >= date_range[0]) & (data['Date'] <= date_range[1])]

if motion_filter == "Active Only":
    data = data[data['Motion_Sensor'] == 'Active']
elif motion_filter == "Inactive Only":
    data = data[data['Motion_Sensor'] == 'Inactive']

if data.empty:
    st.warning("No data for selected filters.")
    st.stop()

# -------------------------- Metrics --------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Energy", f"{data['Total_Energy_kWh'].sum():.2f} kWh")
c2.metric("Active Rooms", data[data['Motion_Sensor']=='Active']['Room'].nunique())
c3.metric("Avg Temp", f"{data['Temperature_C'].mean():.1f}°C")
c4.metric("Avg Humidity", f"{data['Humidity_%'].mean():.1f}%")

st.markdown("---")

# -------------------------- Charts --------------------------
st.subheader("Energy Consumption Over Time")
fig1 = px.area(data, x='DateTime', y='Total_Energy_kWh', color='Room',
               title="Energy Usage by Room (Stacked)")
st.plotly_chart(fig1, use_container_width=True)

# FIXED DUAL-AXIS CHART (this was the only bug!)
st.subheader("Temperature & Humidity Trends")
fig2 = go.Figure()

fig2.add_trace(go.Scatter(
    x=data['DateTime'], y=data['Temperature_C'],
    name="Temperature (°C)",
    line=dict(color="#FF6B6B"),
    yaxis="y1"
))

fig2.add_trace(go.Scatter(
    x=data['DateTime'], y=data['Humidity_%'],
    name="Humidity (%)",
    line=dict(color="#4ECDC4"),
    yaxis="y2"
))

# Correct Plotly 5.15+ syntax
fig2.update_layout(
    title="Indoor Comfort Levels",
    hovermode="x unified",
    height=500,

    yaxis=dict(
        title="Temperature (°C)",
        titlefont=dict(color="#FF6B6B"),
        tickfont=dict(color="#FF6B6B"),
    ),
    yaxis2=dict(
        title="Humidity (%)",
        titlefont=dict(color="#4ECDC4"),
        tickfont=dict(color="#4ECDC4"),
        overlaying="y",
        side="right",
    ),
)
st.plotly_chart(fig2, use_container_width=True)

st.subheader("Motion Activity Heatmap (Hour × Room)")
pivot = data.pivot_table(index='Hour', columns='Room', values='Motion_Sensor',
                         aggfunc=lambda x: (x=='Active').sum(), fill_value=0)
fig3 = px.imshow(pivot.values, x=pivot.columns, y=pivot.index,
                 color_continuous_scale="Blues", title="When Are People in Each Room?")
st.plotly_chart(fig3, use_container_width=True)

st.subheader("Room Comparison")
tab1, tab2 = st.tabs(["Energy", "Comfort"])
with tab1:
    st.plotly_chart(px.box(data, x='Room', y='Total_Energy_kWh', color='Room'), use_container_width=True)
with tab2:
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.box(data, x='Room', y='Temperature_C', color='Room'), use_container_width=True)
    with c2:
        st.plotly_chart(px.box(data, x='Room', y='Humidity_%', color='Room'), use_container_width=True)

# -------------------------- Table & Download --------------------------
st.markdown("---")
st.subheader("Latest Readings")
st.dataframe(
    data.sort_values('DateTime', ascending=False).head(20)[
        ['DateTime', 'Home_ID', 'Room', 'Temperature_C', 'Humidity_%', 'Light_Lux', 'Total_Energy_kWh', 'Motion_Sensor']
    ],
    use_container_width=True, hide_index=True
)

st.download_button("Download Filtered Data", data.to_csv(index=False), "smart_home_filtered.csv", "text/csv")





