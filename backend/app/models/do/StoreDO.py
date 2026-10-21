"""门店领域模型对象 (Store DO)。

专职用于启发式排班、聚类与装载运筹算法的运行时实体。
维护动态频次衰减、空间距离计算与候选店检索等领域行为。
"""
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.utils.distance import haversine


class StoreNode(BaseModel):
    """启发式排班与聚类算法中的门店节点领域模型。"""
    model_config = ConfigDict(extra="allow")

    # 门店簇中心信息
    cluster_center_id: Optional[int] = Field(None, title="聚类中心id")
    cluster_center_lon: Optional[float] = Field(None, title="区域中心经度")
    cluster_center_lat: Optional[float] = Field(None, title="区域中心纬度")
    cdist_warehouse: Optional[float] = Field(None, title="聚类中心距离仓库距离")

    # 仓库相关信息
    dc_code: Optional[str] = Field(None, title="仓库编码")
    warehouse_lon: Optional[float] = Field(None, title="仓库经度")
    warehouse_lat: Optional[float] = Field(None, title="仓库纬度")

    # 门店基础信息
    point_idx: Optional[int] = Field(None, title="原始输入索引")
    dept_id: Optional[str] = Field(None, title="部门ID")
    shop_code: Optional[str] = Field(None, title="门店编号")
    district: Optional[str] = Field(None, title="行政区划")
    district_sub: Optional[str] = Field(None, title="区县子级")
    city_name: Optional[str] = Field(None, title="城市名称")
    is_homepot: Optional[int] = Field(None, title="是否本埠门店")
    store_is_need_dist: Optional[bool] = Field(None, title="门店是否需要配送")
    warzone: Optional[str] = Field(None, title="战区")
    name: Optional[str] = Field(None, title="名称")
    store_lon: Optional[float] = Field(None, title="门店经度")
    store_lat: Optional[float] = Field(None, title="门店纬度")
    sdist_warehouse: Optional[float] = Field(None, title="门店距离仓库距离")
    frequency: Optional[int] = Field(None, title="配送频次")
    store_freq_remains: Optional[int] = Field(None, title="门店剩余频次")
    avg_loads: Optional[float] = Field(None, title="门店箱数")
    demand: Optional[float] = Field(None, title="需求量")
    available_truck: Optional[List[str]] = Field(default_factory=list, title="可配送的车辆列表")
    service_time: Optional[float] = Field(0.5, title="门店卸货服务时间(小时)")
    address: Optional[str] = Field(None, title="详细地址")

    @property
    def lng(self) -> Optional[float]:
        return self.store_lon

    @property
    def lat(self) -> Optional[float]:
        return self.store_lat

    @property
    def longitude(self) -> Optional[float]:
        return self.store_lon

    @property
    def latitude(self) -> Optional[float]:
        return self.store_lat

    @property
    def load(self) -> float:
        return float(self.avg_loads or self.demand or 0.0)

    def update_freq_remains(self):
        """更新剩余频次"""
        if self.store_freq_remains is not None:
            self.store_freq_remains -= 1

    def calc_haversine_distance(self, other_store: "StoreNode") -> float:
        """计算两个门店之间的地理距离 (km)"""
        if self.store_lon is None or self.store_lat is None or other_store.store_lon is None or other_store.store_lat is None:
            return 0.0
        return haversine(self.store_lon, self.store_lat, other_store.store_lon, other_store.store_lat)

    def find_nearest_store(self, store_list: List["StoreNode"]) -> "StoreNode":
        """寻找最近的门店"""
        if not store_list:
            raise ValueError("store_list 不能为空")
        return min(store_list, key=lambda x: self.calc_haversine_distance(x))

    def find_nearest_freq_store(self, store_list: List["StoreNode"], frequency: int = 1) -> "StoreNode":
        """寻找最近的指定频次门店"""
        if not store_list:
            raise ValueError("store_list 不能为空")
        return min(
            store_list,
            key=lambda x: self.calc_haversine_distance(x) if x.frequency == frequency else float("inf")
        )
