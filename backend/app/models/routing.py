"""物流路线规划 (TSP/VRP) 的请求/响应模型。"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class RoutePoint(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = ""
    shop_code: str = ""
    dept_id: str = ""
    district: str = ""
    lng: float = Field(..., description="经度")
    lat: float = Field(..., description="纬度")
    is_depot: bool = False  # 配送中心; 缺省时取第一个点
    avg_loads: float = 0.0  # 负载箱数，VRP 需要
    frequency: int = 1
    delivery_days_str: str = ""
    is_homepot: Optional[int] = Field(default=None, description="是否本埠(1=本埠, 0=外埠)")


class TruckProfile(BaseModel):
    name: str
    capacity: float
    count: int


class RoutingSolveRequest(BaseModel):
    points: List[RoutePoint]
    trucks: List[TruckProfile] = Field(default_factory=list)
    algorithm: str = "ortools"  # Google OR-Tools CVRP
    options: Dict[str, Any] = Field(default_factory=dict)


class RouteResult(BaseModel):
    truck_name: str
    order: List[int]  # 访问顺序在 points 中的索引
    distance: float
    load: float
    is_homepot: int = 0


class RoutingSolveResponse(BaseModel):
    algorithm: str
    routes: List[RouteResult]
    total_distance: float
    total_stores: int
    points: List[dict]


class GlobalRoutingSolveRequest(BaseModel):
    points: List[RoutePoint]
    trucks: List[TruckProfile] = Field(default_factory=list)
    depot_lng: float = 108.318344
    depot_lat: float = 22.846367


class DailyRoutingResult(BaseModel):
    day: str  # "周一", "周二" 等
    routes: List[RouteResult]
    total_distance: float
    total_stores: int


class GlobalRoutingSolveResponse(BaseModel):
    algorithm: str = "global_optimization"
    daily_results: Dict[str, DailyRoutingResult]
    points: List[dict]  # 门店点信息，包含更新后的 delivery_days_str


class SaveRoutingPlanRequest(BaseModel):
    title: str = "路线规划方案"
    depot_name: Optional[str] = "中心仓"
    depot_lng: Optional[float] = 108.318344
    depot_lat: Optional[float] = 22.846367
    day: Optional[str] = "周一"
    points: List[dict]
    trucks: Optional[List[dict]] = None
    routes: Optional[List[dict]] = None
    total_distance: Optional[float] = 0.0
    total_stores: Optional[int] = 0
