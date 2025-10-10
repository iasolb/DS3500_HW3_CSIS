import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Location:
    """Represents a geographical location"""
    name: str
    lat: float
    lng: float
    category: str
    details: Optional[Dict] = None


class BostonDataAPI:
    """API for processing Boston geospatial data"""

    def __init__(self):
        self.dorms_df = None
        self.trader_joes_df = None
        self.food_retail_df = None
        self.mbta_nodes_df = None
        self.mbta_lines_df = None

    def load_data(self):
        """Load all CSV files"""
        try:
            self.dorms_df = pd.read_csv('data/NortheasternDorm_data/layers/dorms_with_prices.csv')
            self.trader_joes_df = pd.read_csv('data/Food_Data/trader_joes.csv')
            self.food_retail_df = pd.read_csv('data/Food_Data/food_retail.csv')
            self.mbta_nodes_df = pd.read_csv('data/MBTA_data/MBTA Rapid Transit Labels/mbta_nodes.csv')
            self.mbta_lines_df = pd.read_csv('data/MBTA_data/MBTA Rapid Transit Lines/mbta_lines.csv')

            # Clean column names
            self.dorms_df.columns = self.dorms_df.columns.str.strip()
            self.food_retail_df.columns = self.food_retail_df.columns.str.strip()

            # Parse geometry for dorms
            self._parse_geometries()

            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False

    def _parse_geometries(self):
        """Parse WKT geometry strings to lat/lng"""

        def parse_point(geom_str):
            try:
                # Handle POINT format: "POINT (lng lat)"
                if pd.isna(geom_str):
                    return None, None
                coords = geom_str.replace('POINT (', '').replace(')', '').split()
                return float(coords[1]), float(coords[0])  # lat, lng
            except:
                return None, None

        # Parse dorm geometries
        if 'geometry' in self.dorms_df.columns:
            self.dorms_df[['lat', 'lng']] = self.dorms_df['geometry'].apply(
                lambda x: pd.Series(parse_point(x))
            )

        # Parse MBTA node geometries
        if 'geometry' in self.mbta_nodes_df.columns:
            self.mbta_nodes_df[['lat', 'lng']] = self.mbta_nodes_df['geometry'].apply(
                lambda x: pd.Series(parse_point(x))
            )

    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points on Earth
        Returns distance in miles
        """
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        c = 2 * np.arcsin(np.sqrt(a))

        # Radius of Earth in miles
        r = 3956
        return c * r

    def get_dorms_data(self) -> List[Dict]:
        """Get all dorm locations with pricing"""
        dorms = []
        for _, row in self.dorms_df.iterrows():
            if pd.notna(row['lat']) and pd.notna(row['lng']):
                dorms.append({
                    'name': row['Name'],
                    'lat': row['lat'],
                    'lng': row['lng'],
                    'price_total': row['Price'],
                    'price_monthly': row['MonthlyPriceEstimate'],
                    'category': 'dorm'
                })
        return dorms

    def get_trader_joes_in_boston(self) -> List[Dict]:
        """Get Trader Joe's locations in Massachusetts"""
        tj_ma = self.trader_joes_df[self.trader_joes_df['state_id'] == 'MA'].copy()

        stores = []
        for _, row in tj_ma.iterrows():
            stores.append({
                'name': f"Trader Joe's - {row['city_name']}",
                'lat': row['lat'],
                'lng': row['lng'],
                'address': row['street_address'],
                'city': row['city_name'],
                'category': 'trader_joes'
            })
        return stores

    def get_grocery_stores(self) -> List[Dict]:
        """Get grocery stores from food retail data"""
        # Filter for Massachusetts and grocery stores
        grocery_types = ['Supermarkets and Other Grocery (except Convenience) Stores',
                         'Supermarkets', 'Grocery']

        groceries = self.food_retail_df[
            (self.food_retail_df['state'] == 'MA') &
            (self.food_retail_df['store_type'].isin(grocery_types))
            ].copy()

        stores = []
        for _, row in groceries.iterrows():
            if pd.notna(row['latitude']) and pd.notna(row['longitude']):
                stores.append({
                    'name': row['coname'],
                    'lat': row['latitude'],
                    'lng': row['longitude'],
                    'address': row['staddr'],
                    'city': row['stcity'],
                    'category': 'grocery'
                })
        return stores

    def get_convenience_pharmacy_stores(self) -> List[Dict]:
        """Get convenience stores and pharmacies"""
        conv_pharm_types = ['Convenience Stores', 'Pharmacies and Drug Stores',
                            'Health and Personal Care Stores']

        stores_df = self.food_retail_df[
            (self.food_retail_df['state'] == 'MA') &
            (self.food_retail_df['store_type'].isin(conv_pharm_types))
            ].copy()

        stores = []
        for _, row in stores_df.iterrows():
            if pd.notna(row['latitude']) and pd.notna(row['longitude']):
                stores.append({
                    'name': row['coname'],
                    'lat': row['latitude'],
                    'lng': row['longitude'],
                    'address': row['staddr'],
                    'city': row['stcity'],
                    'category': 'convenience_pharmacy'
                })
        return stores

    def get_mbta_stops(self) -> List[Dict]:
        """Get MBTA T stops"""
        stops = []
        for _, row in self.mbta_nodes_df.iterrows():
            if pd.notna(row['lat']) and pd.notna(row['lng']):
                stops.append({
                    'name': row['station'],
                    'lat': row['lat'],
                    'lng': row['lng'],
                    'line': row['line'],
                    'route': row['route'],
                    'category': 'mbta'
                })
        return stops

    def find_closest_locations(self, lat: float, lng: float,
                               locations: List[Dict], n: int = 3) -> List[Dict]:
        """Find n closest locations to a given point"""
        for loc in locations:
            loc['distance'] = self.haversine_distance(lat, lng, loc['lat'], loc['lng'])

        sorted_locs = sorted(locations, key=lambda x: x['distance'])
        return sorted_locs[:n]

    def analyze_location(self, name: str, lat: float, lng: float) -> Dict:
        """
        Comprehensive analysis of a location's proximity to amenities
        """
        results = {
            'location': {'name': name, 'lat': lat, 'lng': lng},
            'closest_grocery': None,
            'closest_trader_joes': None,
            'closest_convenience_pharmacy': None,
            'closest_mbta': None
        }

        # Get all store types
        groceries = self.get_grocery_stores()
        trader_joes = self.get_trader_joes_in_boston()
        conv_pharm = self.get_convenience_pharmacy_stores()
        mbta = self.get_mbta_stops()

        # Find closest of each type
        if groceries:
            results['closest_grocery'] = self.find_closest_locations(lat, lng, groceries, 3)
        if trader_joes:
            results['closest_trader_joes'] = self.find_closest_locations(lat, lng, trader_joes, 3)
        if conv_pharm:
            results['closest_convenience_pharmacy'] = self.find_closest_locations(lat, lng, conv_pharm, 3)
        if mbta:
            results['closest_mbta'] = self.find_closest_locations(lat, lng, mbta, 3)

        return results

    def analyze_all_dorms(self) -> List[Dict]:
        """Analyze all dorms for proximity to amenities"""
        dorms = self.get_dorms_data()
        analyses = []

        for dorm in dorms:
            analysis = self.analyze_location(dorm['name'], dorm['lat'], dorm['lng'])
            analysis['location']['price_total'] = dorm['price_total']
            analysis['location']['price_monthly'] = dorm['price_monthly']
            analyses.append(analysis)

        return analyses

    def filter_by_radius(self, center_lat: float, center_lng: float,
                         locations: List[Dict], radius_miles: float) -> List[Dict]:
        """Filter locations within a radius"""
        filtered = []
        for loc in locations:
            distance = self.haversine_distance(center_lat, center_lng, loc['lat'], loc['lng'])
            if distance <= radius_miles:
                loc['distance'] = distance
                filtered.append(loc)
        return filtered

    def get_boston_center(self) -> Tuple[float, float]:
        """Get approximate center of Boston for map initialization"""
        # Northeastern University approximate location
        return 42.3398, -71.0892