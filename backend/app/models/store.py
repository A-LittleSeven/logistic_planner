from typing import Optional, List, Union
from pydantic import BaseModel, Field, ConfigDict

from app.utils.distance import haversine


# ==========================================
# 1. 传输层 DTO / Schemas (API 请求与响应校验)
# ==========================================

class StoreBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    shop_code: str = Field(..., description="门店编号")
    name: str = Field(..., description="门店名称")
    dept_id: Optional[str] = Field(None, description="部门ID")
    district: Optional[str] = Field(None, description="行政区划")
    warzone: Optional[str] = Field(None, description="战区")
    longitude: float = Field(..., description="经度")
    latitude: float = Field(..., description="纬度")
    avg_loads: Optional[float] = Field(0.0, description="日均箱数/需求量")
    frequency: Optional[int] = Field(1, description="配送频次")
    store_freq_remains: Optional[int] = Field(None, description="剩余频次")
    is_homepot: Optional[int] = Field(1, description="是否本埠(1=本埠, 0=外埠)")
    store_is_need_dist: Optional[bool] = Field(True, description="是否需要配送")
    service_time: Optional[float] = Field(0.5, description="卸货服务时间(小时)")
    available_truck: Optional[Union[str, List[str]]] = Field(None, description="可配送车型")
    sdist_warehouse: Optional[float] = Field(None, description="距仓距离(km)")

    # 仓库相关信息
    dc_code: Optional[str] = Field(None, description="仓库编码")
    warehouse_name: Optional[str] = Field(None, description="仓库名称")
    warehouse_lon: Optional[float] = Field(None, description="仓库经度")
    warehouse_lat: Optional[float] = Field(None, description="仓库纬度")

    # 门店簇中心信息
    cluster_center_id: Optional[int] = Field(None, description="聚类中心id")
    cluster_center_lon: Optional[float] = Field(None, description="区域中心经度")
    cluster_center_lat: Optional[float] = Field(None, description="区域中心纬度")
    cdist_warehouse: Optional[float] = Field(None, description="聚类中心距离仓库距离")

    address: Optional[str] = Field(None, description="详细地址")
    is_active: Optional[bool] = Field(True, description="启用状态")


class StoreCreate(StoreBase):
    pass


class StoreUpdate(BaseModel):
    shop_code: Optional[str] = None
    name: Optional[str] = None
    dept_id: Optional[str] = None
    district: Optional[str] = None
    warzone: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    avg_loads: Optional[float] = None
    frequency: Optional[int] = None
    store_freq_remains: Optional[int] = None
    is_homepot: Optional[int] = None
    store_is_need_dist: Optional[bool] = None
    service_time: Optional[float] = None
    available_truck: Optional[Union[str, List[str]]] = None
    sdist_warehouse: Optional[float] = None
    dc_code: Optional[str] = None
    warehouse_name: Optional[str] = None
    warehouse_lon: Optional[float] = None
    warehouse_lat: Optional[float] = None
    cluster_center_id: Optional[int] = None
    cluster_center_lon: Optional[float] = None
    cluster_center_lat: Optional[float] = None
    cdist_warehouse: Optional[float] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class StoreResponse(StoreBase):
    id: int


class BatchImportRequest(BaseModel):
    stores: List[StoreCreate]
    mode: Optional[str] = Field("overwrite", description="overwrite 或 append")


# ==========================================
# 2. 领域/算法层模型 (Domain / Solver Node)
# ==========================================

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
    available_truck: Optional[list[str]] = Field(default_factory=list, title="可配送的车辆列表")
    service_time: Optional[float] = Field(0.5, title="门店卸货服务时间(小时)")
    address: Optional[str] = Field(None, title="详细地址")

    @property
    def lng(self) -> Optional[float]:
        return self.store_lon

    @property
    def lat(self) -> Optional[float]:
        return self.store_lat

    def update_freq_remains(self):
        """更新剩余频次"""
        if self.store_freq_remains is not None:
            self.store_freq_remains -= 1

    def calc_haversine_distance(self, other_store: "StoreNode") -> float:
        """计算两个门店之间的地理距离 (km)"""
        if self.store_lon is None or self.store_lat is None or other_store.store_lon is None or other_store.store_lat is None:
            return 0.0
        return haversine(self.store_lon, self.store_lat, other_store.store_lon, other_store.store_lat)

    def find_nearest_store(self, store_list: list["StoreNode"]) -> "StoreNode":
        """寻找最近的门店"""
        if not store_list:
            raise ValueError("store_list 不能为空")
        return min(store_list, key=lambda x: self.calc_haversine_distance(x))

    def find_nearest_freq_store(self, store_list: list["StoreNode"], frequency: int = 1) -> "StoreNode":
        """寻找最近的指定频次门店"""
        if not store_list:
            raise ValueError("store_list 不能为空")
        return min(
            store_list,
            key=lambda x: self.calc_haversine_distance(x) if x.frequency == frequency else float("inf")
        )
