# app.py — Smart Home Energy Monitor (FINAL WORKING PRO VERSION)
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# =========================== PRO CONFIG ===========================
st.set_page_config(
    page_title="Smart Home Energy Monitor",
    page_icon="power",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .big-font {font-size:50px !important; font-weight: bold; color: #1E90FF;}
    .css-1d391kg {padding-top: 3rem;}
</style>
""", unsafe_allow_html=True)

# Header
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://cdn-icons-png.flaticon.com/512/10861/10861082.png", width=100)
with col2:
    st.markdown("<h1 style='margin:0;'>Smart Home Energy Monitor</h1>", unsafe_allow_html=True)
    st.markdown("**Real-time Energy • Comfort • Motion • Cost Intelligence**")

# =========================== DATA LOADING ===========================
@st.cache_data(ttl=3600)
def load_data():
    try:
        df = pd.read_csv("smart_home_energy_usage_dataset.csv")
    except:
        st.error("Dataset not found!")
        uploaded = st.file_uploader("Upload your CSV", type="csv")
        if uploaded:
            df = pd.read_csv(uploaded)
        else:
            st.stop()
    return df

df = load_data()

# Preprocessing
df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
df = df.dropna(subset=['DateTime']).sort_values('DateTime').reset_index(drop=True)
df['Date'] = df['DateTime'].dt.date
df['Hour'] = df['DateTime'].dt.hour

energy_cols = ['Appliance_Usage_kWh', 'HVAC_Usage_kWh', 'Water_Heater_kWh']
for col in energy_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
df['Total_Energy_kWh'] = df[energy_cols].sum(axis=1)

# =========================== SIDEBAR ===========================
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/10861/10861082.png", width=80)
st.sidebar.markdown("<h2 style='text-align:center;'>Controls</h2>", unsafe_allow_html=True)

selected_room = st.sidebar.selectbox("Room", ['All'] + sorted(df['Room'].unique().tolist()))
date_range = st.sidebar.date_input("Date Range", [df['DateTime'].min().date(), df['DateTime'].max().date()])
motion_filter = st.sidebar.radio("Motion Filter", ["All", "Active Only", "Inactive Only"], horizontal=True)
electricity_rate = st.sidebar.number_input("Rate $/kWh", 0.05, 0.50, 0.15, 0.01)

# =========================== FILTER DATA ===========================
data = df[(df['Date'] >= date_range[0]) & (df['Date'] <= date_range[1])].copy()
if selected_room != 'All':
    data = data[data['Room'] == selected_room]
if motion_filter != "All":
    data = data[data['Motion_Sensor'] == ('Active' if motion_filter == "Active Only" else 'Inactive')]

total_energy = data['Total_Energy_kWh'].sum()
total_cost = total_energy * electricity_rate

# =========================== METRICS ===========================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Energy", f"{total_energy:,.2f} kWh")
c2.metric("Estimated Cost", f"${total_cost:,.2f}")
c3.metric("Active Rooms", data[data['Motion_Sensor']=='Active']['Room'].nunique())
c4.metric("Avg Comfort", f"{data['Temperature_C'].mean():.1f}°C • {data['Humidity_%'].mean():.0f}%")

st.markdown("---")

# =========================== CHARTS ===========================
st.subheader("Energy Consumption Trend")
fig1 = px.area(data, x='DateTime', y='Total_Energy_kWh', color='Room',
               title="Energy Usage Over Time", color_discrete_sequence=px.colors.qualitative.Bold)
st.plotly_chart(fig1, use_container_width=True)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Temperature & Humidity")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=data['DateTime'], y=data['Temperature_C'], name="Temperature °C", line=dict(color="#FF6B6B")))
    fig2.add_trace(go.Scatter(x=data['DateTime'], y=data['Humidity_%'], name="Humidity %", yaxis="y2", line=dict(color="#4ECDC4")))
    
    # THIS IS THE ONLY FIX NEEDED — NEW PLOTLY SYNTAX
    fig2.update_layout(
        title="Indoor Comfort Levels",
        hovermode='x unified',
        height=400,
        yaxis=dict(
            title="Temperature °C",
            titlefont=dict(color="#FF6B6B"),
            tickfont=dict(color="#FF6B6B")
        ),
        yaxis2=dict(
            title="Humidity %",
            titlefont=dict(color="#4ECDC4"),
            tickfont=dict(color="#4ECDC4"),
            overlaying="y",
            side="right"
        )
    )
    st.plotly_chart(fig2, use_container_width=True)

with col2:
    st.subheader("Motion Activity Heatmap")
    pivot = data.pivot_table(index='Hour', columns='Room', values='Motion_Sensor',
                             aggfunc=lambda x: (x=='Active').sum(), fill_value=0)
    fig3 = px.imshow(pivot.values, x=pivot.columns, y=pivot.index,
                     color_continuous_scale="Viridis", title="When is each room occupied?")
    st.plotly_chart(fig3, use_container_width=True)

st.subheader("Room Performance Comparison")
tab1, tab2, tab3 = st.tabs(["Energy", "Comfort", "Light & Motion"])

with tab1:
    st.plotly_chart(px.box(data, x='Room', y='Total_Energy_kWh', color='Room'), use_container_width=True)

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.violin(data, x='Room', y='Temperature_C', color='Room'), use_container_width=True)
    with c2:
        st.plotly_chart(px.violin(data, x='Room', y='Humidity_%', color='Room'), use_container_width=True)

with tab3:
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.box(data, x='Room', y='Light_Lux', color='Room'), use_container_width=True)
    with c2:
        motion_pct = data.groupby('Room')['Motion_Sensor'].apply(lambda x: (x=='Active').mean()*100)
        fig = px.bar(x=motion_pct.index, y=motion_pct.values, title="Motion Activity %", color=motion_pct.values)
        st.plotly_chart(fig, use_container_width=True)

# =========================== TABLE & DOWNLOAD ===========================
st.markdown("---")
st.subheader("Latest Readings")
latest = data.tail(15).sort_values('DateTime', ascending=False)
st.dataframe(latest[['DateTime', 'Home_ID', 'Room', 'Temperature_C', 'Humidity_%', 'Light_Lux', 'Total_Energy_kWh', 'Motion_Sensor']].round(2),
             use_container_width=True, hide_index=True)

st.download_button("Download Data", data.to_csv(index=False), "smart_home_analysis.csv", "text/csv")

st.caption("Smart Home Energy Monitor • Built with Streamlit")


