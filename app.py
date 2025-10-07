import panel as pn
import geopandas as gpd
import folium

pn.extension()

mbta_lines = gpd.read_file(
    "data/MBTA_data/MBTA Rapid Transit Lines/GISDATA_MBTA_ARCLine.shp"
)
mbta_stations = gpd.read_file(
    "data/MBTA_data/MBTA Rapid Transit Labels/GISDATA_MBTA_NODEPoint.shp"
)
dorms = gpd.read_file("data/NortheasternDorm_data/layers/POINT.shp")

line_colors = {
    "RED": "red",
    "ORANGE": "orange",
    "GREEN": "green",
    "BLUE": "blue",
    "SILVER": "gray",
}


# CALLBACKS
def create_folium_map(
    show_lines=True, show_stations=True, show_dorms=True, selected_lines=None
):
    m = folium.Map(location=[42.3601, -71.0589], zoom_start=12)

    if show_lines:
        for line_name, color in line_colors.items():
            if selected_lines is None or line_name in selected_lines:
                line_data = mbta_lines[mbta_lines["line"] == line_name]
                if not line_data.empty:
                    folium.GeoJson(
                        line_data,
                        name=f"{line_name} Line",
                        style_function=lambda x, color=color: {
                            "color": color,
                            "weight": 3,
                            "opacity": 0.7,
                        },
                    ).add_to(m)

    if show_stations:
        for idx, station in mbta_stations.iterrows():
            color = line_colors.get(station["line"].split("/")[0], "gray")
            folium.CircleMarker(
                location=[station.geometry.y, station.geometry.x],
                radius=5,
                popup=f"{station['station']} ({station['line']})",
                color=color,
                fill=True,
                fillColor=color,
            ).add_to(m)

    if show_dorms:
        for idx, dorm in dorms.iterrows():
            folium.Marker(
                location=[dorm.geometry.y, dorm.geometry.x],
                popup=dorm["Name"],
                icon=folium.Icon(color="red", icon="home", prefix="fa"),
            ).add_to(m)

    folium.LayerControl().add_to(m)

    return m


line_selector = pn.widgets.CheckBoxGroup(
    name="MBTA Lines",
    options=["RED", "ORANGE", "GREEN", "BLUE", "SILVER"],
    value=["RED", "ORANGE", "GREEN", "BLUE", "SILVER"],
)

show_stations_toggle = pn.widgets.Checkbox(name="Show Stations", value=True)
show_dorms_toggle = pn.widgets.Checkbox(name="Show Dorms", value=True)

initial_map = create_folium_map()
folium_pane = pn.pane.plot.Folium(initial_map, height=600, sizing_mode="stretch_both")


def update_map(event):
    new_map = create_folium_map(
        show_lines=True,
        show_stations=show_stations_toggle.value,
        show_dorms=show_dorms_toggle.value,
        selected_lines=line_selector.value,
    )
    folium_pane.object = new_map


line_selector.param.watch(update_map, "value")
show_stations_toggle.param.watch(update_map, "value")
show_dorms_toggle.param.watch(update_map, "value")

# DASHBOARD WIDGET CONTAINERS
card_width = 320

search_card = pn.Card(
    pn.Column(
        line_selector,
        show_stations_toggle,
        show_dorms_toggle,
    ),
    title="Map Controls",
    width=card_width,
    collapsed=False,
)

# LAYOUT
layout = pn.template.FastListTemplate(
    title="MBTA Transit Dashboard",
    sidebar=[search_card],
    theme_toggle=False,
    main=[folium_pane],
    header_background="#a93226",
).servable()
