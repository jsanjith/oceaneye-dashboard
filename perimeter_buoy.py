import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
import math
import time
import random


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Autonomous Ocean Observation System",
    page_icon="🌊",
    layout="wide"
)


# ============================================================
# TITLE
# ============================================================

st.title("🌊 Autonomous Low-Cost Ocean Observation Platform")

st.markdown(
    """
    ### Two-Drone and Two-Buoy Simulation

    This simulation contains two autonomous drones attached to
    two separate ocean observation buoys.

    **Buoy 1:** Temperature + Wave Height + GPS  
    **Buoy 2:** Salinity + Turbidity + GPS
    """
)


# ============================================================
# CONSTANTS
# ============================================================

EARTH_RADIUS = 6371000.0

# Starting positions
BUOY1_START_LAT = 13.0827
BUOY1_START_LON = 80.2707

BUOY2_START_LAT = 13.0900
BUOY2_START_LON = 80.2850


# ============================================================
# HAVERSINE DISTANCE
# ============================================================

def haversine(lat1, lon1, lat2, lon2):

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS * c


# ============================================================
# MOVE TOWARDS TARGET
# ============================================================

def move_towards(
    current_lat,
    current_lon,
    target_lat,
    target_lon,
    distance_m
):

    distance = haversine(
        current_lat,
        current_lon,
        target_lat,
        target_lon
    )

    if distance == 0:
        return target_lat, target_lon

    ratio = min(distance_m / distance, 1.0)

    new_lat = current_lat + (
        target_lat - current_lat
    ) * ratio

    new_lon = current_lon + (
        target_lon - current_lon
    ) * ratio

    return new_lat, new_lon


# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

if "initialized" not in st.session_state:

    # -----------------------------
    # BUOY 1
    # -----------------------------

    st.session_state.buoy1_lat = BUOY1_START_LAT
    st.session_state.buoy1_lon = BUOY1_START_LON

    st.session_state.drone1_lat = BUOY1_START_LAT
    st.session_state.drone1_lon = BUOY1_START_LON

    st.session_state.buoy1_status = "NORMAL"
    st.session_state.drone1_status = "Monitoring"

    # -----------------------------
    # BUOY 2
    # -----------------------------

    st.session_state.buoy2_lat = BUOY2_START_LAT
    st.session_state.buoy2_lon = BUOY2_START_LON

    st.session_state.drone2_lat = BUOY2_START_LAT
    st.session_state.drone2_lon = BUOY2_START_LON

    st.session_state.buoy2_status = "NORMAL"
    st.session_state.drone2_status = "Monitoring"

    # -----------------------------
    # Sensor values
    # -----------------------------

    st.session_state.temperature = 28.0
    st.session_state.wave_height = 1.2

    st.session_state.salinity = 35.0
    st.session_state.turbidity = 5.0

    # -----------------------------
    # Counters
    # -----------------------------

    st.session_state.simulation_step = 0
    st.session_state.violations1 = 0
    st.session_state.violations2 = 0

    st.session_state.initialized = True


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("⚙️ Simulation Controls")

perimeter1 = st.sidebar.slider(
    "Buoy 1 Perimeter (meters)",
    min_value=50,
    max_value=1000,
    value=300,
    step=50
)

perimeter2 = st.sidebar.slider(
    "Buoy 2 Perimeter (meters)",
    min_value=50,
    max_value=1000,
    value=300,
    step=50
)

ocean_speed = st.sidebar.slider(
    "Ocean Drift Speed (m/step)",
    min_value=1,
    max_value=100,
    value=20
)

drone_speed = st.sidebar.slider(
    "Drone Speed (m/step)",
    min_value=10,
    max_value=300,
    value=100
)

st.sidebar.markdown("---")

st.sidebar.subheader("Simulation")

start_simulation = st.sidebar.checkbox(
    "▶ Run Simulation",
    value=False
)

force_drift = st.sidebar.checkbox(
    "🌊 Increase Ocean Drift",
    value=False
)

st.sidebar.markdown("---")

