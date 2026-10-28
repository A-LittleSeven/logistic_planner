from abc import abstractmethod, ABC
from typing import Optional

from app.utils.distance import DistanceProvider, ensure_provider


class BaseCluster(ABC):
    def __init__(self, provider: Optional[DistanceProvider] = None):
        self.data = None
        self.lng_col = None
        self.lat_col = None
        self.provider: DistanceProvider = ensure_provider(provider)

    @abstractmethod
    def getClusterCenter(self):
        pass

    @abstractmethod
    def fit(self, *arg):
        pass

    def cdist_calc(self, warehouse_lng, warehouse_lat):
        if self.data is None or len(self.data) == 0:
            return self
        wh = (float(warehouse_lng), float(warehouse_lat))
        center_pts = [wh] + list(
            zip(self.data["center_lgt"].astype(float), self.data["center_lat"].astype(float))
        )
        store_pts = [wh] + list(
            zip(self.data[self.lng_col].astype(float), self.data[self.lat_col].astype(float))
        )
        # 仅需仓库→各点 1×n 距离向量：逐点计算，避免构建 (n+1)² 全量矩阵（几千店时 GB 级内存）
        self.data["c_dist"] = [
            self.provider.distance(wh[0], wh[1], lng, lat) for lng, lat in center_pts[1:]
        ]
        self.data["s_dist"] = [
            self.provider.distance(wh[0], wh[1], lng, lat) for lng, lat in store_pts[1:]
        ]
        self.data["dist"] = self.data["c_dist"]
        self.data["store_dist"] = self.data["s_dist"]
        return self
