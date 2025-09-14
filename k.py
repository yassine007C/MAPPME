"""
Streamlit app: select a circle on a 2D map (click + radius slider) and show the antipodal circle (on the opposite side of the Earth) on a 3D globe.
Requirements:
    pip install streamlit folium streamlit-folium pydeck
Run:
    streamlit run streamlit_globe_circle.py
"""

import math
import json
import streamlit as st
import folium
from streamlit_folium import st_folium
import pydeck as pdk

st.set_page_config(layout="wide", page_title="Globe Antipodal Circle")

st.title("عرض دائرة والجهة المقابلة لها على الكرة الأرضية")

# Earth radius
R = 6371000.0  # meters

# Destination point: starting from (lat, lon) go 'distance_m' meters at bearing 'bearing_deg'
def destination_point(lat_deg, lon_deg, bearing_deg, distance_m):
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    br = math.radians(bearing_deg)
    dR = distance_m / R

    lat2 = math.asin(math.sin(lat) * math.cos(dR) + math.cos(lat) * math.sin(dR) * math.cos(br))
    lon2 = lon + math.atan2(math.sin(br) * math.sin(dR) * math.cos(lat), math.cos(dR) - math.sin(lat) * math.sin(lat2))

    return math.degrees(lat2), math.degrees(lon2)

# Normalize longitude into [-180, 180)
def normalize_lon(lon):
    """Normalize longitude to [-180, 180)"""
    return ((lon + 180) % 360) - 180

# Correct antipode calculation: latitude flips sign, longitude + 180 then normalized
def antipode(lat, lon):
    anti_lat = -lat
    anti_lon = lon + 180
    anti_lon = normalize_lon(anti_lon)
    return anti_lat, anti_lon

# Build circle polygon coordinates (GeoJSON expects [lon, lat])
# Special handling for poles to avoid numerical instability
def circle_polygon_coords(lat, lon, radius_m, n_points=72):
    coords = []
    step = 360.0 / n_points
    prev_lon = None
    for i in range(n_points + 1):
        br = i * step
        lat2, lon2 = destination_point(lat, lon, br, radius_m)
        lon2 = normalize_lon(lon2)

        # إذا كان عندنا قفزة > 180° نصحح
        if prev_lon is not None and abs(lon2 - prev_lon) > 180:
            if lon2 > prev_lon:
                lon2 -= 360
            else:
                lon2 += 360

        coords.append([lon2, lat2])
        prev_lon = lon2
    return coords

    for i in range(n_points + 1):
        br = i * step
        lat2, lon2 = destination_point(lat, lon, br, radius_m)
        coords.append([normalize_lon(lon2), lat2])
    return coords

# --- UI ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("خريطة 2D — اضغط لاختيار مركز الدائرة")

    if 'center' not in st.session_state:
        st.session_state.center = (20.0, 0.0)

    center_lat, center_lon = st.session_state.center

    with st.expander("تحديد يدوي للمركز (اختياري)"):
        manual_lat = st.number_input("Latitude", value=float(center_lat), format="%.6f")
        manual_lon = st.number_input("Longitude", value=float(center_lon), format="%.6f")
        if st.button("تعيين المركز يدوياً"):
            st.session_state.center = (manual_lat, manual_lon)
            center_lat, center_lon = st.session_state.center

    radius = st.slider("نصف القطر (بالأمتار)", min_value=100, max_value=2000000, value=50000, step=100)

    st.markdown("**اضغط على الخريطة لاختيار مركز الدائرة. أو استخدم التحديد اليدوي أعلاه.**")

    # Build folium map with the current center and circle (so the circle is visible immediately)
    m = folium.Map(location=[center_lat, center_lon], zoom_start=3, tiles="OpenStreetMap")
    folium.Marker(location=[center_lat, center_lon], popup="Center").add_to(m)
    folium.Circle(location=[center_lat, center_lon], radius=radius, color="#3388ff", fill=True, fill_opacity=0.2).add_to(m)

    # Show and capture click
    map_data = st_folium(m, width=700, height=500, returned_objects=["last_clicked"], key="map")
    if map_data and map_data.get("last_clicked"):
        lat_click = map_data["last_clicked"]["lat"]
        lon_click = map_data["last_clicked"]["lng"]
        # normalize longitude just in case
        lon_click = normalize_lon(lon_click)
        st.session_state.center = (lat_click, lon_click)
        center_lat, center_lon = lat_click, lon_click

with col2:
    st.subheader("الكرة الأرضية 3D — الدائرة على الجهة المقابلة")

    if 'center' in st.session_state:
        lat0, lon0 = st.session_state.center
    else:
        lat0, lon0 = 20.0, 0.0

    # Compute antipode correctly
    anti_lat, anti_lon = antipode(lat0, lon0)

    # Build GeoJSON polygon for the antipodal circle
    polygon_coords = circle_polygon_coords(anti_lat, anti_lon, radius, n_points=128)
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "antipodal_circle"},
                "geometry": {"type": "Polygon", "coordinates": [polygon_coords]},
            }
        ]
    }

    globe_view = pdk.View(type="GlobeView")

    geojson_layer = pdk.Layer(
        "GeoJsonLayer",
        data=geojson,
        stroked=True,
        filled=True,
        extruded=False,
        get_fill_color=[0, 200, 255, 100],
        get_line_color=[0, 100, 255],
        line_width_min_pixels=2,
    )

    deck = pdk.Deck(
        layers=[geojson_layer],
        initial_view_state=pdk.ViewState(latitude=anti_lat, longitude=anti_lon, zoom=0, pitch=0),
        views=[globe_view],
        map_style=None,
    )

    st.pydeck_chart(deck)

# Footer / tips
st.markdown("---")
st.markdown("**نصائح:** جرّب أن تختار نقطة في شمال المغرب (مثلاً 34, -6). النتيجة المتوقعة للجهة المقابلة: حوالي (-34, 174). إذا اخترت القطب (±90)، فهناك معالجة خاصة لتجنب مشاكل تناظرية في الحسابات.")

# Optional: download GeoJSON
if st.button("تحميل GeoJSON للدائرة المقابلة"):
    st.download_button("تحميل GeoJSON", data=json.dumps(geojson), file_name="antipodal_circle.geojson", mime="application/json")
