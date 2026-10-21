"""店群/片区领域模型对象 (Cluster DO)。

专职用于聚类拓扑、店群邻域借店与多簇排班调度的运行时实体。
维护簇中心坐标、归属门店集合、全簇总载重计算及簇间邻近距离检索。
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.do.StoreDO import StoreNode
from app.utils.distance import haversine


class ClusterNode(BaseModel):
    """区域店群节点领域模型。"""
    cluster_id: Optional[int] = Field(..., title="区域ID")
    cluster_lon: Optional[float] = Field(..., title="区域经度")
    cluster_lat: Optional[float] = Field(..., title="区域纬度")
    cdist_warehouse: Optional[float] = Field(..., title="区域距离仓库距离")
    cluster_store_detailed: Optional[List[StoreNode]] = Field(..., title="区域门店详情")
    cluster_store_avg_distance: Optional[float] = Field(None, title="区域门店平均距离")
    is_planned: Optional[bool] = Field(False, title="区域是否已规划完毕")

    def is_contain_store(self, store: StoreNode) -> bool:
        """判断区域是否包含门店"""
        return any(s.dept_id == store.dept_id for s in (self.cluster_store_detailed or []))

    def update_store_detail(self, store_list: List[StoreNode]):
        """更新区域门店信息"""
        self.cluster_store_detailed = store_list

    def get_cluster_freq_total(self) -> int:
        """获取区域门店总频次"""
        if not self.cluster_store_detailed:
            return 0
        return sum(store.frequency or 0 for store in self.cluster_store_detailed)

    def get_cluster_total_loads(self) -> float:
        """获取区域门店总载重量"""
        if not self.cluster_store_detailed:
            return 0.0
        return sum(store.avg_loads or 0.0 for store in self.cluster_store_detailed)

    def get_cluster_total_stores(self) -> int:
        """获取区域门店总数量"""
        return len(self.cluster_store_detailed or [])

    def get_nearest_n_cluster(self, all_clusters: List["ClusterNode"], n: int = 2) -> List["ClusterNode"]:
        """获取当前簇地理距离最近的 n 个邻居簇"""
        others = [c for c in all_clusters if c.cluster_id != self.cluster_id]
        return sorted(others, key=lambda x: haversine(
            self.cluster_lon, self.cluster_lat,
            x.cluster_lon, x.cluster_lat
        ))[:n]
