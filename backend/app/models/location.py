"""物流选址 (设施选址) 的请求/响应模型。"""
from pydantic import BaseModel, Field


class DemandPoint(BaseModel):
    name: str = ""
    lng: float
    lat: float
    weight: float = Field(default=1.0, gt=0, description="需求量/权重")


class LocationSolveRequest(BaseModel):
    points: list[DemandPoint]
    algorithm: str = "center_of_gravity"  # 拓展: p_median, center_of_gravity_iter ...
    options: dict = Field(default_factory=dict)


class LocationSolveResponse(BaseModel):
    algorithm: str
    optimal: dict  # {lng, lat}
    total_weighted_distance: float
    points: list[dict]