if st.sidebar.button("🔄 Reset Simulation"):

    st.session_state.buoy1_lat = BUOY1_START_LAT
    st.session_state.buoy1_lon = BUOY1_START_LON

    st.session_state.drone1_lat = BUOY1_START_LAT
    st.session_state.drone1_lon = BUOY1_START_LON

    st.session_state.buoy2_lat = BUOY2_START_LAT
    st.session_state.buoy2_lon = BUOY2_START_LON

    st.session_state.drone2_lat = BUOY2_START_LAT
    st.session_state.drone2_lon = BUOY2_START_LON

    st.session_state.buoy1_status = "NORMAL"
    st.session_state.buoy2_status = "NORMAL"

    st.session_state.drone1_status = "Monitoring"
    st.session_state.drone2_status = "Monitoring"

    st.session_state.violations1 = 0
    st.session_state.violations2 = 0
    st.session_state.simulation_step = 0

    st.rerun()


# ============================================================
# OCEAN DRIFT FUNCTION
# ============================================================

def simulate_ocean_drift(lat, lon, speed):

    # Random ocean current direction
    angle = random.uniform(0, 2 * math.pi)

    north_movement = math.cos(angle) * speed
    east_movement = math.sin(angle) * speed

    # Convert meters to latitude/longitude
    lat_change = north_movement / 111320

    lon_change = east_movement / (
        111320 * math.cos(math.radians(lat))
    )

    return (
        lat + lat_change,
        lon + lon_change
    )


# ============================================================
# SIMULATION UPDATE
# ============================================================

