import pandas as pd
import geopandas as gpd


class DashApi:

    def get_GDF(self, filepath: str, shapefile=False):
        if shapefile:
            gdf = gpd.read_file(filepath)
        else:
            df = pd.read_csv(filepath)
            df["geometry"] = gpd.GeoSeries.from_wkt(df["geometry"])
            gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
        return gdf

    def get_line_colors(self):
        line_colors = {
            "RED": "red",
            "ORANGE": "orange",
            "GREEN": "green",
            "BLUE": "blue",
            "SILVER": "gray",
        }
        return line_colors

    def get_convenience_stores(self, data: pd.DataFrame):
        """
        data: pd.DataFrame
        Used for food_retail dataset,
        filters for convenience stores on store_type column
        returns: pd.DataFrame subset of convenience stores
        """
        convenience_stores = data[
            data["store_type"] == "Convenience Stores, Pharmacies, and Drug Stores"
        ]
        return convenience_stores

    def get_grocery_stores(self, data: pd.DataFrame):
        """
        data: pd.DataFrame
        Used for food_retail dataset,
        filters for grocery stores on store_type column
        returns: pd.DataFrame subset of grocery stores
        """
        grocery_stores = data[data["store_type"] == "Supermarket or Other Grocery"]
        return grocery_stores

    def get_boston_trader_joes(self, data: pd.DataFrame):
        """
        data: pd.DataFrame
        Used for food_retail dataset,
        filters for trader joe's stores on store_name column
        returns: pd.DataFrame subset of trader joe's stores
        """
        boston_zips = [2116, 2115, 2446, 2139, 2494, 2476, 2465, 2138, 1803, 1906, 1960]
        boston_tjs = data[data["postal_cod"].isin(boston_zips)]
        return boston_tjs

    def align_crs(self, dorms, convenience_stores, grocery_stores, boston_tjs):
        """
        Aligns the coordinate reference systems (CRS) of multiple GeoDataFrames to ensure they match.

        Parameters:
        dorms (gpd.GeoDataFrame): GeoDataFrame containing dormitory locations.
        convencience_stores (gpd.GeoDataFrame): GeoDataFrame containing convenience store locations.
        grocery_stores (gpd.GeoDataFrame): GeoDataFrame containing grocery store locations.
        trader_joes (gpd.GeoDataFrame): GeoDataFrame containing Trader Joe's store locations.

        Returns:
        tuple: A tuple containing the aligned GeoDataFrames in the order they were provided.
        """
        if convenience_stores.crs != dorms.crs:
            convenience_stores = convenience_stores.to_crs(dorms.crs)
        if grocery_stores.crs != dorms.crs:
            grocery_stores = grocery_stores.to_crs(dorms.crs)
        if boston_tjs.crs != dorms.crs:
            boston_tjs = boston_tjs.to_crs(dorms.crs)
        return convenience_stores, grocery_stores, boston_tjs
