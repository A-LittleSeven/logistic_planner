"""物流选址数据传输对象 (Location DTO)。

专职负责设施选址 (重心法、P-中值法等) 的 HTTP API 请求/响应模型。
"""
from typing import List, Dict, Any
from pydantic import BaseModel, Field


class DemandPoint(BaseModel):
    name: str = ""
    lng: float
    lat: float
    weight: float = Field(default=1.0, gt=0, description="需求量/权重")


class LocationSolveRequest(BaseModel):
    points: List[DemandPoint]
    algorithm: str = "center_of_gravity"  # 拓展: p_median, center_of_gravity_iter ...
    options: Dict[str, Any] = Field(default_factory=dict)


class LocationCandidate(BaseModel):
    name: str = ""
    lng: float
    lat: float


class LocationSolveResponse(BaseModel):
    algorithm: str
    optimal: dict  # {lng, lat}
    total_weighted_distance: float
    points: List[dict]
