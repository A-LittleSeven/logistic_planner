import pandas as pd

from app.core.cluster.baseCluster import BaseCluster


class ClusterByDistinct(BaseCluster):
    def __init__(self, data: pd.DataFrame,
                 distinct_col='district',
                 lng_col='longitude',
                 lat_col='latitude'):
        super().__init__()
        self.data = data.copy()
        self.distinct_col = distinct_col
        self.lng_col = lng_col
        self.lat_col = lat_col
        self.cluster_center = None

    def getClusterCenter(self):
        data_sub = self.data[[self.distinct_col, self.lng_col, self.lat_col]]
        df_center = data_sub.groupby(self.distinct_col, as_index=False).agg({
            self.lng_col: "mean",
            self.lat_col: "mean"
        })
        df_center = df_center.rename(columns={
            self.lng_col: "center_lgt",
            self.lat_col: "center_lat"
        })
        df_center["cluster_id"] = range(len(df_center))
        return df_center

    def fit(self, warehouse_lng=None, warehouse_lat=None):
        self.cluster_center = self.getClusterCenter()
        self.data = pd.merge(self.data, self.cluster_center, on=self.distinct_col, how='left')
        if warehouse_lng is not None and warehouse_lat is not None:
            self.cdist_calc(warehouse_lng, warehouse_lat)
        return self