if start_simulation:

    st.session_state.simulation_step += 1

    current_drift = ocean_speed

    if force_drift:
        current_drift = ocean_speed * 3


    # ========================================================
    # BUOY 1 MOVEMENT
    # ========================================================

    if st.session_state.buoy1_status == "NORMAL":

        new_lat, new_lon = simulate_ocean_drift(
            st.session_state.buoy1_lat,
            st.session_state.buoy1_lon,
            current_drift
        )

        st.session_state.buoy1_lat = new_lat
        st.session_state.buoy1_lon = new_lon


    # ========================================================
    # BUOY 2 MOVEMENT
    # ========================================================

    if st.session_state.buoy2_status == "NORMAL":

        new_lat, new_lon = simulate_ocean_drift(
            st.session_state.buoy2_lat,
            st.session_state.buoy2_lon,
            current_drift
        )

        st.session_state.buoy2_lat = new_lat
        st.session_state.buoy2_lon = new_lon


    # ========================================================
    # CALCULATE DISTANCES FROM ORIGINAL POSITION
    # ========================================================

    distance1 = haversine(
        BUOY1_START_LAT,
        BUOY1_START_LON,
        st.session_state.buoy1_lat,
        st.session_state.buoy1_lon
    )

    distance2 = haversine(
        BUOY2_START_LAT,
        BUOY2_START_LON,
        st.session_state.buoy2_lat,
        st.session_state.buoy2_lon
    )


    # ========================================================
    # BUOY 1 PERIMETER CHECK
    # ========================================================

    if distance1 > perimeter1:

        if st.session_state.buoy1_status == "NORMAL":

            st.session_state.violations1 += 1

        st.session_state.buoy1_status = "OUTSIDE PERIMETER"
        st.session_state.drone1_status = "🚨 Recovering Buoy"

        # Drone moves toward buoy
        st.session_state.drone1_lat, st.session_state.drone1_lon = (
            move_towards(
                st.session_state.drone1_lat,
                st.session_state.drone1_lon,
                st.session_state.buoy1_lat,
                st.session_state.buoy1_lon,
                drone_speed
            )
        )

        # Check if drone has reached buoy
        drone_buoy_distance = haversine(
            st.session_state.drone1_lat,
            st.session_state.drone1_lon,
            st.session_state.buoy1_lat,
            st.session_state.buoy1_lon
        )

        if drone_buoy_distance < 10:

            st.session_state.drone1_status = (
                "🔗 Attached - Returning Buoy"
            )

            # Move buoy back toward starting point
            st.session_state.buoy1_lat, st.session_state.buoy1_lon = (
                move_towards(
                    st.session_state.buoy1_lat,
                    st.session_state.buoy1_lon,
                    BUOY1_START_LAT,
                    BUOY1_START_LON,
                    drone_speed
                )
            )

    else:

        st.session_state.buoy1_status = "NORMAL"

        if haversine(
            st.session_state.drone1_lat,
            st.session_state.drone1_lon,
            BUOY1_START_LAT,
            BUOY1_START_LON
        ) > 10:

            st.session_state.drone1_lat, st.session_state.drone1_lon = (
                move_towards(
                    st.session_state.drone1_lat,
                    st.session_state.drone1_lon,
                    BUOY1_START_LAT,
                    BUOY1_START_LON,
                    drone_speed
                )
            )

        else:

            st.session_state.drone1_lat = BUOY1_START_LAT
            st.session_state.drone1_lon = BUOY1_START_LON

            st.session_state.drone1_status = "Monitoring"


    # ========================================================
    # BUOY 2 PERIMETER CHECK
    # ========================================================

    if distance2 > perimeter2:

        if st.session_state.buoy2_status == "NORMAL":

            st.session_state.violations2 += 1

        st.session_state.buoy2_status = "OUTSIDE PERIMETER"
        st.session_state.drone2_status = "🚨 Recovering Buoy"

        # Drone moves toward buoy
        st.session_state.drone2_lat, st.session_state.drone2_lon = (
            move_towards(
                st.session_state.drone2_lat,
                st.session_state.drone2_lon,
                st.session_state.buoy2_lat,
                st.session_state.buoy2_lon,
                drone_speed
            )
        )

        # Check if drone reaches buoy
        drone_buoy_distance = haversine(
            st.session_state.drone2_lat,
            st.session_state.drone2_lon,
            st.session_state.buoy2_lat,
            st.session_state.buoy2_lon
        )

        if drone_buoy_distance < 10:

            st.session_state.drone2_status = (
                "🔗 Attached - Returning Buoy"
            )

            # Move buoy back to original location
            st.session_state.buoy2_lat, st.session_state.buoy2_lon = (
                move_towards(
                    st.session_state.buoy2_lat,
                    st.session_state.buoy2_lon,
                    BUOY2_START_LAT,
                    BUOY2_START_LON,
                    drone_speed
                )
            )

    else:

        st.session_state.buoy2_status = "NORMAL"

        if haversine(
            st.session_state.drone2_lat,
            st.session_state.drone2_lon,
            BUOY2_START_LAT,
            BUOY2_START_LON
        ) > 10:

            st.session_state.drone2_lat, st.session_state.drone2_lon = (
                move_towards(
                    st.session_state.drone2_lat,
                    st.session_state.drone2_lon,
                    BUOY2_START_LAT,
                    BUOY2_START_LON,
                    drone_speed
                )
            )

        else:

            st.session_state.drone2_lat = BUOY2_START_LAT
            st.session_state.drone2_lon = BUOY2_START_LON

            st.session_state.drone2_status = "Monitoring"


    # ========================================================
    # SENSOR SIMULATION
    # ========================================================

    st.session_state.temperature += random.uniform(
        -0.15,
        0.15
    )

    st.session_state.wave_height += random.uniform(
        -0.08,
        0.08
    )

    st.session_state.salinity += random.uniform(
        -0.05,
        0.05
    )

    st.session_state.turbidity += random.uniform(
        -0.5,
        0.5
    )

    # Keep values in realistic simulation ranges

    st.session_state.temperature = np.clip(
        st.session_state.temperature,
        20,
        35
    )

    st.session_state.wave_height = np.clip(
        st.session_state.wave_height,
        0.1,
        5
    )

    st.session_state.salinity = np.clip(
        st.session_state.salinity,
        25,
        40
    )

    st.session_state.turbidity = np.clip(
        st.session_state.turbidity,
        0,
        100
    )


# ============================================================
# SENSOR DATA SECTION
# ============================================================

st.subheader("📡 Live Sensor Data")

col1, col2 = st.columns(2)


# ============================================================
# BUOY 1 DATA
# ============================================================

