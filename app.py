import panel as pn
import geopandas as gpd
import folium
import pandas as pd
from api import DashApi

pn.extension()

api = DashApi()

mbta_lines = api.get_GDF(
    "data/MBTA_data/MBTA Rapid Transit Lines/GISDATA_MBTA_ARCLine.shp", shapefile=True
)
mbta_stations = api.get_GDF(
    "data/MBTA_data/MBTA Rapid Transit Labels/GISDATA_MBTA_NODEPoint.shp",
    shapefile=True,
)
dorms = api.get_GDF("data/NortheasternDorm_data/dorms_with_prices.csv", shapefile=False)
food_retail = api.get_GDF("data/Food_Data/food_retail.shp", shapefile=True)
trader_joes = api.get_GDF("data/Food_Data/trader_joes.shp", shapefile=True)

convenience_stores = api.get_convenience_stores(food_retail)
grocery_stores = api.get_grocery_stores(food_retail)
boston_tjs = api.get_boston_trader_joes(trader_joes)

convenience_stores, grocery_stores, boston_tjs = api.align_crs(
    dorms, convenience_stores, grocery_stores, boston_tjs
)

line_colors = api.get_line_colors()


# CALCULATIONS
# Calculate Distance
def find_nearest_store(dorm_geom, stores_gdf):
    """Find distance to nearest store in meters"""
    if len(stores_gdf) == 0:
        return None, None

    # Convert to projected CRS for accurate distance calculation (UTM Zone 19N for Boston)
    dorm_proj = gpd.GeoSeries([dorm_geom], crs="EPSG:4326").to_crs("EPSG:32619")
    stores_proj = stores_gdf.to_crs("EPSG:32619")

    distances = stores_proj.distance(dorm_proj.iloc[0])
    min_distance = distances.min()
    nearest_store_idx = distances.argmin()
    nearest_store = stores_gdf.iloc[nearest_store_idx]

    return min_distance, nearest_store


# Add distance columns to dorms
for idx, dorm in dorms.iterrows():

    # Grocery stores
    dist, store = find_nearest_store(dorm.geometry, grocery_stores)
    if dist is not None:
        dorms.at[idx, "nearest_grocery_dist_m"] = dist
        dorms.at[idx, "nearest_grocery_miles"] = dist / 1609.34
        dorms.at[idx, "nearest_grocery_name"] = store.get("store_name", "Unknown")
        dorms.at[idx, "nearest_grocery_geom"] = store.geometry

    # Pharmacies
    dist, store = find_nearest_store(dorm.geometry, convenience_stores)
    if dist is not None:
        dorms.at[idx, "nearest_pharmacy_dist_m"] = dist
        dorms.at[idx, "nearest_pharmacy_miles"] = dist / 1609.34
        dorms.at[idx, "nearest_pharmacy_name"] = store.get("store_name", "Unknown")
        dorms.at[idx, "nearest_pharmacy_geom"] = store.geometry

    # Trader Joe's
    dist, store = find_nearest_store(dorm.geometry, boston_tjs)
    if dist is not None:
        dorms.at[idx, "nearest_tj_dist_m"] = dist
        dorms.at[idx, "nearest_tj_miles"] = dist / 1609.34
        dorms.at[idx, "nearest_tj_name"] = store.get("name", "Trader Joe's")
        dorms.at[idx, "nearest_tj_geom"] = store.geometry


