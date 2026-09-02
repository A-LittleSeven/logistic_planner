from abc import abstractmethod, ABC

from app.utils.distance import haversine


class BaseCluster(ABC):
    def __init__(self):
        self.data = None
        self.lng_col = None
        self.lat_col = None

    @abstractmethod
    def getClusterCenter(self):
        pass

    @abstractmethod
    def fit(self, *arg):
        pass

    def cdist_calc(self, warehouse_lng, warehouse_lat):
        self.data["c_dist"] = self.data.apply(
            lambda row: haversine(row["center_lgt"], row["center_lat"], warehouse_lng, warehouse_lat),
            axis=1,
        )
        self.data["s_dist"] = self.data.apply(
            lambda row: haversine(row[self.lng_col], row[self.lat_col], warehouse_lng, warehouse_lat),
            axis=1,
        )
        self.data["dist"] = self.data["c_dist"]
        self.data["store_dist"] = self.data["s_dist"]
        return self
