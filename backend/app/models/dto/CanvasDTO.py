"""规划画布数据传输对象 (Canvas DTO)。

专职负责规划画布、版本创建、快照载入与详情查询的 HTTP API 请求/响应模型。
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class CanvasPoint(BaseModel):
    """门店/规划点数据模型"""
    model_config = ConfigDict(from_attributes=True, extra="allow")

    id: Optional[Any] = None
    shop_code: Optional[str] = None
    name: Optional[str] = None
    lng: float
    lat: float
    avg_loads: Optional[float] = 10.0
    frequency: Optional[int] = 1
    is_homepot: Optional[int] = 1
    district: Optional[str] = None
    address: Optional[str] = None
    cluster_id: Optional[int] = None
    cluster_name: Optional[str] = None
    schedule_day: Optional[str] = None
    delivery_days_str: Optional[str] = None
    store_is_need_dist: Optional[bool] = True
    available_truck: Optional[str] = None
    service_time: Optional[float] = 0.5


class CanvasCreate(BaseModel):
    name: str = Field(..., description="画布名称，如：南宁仓库2026Q3配送规划")
    dc_code: Optional[str] = Field(None, description="仓库编码")
    depot_name: Optional[str] = Field("中心仓", description="中心仓名称")
    depot_lng: float = Field(..., description="中心仓经度")
    depot_lat: float = Field(..., description="中心仓纬度")
    depot_address: Optional[str] = Field(None, description="中心仓地址")
    description: Optional[str] = Field(None, description="规划描述/备注")
    points: List[CanvasPoint] = Field(default_factory=list, description="初始规划门店池")
    algorithm_configs: Optional[Dict[str, Any]] = Field(default_factory=dict, description="默认算法参数")


class CanvasUpdate(BaseModel):
    name: Optional[str] = None
    dc_code: Optional[str] = None
    depot_name: Optional[str] = None
    depot_lng: Optional[float] = None
    depot_lat: Optional[float] = None
    depot_address: Optional[str] = None
    description: Optional[str] = None
    stage: Optional[str] = None


class CanvasVersionCreate(BaseModel):
    version_name: Optional[str] = None
    change_summary: Optional[str] = None
    stage: Optional[str] = None
    parent_version_id: Optional[int] = None
    snapshot_data: Dict[str, Any] = Field(..., description="版本完整快照数据")


class CanvasVersionSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    canvas_id: str
    version_number: int
    version_name: Optional[str] = None
    change_summary: Optional[str] = None
    parent_version_id: Optional[int] = None
    stage: str
    created_at: Optional[datetime] = None


class CanvasVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    canvas_id: str
    version_number: int
    version_name: Optional[str] = None
    change_summary: Optional[str] = None
    parent_version_id: Optional[int] = None
    stage: str
    snapshot_data: Dict[str, Any]
    created_at: Optional[datetime] = None


class CanvasSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    canvas_id: str
    name: str
    dc_code: Optional[str] = None
    depot_name: Optional[str] = None
    depot_lng: Optional[float] = None
    depot_lat: Optional[float] = None
    depot_address: Optional[str] = None
    description: Optional[str] = None
    stage: str
    current_version_id: Optional[int] = None
    current_version_number: Optional[int] = 1
    version_count: int = 1
    store_count: int = 0
    total_loads: Optional[int] = 0
    route_count: Optional[int] = 0
    total_distance: Optional[float] = 0.0
    cluster_count: Optional[int] = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CanvasDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    canvas_id: str
    name: str
    dc_code: Optional[str] = None
    depot_name: Optional[str] = None
    depot_lng: Optional[float] = None
    depot_lat: Optional[float] = None
    depot_address: Optional[str] = None
    description: Optional[str] = None
    stage: str
    current_version_id: Optional[int] = None
    current_version_number: Optional[int] = 1
    version_count: int = 1
    current_version: Optional[CanvasVersionResponse] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
