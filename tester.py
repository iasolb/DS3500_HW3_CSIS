import panel as pn
import geopandas as gpd
import folium
import pandas as pd

food_retail = gpd.read_file("data/Food_Data/food_retail.shp")
convenience_stores = food_retail[food_retail['store_type'] == "Convenience Stores, Pharmacies, and Drug Stores"]



trader_joes = gpd.read_file("data/Food_Data/trader_joes.shp")
boston_zips = [2116, 2115, 2446, 2139, 2494, 2476, 2465, 2138, 1803, 1906, 1960]
boston_tjs = trader_joes[trader_joes['postal_cod'].isin(boston_zips)]

print(boston_tjs)

