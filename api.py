import pandas as pd


class DashApi:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def get_subset(self, columns=None):
        pass