# CALLBACKS
def create_folium_map(
    show_lines=True,
    show_stations=True,
    show_dorms=True,
    show_grocery=False,
    show_pharmacy=False,
    show_tj=False,
    show_distance_lines=False,
    selected_lines=None,
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
            popup_text = f"""<b>Dorm Name:</b> {dorm['Name']}<br>
                            <b>Price Per Semester:</b> {dorm['Price']}<br>
                            <b>Monthly Estimate:</b> {dorm['MonthlyPriceEstimate']}"""

            if "nearest_grocery_miles" in dorm and pd.notna(
                dorm["nearest_grocery_miles"]
            ):
                popup_text += f"""<br><br><b>Nearest Grocery:</b> {dorm['nearest_grocery_name']}<br>
                                    <b>Distance:</b> {dorm['nearest_grocery_miles']:.2f} miles"""

            if "nearest_pharmacy_miles" in dorm and pd.notna(
                dorm["nearest_pharmacy_miles"]
            ):
                popup_text += f"""<br><br><b>Nearest Pharmacy:</b> {dorm['nearest_pharmacy_name']}<br>
                                    <b>Distance:</b> {dorm['nearest_pharmacy_miles']:.2f} miles"""

            if "nearest_tj_miles" in dorm and pd.notna(dorm["nearest_tj_miles"]):
                popup_text += f"""<br><br><b>Nearest Trader Joe's:</b> {dorm['nearest_tj_name']}<br>
                                    <b>Distance:</b> {dorm['nearest_tj_miles']:.2f} miles"""

            folium.Marker(
                location=[dorm.geometry.y, dorm.geometry.x],
                popup=folium.Popup(popup_text, max_width=300),
                icon=folium.Icon(color="red", icon="home", prefix="fa"),
            ).add_to(m)

            # Add distance lines if enabled
            if show_distance_lines:
                if (
                    show_grocery
                    and "nearest_grocery_geom" in dorm
                    and pd.notna(dorm["nearest_grocery_geom"])
                ):
                    folium.PolyLine(
                        locations=[
                            [dorm.geometry.y, dorm.geometry.x],
                            [
                                dorm["nearest_grocery_geom"].y,
                                dorm["nearest_grocery_geom"].x,
                            ],
                        ],
                        color="green",
                        weight=2,
                        opacity=0.5,
                        dash_array="5",
                    ).add_to(m)

                if (
                    show_pharmacy
                    and "nearest_pharmacy_geom" in dorm
                    and pd.notna(dorm["nearest_pharmacy_geom"])
                ):
                    folium.PolyLine(
                        locations=[
                            [dorm.geometry.y, dorm.geometry.x],
                            [
                                dorm["nearest_pharmacy_geom"].y,
                                dorm["nearest_pharmacy_geom"].x,
                            ],
                        ],
                        color="purple",
                        weight=2,
                        opacity=0.5,
                        dash_array="5",
                    ).add_to(m)

                if (
                    show_tj
                    and "nearest_tj_geom" in dorm
                    and pd.notna(dorm["nearest_tj_geom"])
                ):
                    folium.PolyLine(
                        locations=[
                            [dorm.geometry.y, dorm.geometry.x],
                            [dorm["nearest_tj_geom"].y, dorm["nearest_tj_geom"].x],
                        ],
                        color="orange",
                        weight=2,
                        opacity=0.5,
                        dash_array="5",
                    ).add_to(m)

    # Add grocery stores
    if show_grocery:
        for idx, store in grocery_stores.iterrows():
            folium.Marker(
                location=[store.geometry.y, store.geometry.x],
                popup=store.get("store_name", "Grocery Store"),
                icon=folium.Icon(color="green", icon="shopping-cart", prefix="fa"),
                tooltip="Grocery Store",
            ).add_to(m)

    # Add pharmacies
    if show_pharmacy:
        for idx, store in convenience_stores.iterrows():
            folium.Marker(
                location=[store.geometry.y, store.geometry.x],
                popup=store.get("store_name", "Pharmacy"),
                icon=folium.Icon(color="purple", icon="plus", prefix="fa"),
                tooltip="Pharmacy",
            ).add_to(m)

    # Add Trader Joe's
    if show_tj:
        for idx, store in boston_tjs.iterrows():
            folium.Marker(
                location=[store.geometry.y, store.geometry.x],
                popup=store.get("name", "Trader Joe's"),
                icon=folium.Icon(color="orange", icon="shopping-basket", prefix="fa"),
                tooltip="Trader Joe's",
            ).add_to(m)

    folium.LayerControl().add_to(m)
    return m


# WIDGETS?
line_selector = pn.widgets.CheckBoxGroup(
    name="MBTA Lines",
    options=["RED", "ORANGE", "GREEN", "BLUE", "SILVER"],
    value=["RED", "ORANGE", "GREEN", "BLUE", "SILVER"],
)

show_stations_toggle = pn.widgets.Checkbox(name="Show Stations", value=True)
show_dorms_toggle = pn.widgets.Checkbox(name="Show Dorms", value=True)
show_grocery_toggle = pn.widgets.Checkbox(name="Show Grocery Stores", value=False)
show_pharmacy_toggle = pn.widgets.Checkbox(name="Show Pharmacies", value=False)
show_tj_toggle = pn.widgets.Checkbox(name="Show Trader Joe's", value=False)
show_distance_lines_toggle = pn.widgets.Checkbox(
    name="Show Distance Lines", value=False
)


initial_map = create_folium_map()
folium_pane = pn.pane.plot.Folium(initial_map, height=600, sizing_mode="stretch_both")


def update_map(event):
    new_map = create_folium_map(
        show_lines=True,
        show_stations=show_stations_toggle.value,
        show_dorms=show_dorms_toggle.value,
        show_grocery=show_grocery_toggle.value,
        show_pharmacy=show_pharmacy_toggle.value,
        show_tj=show_tj_toggle.value,
        show_distance_lines=show_distance_lines_toggle.value,
        selected_lines=line_selector.value,
    )
    folium_pane.object = new_map


line_selector.param.watch(update_map, "value")
show_stations_toggle.param.watch(update_map, "value")
show_dorms_toggle.param.watch(update_map, "value")
show_grocery_toggle.param.watch(update_map, "value")
show_pharmacy_toggle.param.watch(update_map, "value")
show_tj_toggle.param.watch(update_map, "value")
show_distance_lines_toggle.param.watch(update_map, "value")

# DASHBOARD WIDGET CONTAINERS
card_width = 320

search_card = pn.Card(
    pn.Column(
        line_selector,
        show_stations_toggle,
        show_dorms_toggle,
        "### Food Access",
        show_grocery_toggle,
        show_pharmacy_toggle,
        show_tj_toggle,
        show_distance_lines_toggle,
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