with col1:

    st.markdown("### 🟦 Buoy 1")

    c1, c2 = st.columns(2)

    with c1:

        st.metric(
            "🌡 Temperature",
            f"{st.session_state.temperature:.2f} °C"
        )

        st.metric(
            "📍 Latitude",
            f"{st.session_state.buoy1_lat:.6f}"
        )

    with c2:

        st.metric(
            "🌊 Wave Height",
            f"{st.session_state.wave_height:.2f} m"
        )

        st.metric(
            "📍 Longitude",
            f"{st.session_state.buoy1_lon:.6f}"
        )

    st.write(
        f"**Buoy Status:** {st.session_state.buoy1_status}"
    )

    st.write(
        f"**Drone Status:** {st.session_state.drone1_status}"
    )

    st.write(
        f"**Distance from home:** {distance1:.2f} m"
    )

    st.write(
        f"**Perimeter:** {perimeter1} m"
    )

    st.write(
        f"**Perimeter Violations:** "
        f"{st.session_state.violations1}"
    )


# ============================================================
# BUOY 2 DATA
# ============================================================

with col2:

    st.markdown("### 🟩 Buoy 2")

    c1, c2 = st.columns(2)

    with c1:

        st.metric(
            "🧂 Salinity",
            f"{st.session_state.salinity:.2f} PSU"
        )

        st.metric(
            "📍 Latitude",
            f"{st.session_state.buoy2_lat:.6f}"
        )

    with c2:

        st.metric(
            "💧 Turbidity",
            f"{st.session_state.turbidity:.2f} NTU"
        )

        st.metric(
            "📍 Longitude",
            f"{st.session_state.buoy2_lon:.6f}"
        )

    st.write(
        f"**Buoy Status:** {st.session_state.buoy2_status}"
    )

    st.write(
        f"**Drone Status:** {st.session_state.drone2_status}"
    )

    st.write(
        f"**Distance from home:** {distance2:.2f} m"
    )

    st.write(
        f"**Perimeter:** {perimeter2} m"
    )

    st.write(
        f"**Perimeter Violations:** "
        f"{st.session_state.violations2}"
    )


# ============================================================
# ALERTS
# ============================================================

if st.session_state.buoy1_status == "OUTSIDE PERIMETER":

    st.error(
        "🚨 ALERT: BUOY 1 HAS LEFT ITS PERIMETER. "
        "DRONE 1 IS INITIATING RECOVERY."
    )


if st.session_state.buoy2_status == "OUTSIDE PERIMETER":

    st.error(
        "🚨 ALERT: BUOY 2 HAS LEFT ITS PERIMETER. "
        "DRONE 2 IS INITIATING RECOVERY."
    )


# ============================================================
# MAP DATA
# ============================================================

map_data = pd.DataFrame(
    [
        {
            "name": "Buoy 1",
            "lat": st.session_state.buoy1_lat,
            "lon": st.session_state.buoy1_lon,
            "type": "Buoy 1"
        },
        {
            "name": "Drone 1",
            "lat": st.session_state.drone1_lat,
            "lon": st.session_state.drone1_lon,
            "type": "Drone 1"
        },
        {
            "name": "Buoy 2",
            "lat": st.session_state.buoy2_lat,
            "lon": st.session_state.buoy2_lon,
            "type": "Buoy 2"
        },
        {
            "name": "Drone 2",
            "lat": st.session_state.drone2_lat,
            "lon": st.session_state.drone2_lon,
            "type": "Drone 2"
        }
    ]
)


# ============================================================
# MAP
# ============================================================

st.subheader("🗺️ Live Autonomous Ocean Map")

map_view = pdk.ViewState(
    latitude=13.085,
    longitude=80.278,
    zoom=12,
    pitch=0
)


# ------------------------------------------------------------
# BUOY LAYER
# ------------------------------------------------------------

buoy_layer = pdk.Layer(
    "ScatterplotLayer",
    data=map_data[
        map_data["type"].str.contains("Buoy")
    ],
    get_position="[lon, lat]",
    get_radius=80,
    pickable=True
)


# ------------------------------------------------------------
# DRONE LAYER
# ------------------------------------------------------------

drone_layer = pdk.Layer(
    "ScatterplotLayer",
    data=map_data[
        map_data["type"].str.contains("Drone")
    ],
    get_position="[lon, lat]",
    get_radius=60,
    pickable=True
)


