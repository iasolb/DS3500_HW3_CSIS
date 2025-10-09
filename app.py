import panel as pn
import geopandas as gpd
import folium
import pandas as pd
from api import DashApi

pn.extension()

api = DashApi()

# load all data
data = api.load_all_data()
mbta_lines, mbta_stations, dorms, food_retail, trader_joes = (
    data["mbta_lines"],
    data["mbta_stations"],
    data["dorms"],
    data["food_retail"],
    data["trader_joes"],
)

convenience_stores = api.get_convenience_stores(food_retail)
grocery_stores = api.get_grocery_stores(food_retail)
boston_tjs = api.get_boston_trader_joes(trader_joes)
line_colors = api.get_line_colors()
dorms = api.add_nearest_store_columns(
    dorms, convenience_stores, grocery_stores, boston_tjs
)

# Global variable to store user location
user_location = None


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

    # Add user location if it exists
    if user_location is not None and len(user_location) > 0:
        user_loc = user_location.iloc[0]
        popup_text = f"""<b>Your Location</b><br>
                        <b>Address:</b> {user_loc['address']}"""

        if pd.notna(user_loc.get("nearest_grocery_miles")):
            popup_text += f"""<br><br><b>Nearest Grocery:</b> {user_loc['nearest_grocery_name']}<br>
                            <b>Distance:</b> {user_loc['nearest_grocery_miles']:.2f} miles"""

        if pd.notna(user_loc.get("nearest_pharmacy_miles")):
            popup_text += f"""<br><br><b>Nearest Pharmacy:</b> {user_loc['nearest_pharmacy_name']}<br>
                            <b>Distance:</b> {user_loc['nearest_pharmacy_miles']:.2f} miles"""

        if pd.notna(user_loc.get("nearest_tj_miles")):
            popup_text += f"""<br><br><b>Nearest Trader Joe's:</b> {user_loc['nearest_tj_name']}<br>
                            <b>Distance:</b> {user_loc['nearest_tj_miles']:.2f} miles"""

        folium.Marker(
            location=[user_loc.geometry.y, user_loc.geometry.x],
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color="blue", icon="user", prefix="fa"),
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


# WIDGETS
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

# User location widgets
address_input = pn.widgets.TextInput(
    name="Enter Your Address", placeholder="123 Main St, Boston, MA", width=280
)

geocode_button = pn.widgets.Button(
    name="Add My Location", button_type="primary", width=280
)

user_location_info = pn.pane.Markdown("", width=280)


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


def geocode_user_address(event):
    global user_location

    address = address_input.value
    if not address:
        user_location_info.object = "⚠️ Please enter an address"
        return

    # Geocode the address
    coords = api.geocode_address(address)

    if coords is None:
        user_location_info.object = "❌ Could not find address. Try adding 'Boston, MA'"
        return

    lat, lon = coords

    # Create GeoDataFrame for user location
    user_location = api.create_user_location_gdf(lat, lon, address)

    # Calculate distances to nearest stores
    user_location = api.add_nearest_store_columns(
        user_location, convenience_stores, grocery_stores, boston_tjs
    )

    # Format the info message
    info = f"📍 **Your Location:** {address}\n\n"

    if pd.notna(user_location.iloc[0]["nearest_grocery_miles"]):
        info += (
            f"🛒 **Nearest Grocery:** {user_location.iloc[0]['nearest_grocery_name']}\n"
        )
        info += f"   └ {user_location.iloc[0]['nearest_grocery_miles']:.2f} miles\n\n"

    if pd.notna(user_location.iloc[0]["nearest_pharmacy_miles"]):
        info += f"💊 **Nearest Pharmacy:** {user_location.iloc[0]['nearest_pharmacy_name']}\n"
        info += f"   └ {user_location.iloc[0]['nearest_pharmacy_miles']:.2f} miles\n\n"

    if pd.notna(user_location.iloc[0]["nearest_tj_miles"]):
        info += (
            f"�️ **Nearest Trader Joe's:** {user_location.iloc[0]['nearest_tj_name']}\n"
        )
        info += f"   └ {user_location.iloc[0]['nearest_tj_miles']:.2f} miles"

    user_location_info.object = info

    # Trigger map update
    update_map(None)


line_selector.param.watch(update_map, "value")
show_stations_toggle.param.watch(update_map, "value")
show_dorms_toggle.param.watch(update_map, "value")
show_grocery_toggle.param.watch(update_map, "value")
show_pharmacy_toggle.param.watch(update_map, "value")
show_tj_toggle.param.watch(update_map, "value")
show_distance_lines_toggle.param.watch(update_map, "value")
geocode_button.on_click(geocode_user_address)

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
        "---",
        "### Your Location",
        address_input,
        geocode_button,
        user_location_info,
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
