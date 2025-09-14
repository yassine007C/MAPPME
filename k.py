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

# Helper: destination point given start lat/lon, bearing (deg), distance (m)
R = 6371000.0  # Earth radius in meters

def destination_point(lat_deg, lon_deg, bearing_deg, distance_m):
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    br = math.radians(bearing_deg)
    dR = distance_m / R

    lat2 = math.asin(math.sin(lat) * math.cos(dR) + math.cos(lat) * math.sin(dR) * math.cos(br))
    lon2 = lon + math.atan2(math.sin(br) * math.sin(dR) * math.cos(lat), math.cos(dR) - math.sin(lat) * math.sin(lat2))

    return math.degrees(lat2), (math.degrees(lon2) + 540) % 360 - 180  # normalize lon


def circle_polygon_coords(lat, lon, radius_m, n_points=72):
    coords = []
    step = 360.0 / n_points
    for i in range(n_points + 1):
        br = i * step
        lat2, lon2 = destination_point(lat, lon, br, radius_m)
        coords.append([lon2, lat2])  # GeoJSON expects [lon, lat]
    return coords

# Antipode function
def antipode(lat, lon):
    return -lat, ((lon + 180) % 360) - 180

# Layout: left column for 2D folium map, right for globe
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("خريطة 2D — اضغط لاختيار مركز الدائرة")
    # initial center
    if 'center' not in st.session_state:
        st.session_state.center = (20.0, 0.0)

    center_lat, center_lon = st.session_state.center

    m = folium.Map(location=[center_lat, center_lon], zoom_start=2, tiles="OpenStreetMap")

    # If user provided lat/lon inputs manually
    with st.expander("تحديد يدوي للمركز (اختياري)"):
        manual_lat = st.number_input("Latitude", value=float(center_lat), format="%.6f")
        manual_lon = st.number_input("Longitude", value=float(center_lon), format="%.6f")
        if st.button("تعيين المركز يدوياً"):
            st.session_state.center = (manual_lat, manual_lon)
            center_lat, center_lon = st.session_state.center
            m.location = [center_lat, center_lon]
            m.zoom_start = 4

    # Radius slider
    radius = st.slider("نصف القطر (بالأمتار)", min_value=100, max_value=2000000, value=50000, step=100)

    # Draw instructions
    st.markdown("**اضغط على الخريطة لاختيار مركز الدائرة. أو استخدم التحديد اليدوي أعلاه.**")

    # show folium map and capture click
    map_data = st_folium(m, width=700, height=500, returned_objects=["last_clicked"], key="map1")
    if map_data and map_data.get("last_clicked"):
        lat_click = map_data["last_clicked"]["lat"]
        lon_click = map_data["last_clicked"]["lng"]
        st.session_state.center = (lat_click, lon_click)
        center_lat, center_lon = lat_click, lon_click

    # Draw the chosen circle on the folium map
    folium.Circle(location=[center_lat, center_lon], radius=radius, color="#3388ff", fill=True, fill_opacity=0.2).add_to(m)
    folium.Marker(location=[center_lat, center_lon], popup="Center").add_to(m)

    # Re-render map with circle
    st_folium(m, width=700, height=500, key="map2")

with col2:
    st.subheader("الكرة الأرضية 3D — الدائرة على الجهة المقابلة")

    if 'center' in st.session_state:
        lat0, lon0 = st.session_state.center
    else:
        lat0, lon0 = 20.0, 0.0

    # Compute antipode of selected center
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

    # Prepare the PyDeck deck with GlobeView
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
st.markdown("**نصائح:** العمود الأيسر لاختيار المركز ونصف القطر، العمود الأيمن يعرض الدائرة في الجهة المقابلة من الكرة الأرضية.")

# Optional: download GeoJSON
if st.button("تحميل GeoJSON للدائرة المقابلة"):
    st.download_button("تحميل GeoJSON", data=json.dumps(geojson), file_name="antipodal_circle.geojson", mime="application/json")
