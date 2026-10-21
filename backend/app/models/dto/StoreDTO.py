"""门店管理数据传输对象 (Store DTO)。

专职负责 HTTP API 请求入参校验、响应序列化与表单数据交互。
"""
from typing import Optional, List, Union
from pydantic import BaseModel, Field, ConfigDict


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