# ------------------------------------------------------------
# PERIMETER CIRCLES
# ------------------------------------------------------------

perimeter_data = pd.DataFrame(
    [
        {
            "lat": BUOY1_START_LAT,
            "lon": BUOY1_START_LON,
            "radius": perimeter1
        },
        {
            "lat": BUOY2_START_LAT,
            "lon": BUOY2_START_LON,
            "radius": perimeter2
        }
    ]
)


perimeter_layer = pdk.Layer(
    "ScatterplotLayer",
    data=perimeter_data,
    get_position="[lon, lat]",
    get_radius="radius",
    filled=False,
    stroked=True,
    get_line_width=3,
    pickable=False
)


# ------------------------------------------------------------
# HOME POSITIONS
# ------------------------------------------------------------

home_data = pd.DataFrame(
    [
        {
            "lat": BUOY1_START_LAT,
            "lon": BUOY1_START_LON,
            "name": "Buoy 1 Home"
        },
        {
            "lat": BUOY2_START_LAT,
            "lon": BUOY2_START_LON,
            "name": "Buoy 2 Home"
        }
    ]
)


home_layer = pdk.Layer(
    "ScatterplotLayer",
    data=home_data,
    get_position="[lon, lat]",
    get_radius=25,
    pickable=True
)


# ============================================================
# RENDER MAP
# ============================================================

deck = pdk.Deck(
    layers=[
        perimeter_layer,
        home_layer,
        buoy_layer,
        drone_layer
    ],
    initial_view_state=map_view,
    tooltip={
        "text": "{name}"
    }
)

st.pydeck_chart(
    deck,
    use_container_width=True
)


# ============================================================
# POSITION TABLE
# ============================================================

st.subheader("📍 GPS Tracking")

gps_table = pd.DataFrame(
    [
        {
            "Object": "Buoy 1",
            "Latitude": round(
                st.session_state.buoy1_lat,
                6
            ),
            "Longitude": round(
                st.session_state.buoy1_lon,
                6
            ),
            "Status": st.session_state.buoy1_status
        },
        {
            "Object": "Drone 1",
            "Latitude": round(
                st.session_state.drone1_lat,
                6
            ),
            "Longitude": round(
                st.session_state.drone1_lon,
                6
            ),
            "Status": st.session_state.drone1_status
        },
        {
            "Object": "Buoy 2",
            "Latitude": round(
                st.session_state.buoy2_lat,
                6
            ),
            "Longitude": round(
                st.session_state.buoy2_lon,
                6
            ),
            "Status": st.session_state.buoy2_status
        },
        {
            "Object": "Drone 2",
            "Latitude": round(
                st.session_state.drone2_lat,
                6
            ),
            "Longitude": round(
                st.session_state.drone2_lon,
                6
            ),
            "Status": st.session_state.drone2_status
        }
    ]
)

st.dataframe(
    gps_table,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# SYSTEM STATUS
# ============================================================

st.subheader("🤖 Autonomous System Status")

status1, status2 = st.columns(2)


with status1:

    st.markdown("### 🚁 Drone 1")

    if st.session_state.drone1_status == "Monitoring":

        st.success(
            "Drone 1 is monitoring Buoy 1."
        )

    else:

        st.warning(
            f"Drone 1: {st.session_state.drone1_status}"
        )


with status2:

    st.markdown("### 🚁 Drone 2")

    if st.session_state.drone2_status == "Monitoring":

        st.success(
            "Drone 2 is monitoring Buoy 2."
        )

    else:

        st.warning(
            f"Drone 2: {st.session_state.drone2_status}"
        )


# ============================================================
# SIMULATION INFORMATION
# ============================================================

st.subheader("📊 Simulation Information")

info1, info2, info3 = st.columns(3)

with info1:

    st.metric(
        "Simulation Step",
        st.session_state.simulation_step
    )

with info2:

    st.metric(
        "Buoy 1 Violations",
        st.session_state.violations1
    )

with info3:

    st.metric(
        "Buoy 2 Violations",
        st.session_state.violations2
    )


# ============================================================
# AUTO REFRESH
# ============================================================

if start_simulation:

    time.sleep(0.5)

    st.rerun()
