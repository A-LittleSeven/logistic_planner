"""店群规划与排班数据传输对象 (Clustering DTO)。

专职负责店群划分、全周排班均衡与方案存盘的 HTTP API 请求/响应模型。
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator


class StorePoint(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = ""
    shop_code: str = ""
    dept_id: str = ""
    district: str = ""
    lng: float = Field(..., description="经度")
    lat: float = Field(..., description="纬度")
    avg_loads: float = 1.0
    frequency: int = 1
    is_homepot: Optional[int] = Field(default=0, description="是否本埠(1=本埠, 0=外埠)；未提供时默认外埠 0")
    delivery_days_str: str = ""

    @field_validator("is_homepot", mode="before")
    @classmethod
    def _default_homepot(cls, v):
        """空值/空串归一化为外埠 0，默认填充统一收敛在 DTO 层"""
        return 0 if (v is None or v == "") else v


class ClusteringSolveRequest(BaseModel):
    points: List[StorePoint]
    k: Optional[int] = Field(default=6, description="店群数量")
    algorithm: str = "kmeans"  # 拓展: kmeans, district, district_extension ...
    depot_lng: float = Field(default=108.318344, description="仓库/中心仓经度")
    depot_lat: float = Field(default=22.846367, description="仓库/中心仓纬度")
    options: Dict[str, Any] = Field(default_factory=dict)
    depot: Optional[Dict[str, Any]] = None

    @model_validator(mode="before")
    @classmethod
    def extract_depot(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "depot" in data and isinstance(data["depot"], dict):
                depot_dict = data["depot"]
                if "lng" in depot_dict and "depot_lng" not in data:
                    data["depot_lng"] = float(depot_dict["lng"])
                if "lat" in depot_dict and "depot_lat" not in data:
                    data["depot_lat"] = float(depot_dict["lat"])
            if "k" not in data or data.get("k") is None or data.get("k") == 0:
                data["k"] = 6
        return data


class ClusterResult(BaseModel):
    cluster_id: int
    center: Dict[str, float]  # {"lng": float, "lat": float}
    size: int
    point_indices: List[int]
    cdist_warehouse: float = 0.0  # 簇中心距离仓库距离 (km)


class ClusteringSolveResponse(BaseModel):
    algorithm: str
    k: int
    clusters: List[ClusterResult]
    assignments: List[int]  # 每个点所属簇 id
    points: List[dict]  # 每个点附带 sdist_warehouse 和 cdist_warehouse


class ScheduleSolveRequest(BaseModel):
    points: List[StorePoint]
    depot_lng: float = 108.318344
    depot_lat: float = 22.846367
    algorithm: str = "cluster_balanced"  # 拓展注册: cluster_balanced, frequency_balanced, etc.
    options: Dict[str, Any] = Field(default_factory=dict)
    depot: Optional[Dict[str, Any]] = None

    @model_validator(mode="before")
    @classmethod
    def extract_depot_schedule(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "depot" in data and isinstance(data["depot"], dict):
                depot_dict = data["depot"]
                if "lng" in depot_dict and "depot_lng" not in data:
                    data["depot_lng"] = float(depot_dict["lng"])
                if "lat" in depot_dict and "depot_lat" not in data:
                    data["depot_lat"] = float(depot_dict["lat"])
        return data


class ScheduleSolveResponse(BaseModel):
    points: List[dict]


class SaveClusterPlanRequest(BaseModel):
    title: Optional[str] = Field("店群规划调整方案", description="方案标题")
    algorithm: Optional[str] = Field("kmeans", description="规划算法或手动调整")
    depot_name: Optional[str] = Field("中心仓库", description="中心仓名称")
    depot_lng: Optional[float] = Field(None, description="中心仓经度")
    depot_lat: Optional[float] = Field(None, description="中心仓纬度")
    points: List[dict] = Field(..., description="门店点列表")
    clusters: Optional[List[dict]] = Field(default_factory=list, description="店群列表")
    assignments: Optional[List[int]] = Field(default_factory=list, description="分配列表")
    k: Optional[int] = Field(None, description="店群数量")


class SaveScheduleRequest(BaseModel):
    title: str = "店群排班方案"
    depot_name: Optional[str] = "中心仓"
    depot_lng: Optional[float] = 108.318344
    depot_lat: Optional[float] = 22.846367
    points: List[dict]
