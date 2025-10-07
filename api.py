import pandas as pd
import geopandas as gpd


class DashApi:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def get_GDF(self, filepath: str):
        self.data = gpd.read_file(filepath)

    def get_subset(self, columns=None):
        if columns:
            return self.data[columns]
        return self.data

    def get_map(self, *gdfs):
        pass
