from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.store import StoreNode
from app.utils.distance import haversine


class ClusterNode(BaseModel):
    """
    This class is used to store the cluster information.
    """
    cluster_id: Optional[int] = Field(..., title="区域ID")
    cluster_lon: Optional[float] = Field(..., title="区域经度")
    cluster_lat: Optional[float] = Field(..., title="区域纬度")
    cdist_warehouse: Optional[float] = Field(..., title="区域距离仓库距离")
    # cluster_freq_total: Optional[int] = None
    # cluster_rows_total: Optional[int] = None
    # cluster_store_total: Optional[int] = None
    cluster_store_detailed: Optional[list[StoreNode]] = Field(..., title="区域门店详情")
    cluster_store_avg_distance: Optional[float] = Field(None, title="区域门店平均距离")
    is_planned: Optional[bool] = Field(False, title="区域是否已规划完毕")

    def is_contain_store(self, store: StoreNode) -> bool:
        """
        判断区域是否包含门店
        :param store:
        :return: bool
        """
        return any(s.dept_id == store.dept_id for s in self.cluster_store_detailed)

    def update_store_detail(self, store_list: list[StoreNode]):
        """
        更新区域门店信息
        :return:
        """
        self.cluster_store_detailed = store_list

    def get_cluster_freq_total(self) -> int:
        """
        获取区域门店总频次
        :return: frequency
        """
        frequency = 0
        for store in self.cluster_store_detailed:
            frequency += store.frequency
        return frequency

    def get_cluster_total_loads(self) -> int:
        """
        获取区域门店总载重量
        :return: 区域门店总载重量
        """
        loads = 0
        for store in self.cluster_store_detailed:
            loads += store.avg_loads
        return loads

    def get_cluster_total_stores(self) -> int:
        """
        获取区域门店总数量
        :return: 区域门店总数量
        """
        return len(self.cluster_store_detailed)
    def get_nearest_n_cluster(self, all_clusters: List["ClusterNode"], n: int = 2) -> List["ClusterNode"]:
        """
        获取当前簇地理距离最近 of n 个簇
        :param all_clusters: 所有簇列表
        :param n: 返回最近邻的数量
        :return: 最近的 n 个簇列表
        """
        others = [c for c in all_clusters if c.cluster_id != self.cluster_id]
        return sorted(others, key=lambda x: haversine(
            self.cluster_lon, self.cluster_lat,
            x.cluster_lon, x.cluster_lat
        ))[:n]
