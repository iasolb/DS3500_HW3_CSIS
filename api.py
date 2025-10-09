import pandas as pd
import geopandas as gpd
from typing import Dict, Tuple, Optional
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


class DashApi:
    """API for loading and processing geographic and transit data for the MBTA dashboard."""

    # Constants
    BOSTON_ZIPS = [2116, 2115, 2446, 2139, 2494, 2476, 2465, 2138, 1803, 1906, 1960]
    STORE_TYPE_CONVENIENCE = "Convenience Stores, Pharmacies, and Drug Stores"
    STORE_TYPE_GROCERY = "Supermarket or Other Grocery"
    METERS_PER_MILE = 1609.34
    UTM_ZONE_19N = "EPSG:32619"  # For accurate distance calculation in Boston area
    WGS84 = "EPSG:4326"

    LINE_COLORS = {
        "RED": "red",
        "ORANGE": "orange",
        "GREEN": "green",
        "BLUE": "blue",
        "SILVER": "gray",
    }

    # ============================================================================
    # Data Loading Methods
    # ============================================================================

    def get_GDF(self, filepath: str, shapefile: bool = False) -> gpd.GeoDataFrame:
        """
        Load geographic data from either a shapefile or CSV.

        Args:
            filepath: Path to the data file
            shapefile: If True, load as shapefile. If False, load as CSV with WKT geometry

        Returns:
            GeoDataFrame with the loaded data
        """
        if shapefile:
            gdf = gpd.read_file(filepath)
        else:
            df = pd.read_csv(filepath)
            df["geometry"] = gpd.GeoSeries.from_wkt(df["geometry"])
            gdf = gpd.GeoDataFrame(df, geometry="geometry", crs=self.WGS84)
        return gdf

    def load_all_data(self, data_dir: str = "data") -> Dict[str, gpd.GeoDataFrame]:
        """
        Load all required datasets for the dashboard.

        Args:
            data_dir: Base directory containing data folders

        Returns:
            Dictionary with keys: mbta_lines, mbta_stations, dorms, food_retail, trader_joes
        """
        return {
            "mbta_lines": self.get_GDF(
                f"{data_dir}/MBTA_data/MBTA Rapid Transit Lines/GISDATA_MBTA_ARCLine.shp",
                shapefile=True,
            ),
            "mbta_stations": self.get_GDF(
                f"{data_dir}/MBTA_data/MBTA Rapid Transit Labels/GISDATA_MBTA_NODEPoint.shp",
                shapefile=True,
            ),
            "dorms": self.get_GDF(
                f"{data_dir}/NortheasternDorm_data/dorms_with_prices.csv",
                shapefile=False,
            ),
            "food_retail": self.get_GDF(
                f"{data_dir}/Food_Data/food_retail.shp", shapefile=True
            ),
            "trader_joes": self.get_GDF(
                f"{data_dir}/Food_Data/trader_joes.shp", shapefile=True
            ),
        }

    # ============================================================================
    # Configuration Getters
    # ============================================================================

    def get_line_colors(self) -> Dict[str, str]:
        """Get the color mapping for MBTA transit lines."""
        return self.LINE_COLORS

    def get_boston_zips(self) -> list:
        """Get list of Boston-area zip codes."""
        return self.BOSTON_ZIPS

    # ============================================================================
    # Data Filtering Methods
    # ============================================================================

    def filter_by_column(self, data: pd.DataFrame, column: str, value) -> pd.DataFrame:
        """
        Generic filter for DataFrame columns.

        Args:
            data: DataFrame to filter
            column: Column name to filter on
            value: Value to match (can be single value or list for .isin())

        Returns:
            Filtered DataFrame
        """
        if isinstance(value, list):
            return data[data[column].isin(value)]
        return data[data[column] == value]

    def get_convenience_stores(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Filter food retail data for convenience stores and pharmacies.

        Args:
            data: Food retail DataFrame

        Returns:
            DataFrame subset containing only convenience stores/pharmacies
        """
        return self.filter_by_column(data, "store_type", self.STORE_TYPE_CONVENIENCE)

    def get_grocery_stores(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Filter food retail data for grocery stores.

        Args:
            data: Food retail DataFrame

        Returns:
            DataFrame subset containing only grocery stores
        """
        return self.filter_by_column(data, "store_type", self.STORE_TYPE_GROCERY)

    def get_boston_trader_joes(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Filter Trader Joe's data for Boston-area locations.

        Args:
            data: Trader Joe's DataFrame

        Returns:
            DataFrame subset containing only Boston-area Trader Joe's
        """
        return self.filter_by_column(data, "postal_cod", self.BOSTON_ZIPS)

    # ============================================================================
    # CRS and Geometry Operations
    # ============================================================================

    def align_crs(
        self,
        dorms: gpd.GeoDataFrame,
        convenience_stores: gpd.GeoDataFrame,
        grocery_stores: gpd.GeoDataFrame,
        boston_tjs: gpd.GeoDataFrame,
    ) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
        """
        Align the coordinate reference systems (CRS) of store GeoDataFrames to match dorms.

        Args:
            dorms: GeoDataFrame containing dormitory locations (reference CRS)
            convenience_stores: GeoDataFrame containing convenience store locations
            grocery_stores: GeoDataFrame containing grocery store locations
            boston_tjs: GeoDataFrame containing Trader Joe's store locations

        Returns:
            Tuple of (convenience_stores, grocery_stores, boston_tjs) with aligned CRS
        """
        if convenience_stores.crs != dorms.crs:
            convenience_stores = convenience_stores.to_crs(dorms.crs)
        if grocery_stores.crs != dorms.crs:
            grocery_stores = grocery_stores.to_crs(dorms.crs)
        if boston_tjs.crs != dorms.crs:
            boston_tjs = boston_tjs.to_crs(dorms.crs)
        return convenience_stores, grocery_stores, boston_tjs

    def find_nearest_store(
        self, dorm_geom, stores_gdf: gpd.GeoDataFrame
    ) -> Tuple[Optional[float], Optional[pd.Series]]:
        """
        Find the nearest store to a dorm location and calculate distance in meters.

        Uses UTM projection for accurate distance calculation.

        Args:
            dorm_geom: Geometry of the dorm location
            stores_gdf: GeoDataFrame containing store locations

        Returns:
            Tuple of (distance_in_meters, nearest_store_row) or (None, None) if no stores
        """
        if len(stores_gdf) == 0:
            return None, None

        # Convert to projected CRS for accurate distance calculation (UTM Zone 19N for Boston)
        dorm_proj = gpd.GeoSeries([dorm_geom], crs=self.WGS84).to_crs(self.UTM_ZONE_19N)
        stores_proj = stores_gdf.to_crs(self.UTM_ZONE_19N)

        distances = stores_proj.distance(dorm_proj.iloc[0])
        min_distance = distances.min()
        nearest_store_idx = distances.argmin()
        nearest_store = stores_gdf.iloc[nearest_store_idx]

        return min_distance, nearest_store

    def _add_store_info_to_dorm(
        self,
        dorms: gpd.GeoDataFrame,
        idx: int,
        dist: Optional[float],
        store: Optional[pd.Series],
        prefix: str,
        store_name_key: str = "store_name",
        default_name: str = "Unknown",
    ) -> None:
        """
        Helper method to add nearest store information to a dorm row.

        Args:
            dorms: GeoDataFrame to modify
            idx: Index of the dorm row
            dist: Distance to nearest store in meters
            store: Series containing store information
            prefix: Prefix for column names (e.g., 'grocery', 'pharmacy', 'tj')
            store_name_key: Key to use for store name in the store Series
        """
        if dist is not None:
            dorms.at[idx, f"nearest_{prefix}_dist_m"] = dist
            dorms.at[idx, f"nearest_{prefix}_miles"] = dist / self.METERS_PER_MILE
            dorms.at[idx, f"nearest_{prefix}_name"] = store.get(
                store_name_key, default_name
            )
            dorms.at[idx, f"nearest_{prefix}_geom"] = store.geometry

    def add_nearest_store_columns(
        self,
        dorms: gpd.GeoDataFrame,
        convenience_stores: gpd.GeoDataFrame,
        grocery_stores: gpd.GeoDataFrame,
        boston_tjs: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        for idx, dorm in dorms.iterrows():
            dist, store = self.find_nearest_store(dorm.geometry, grocery_stores)
            self._add_store_info_to_dorm(
                dorms,
                idx,
                dist,
                store,
                "grocery",
                store_name_key="coname",
                default_name="Unknown Grocery Store",
            )

            dist, store = self.find_nearest_store(dorm.geometry, convenience_stores)
            self._add_store_info_to_dorm(
                dorms,
                idx,
                dist,
                store,
                "pharmacy",
                store_name_key="coname",
                default_name="Unknown Pharmacy",
            )

            dist, store = self.find_nearest_store(dorm.geometry, boston_tjs)
            self._add_store_info_to_dorm(
                dorms,
                idx,
                dist,
                store,
                "tj",
                store_name_key="city_name",
                default_name="Trader Joe's",
            )

        return dorms

    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Geocode an address to latitude/longitude coordinates.

        Args:
            address: Street address to geocode

            Returns:
                Tuple of (latitude, longitude) or None if geocoding fails
        """
        try:
            geolocator = Nominatim(user_agent="mbta_dashboard")
            location = geolocator.geocode(address + ", Boston, MA")
            if location:
                return (location.latitude, location.longitude)
            return None
        except (GeocoderTimedOut, GeocoderServiceError):
            return None

    def create_user_location_gdf(
        self, lat: float, lon: float, address: str
    ) -> gpd.GeoDataFrame:
        """
        Create a GeoDataFrame for a user-provided location.

        Args:
            lat: Latitude
            lon: Longitude
            address: Address string

        Returns:
            GeoDataFrame with single point
        """
        from shapely.geometry import Point

        gdf = gpd.GeoDataFrame(
            {"address": [address]}, geometry=[Point(lon, lat)], crs=self.WGS84
        )

        return gdf
