"""
Streamlit app: select a circle on a 2D map (click + radius slider) and show the corresponding circle on a 3D globe.
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

st.set_page_config(layout="wide", page_title="Globe Circle Selector")

st.title("عرض دائرة على الخريطة واظهارها على الكرة الأرضية")

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
    map_data = st_folium(m, width=700, height=500)
    # st_folium returns last_clicked
    last_clicked = map_data.get("last_clicked") if isinstance(map_data, dict) else None

    if last_clicked:
        lat_click = last_clicked.get('lat')
        lon_click = last_clicked.get('lng')
        st.session_state.center = (lat_click, lon_click)
        center_lat, center_lon = lat_click, lon_click

    # Draw the chosen circle on the folium map
    folium.Circle(location=[center_lat, center_lon], radius=radius, color="#3388ff", fill=True, fill_opacity=0.2).add_to(m)
    folium.Marker(location=[center_lat, center_lon], popup="Center").add_to(m)

    # Re-render map with circle
    st_folium(m, width=700, height=500, returned_objects=["last_clicked"])  # second rendering so user sees circle

with col2:
    st.subheader("الكرة الأرضية 3D — الدائرة المقابلة")

    if 'center' in st.session_state:
        lat0, lon0 = st.session_state.center
    else:
        lat0, lon0 = 20.0, 0.0

    # Build GeoJSON polygon for the circle
    polygon_coords = circle_polygon_coords(lat0, lon0, radius, n_points=128)
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "selected_circle"},
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
        get_fill_color=[255, 160, 0, 100],
        get_line_color=[255, 100, 0],
        line_width_min_pixels=2,
    )

    deck = pdk.Deck(
        layers=[geojson_layer],
        initial_view_state=pdk.ViewState(latitude=lat0, longitude=lon0, zoom=0, pitch=0),
        views=[globe_view],
        map_style=None,
    )

    st.pydeck_chart(deck)

# Footer / tips
st.markdown("---")
st.markdown("**نصائح:** اضغط على الخريطة في العمود الأيسر لاختيار مركز الدائرة، وغير نصف القطر عبر شريط التمرير. الخريطة ثلاثية الأبعاد في العمود الأيمن تُظهر الموقع المقابل على الكرة الأرضية.")

# Optional: download GeoJSON
if st.button("تحميل GeoJSON للدائرة"):
    st.download_button("تحميل GeoJSON", data=json.dumps(geojson), file_name="circle.geojson", mime="application/json")
