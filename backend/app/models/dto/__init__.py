"""DTO (Data Transfer Object) 数据传输对象层。

专注用于 REST API 请求校验、响应序列化与表单数据交互。
"""
from app.models.dto.StoreDTO import (
    StoreBase,
    StoreCreate,
    StoreUpdate,
    StoreResponse,
    BatchImportRequest,
)
from app.models.dto.VehicleDTO import (
    VehicleBase,
    VehicleCreate,
    VehicleUpdate,
    VehicleResponse,
)
from app.models.dto.CanvasDTO import (
    CanvasPoint,
    CanvasCreate,
    CanvasUpdate,
    CanvasVersionCreate,
    CanvasVersionSummaryResponse,
    CanvasVersionResponse,
    CanvasSummaryResponse,
    CanvasDetailResponse,
)
from app.models.dto.ClusteringDTO import (
    StorePoint,
    ClusteringSolveRequest,
    ClusterResult,
    ClusteringSolveResponse,
    ScheduleSolveRequest,
    ScheduleSolveResponse,
    SaveClusterPlanRequest,
    SaveScheduleRequest,
)
from app.models.dto.RoutingDTO import (
    RoutePoint,
    TruckProfile,
    RoutingSolveRequest,
    RouteResult,
    RoutingSolveResponse,
    SaveRoutingPlanRequest,
)
from app.models.dto.DepotDTO import (
    DepotBase,
    DepotCreate,
    DepotUpdate,
    DepotResponse,
)
from app.models.dto.LocationDTO import (
    DemandPoint,
    LocationSolveRequest,
    LocationCandidate,
    LocationSolveResponse,
)
from app.models.dto.HistoryDTO import (
    TaskHistoryBase,
    TaskHistoryCreate,
    TaskHistoryResponse,
)
from app.models.dto.SystemDTO import (
    AMapConfigRequest,
    AMapConfigResponse,
)

__all__ = [
    # Store
    "StoreBase", "StoreCreate", "StoreUpdate", "StoreResponse", "BatchImportRequest",
    # Vehicle
    "VehicleBase", "VehicleCreate", "VehicleUpdate", "VehicleResponse",
    # Canvas
    "CanvasPoint", "CanvasCreate", "CanvasUpdate", "CanvasVersionCreate",
    "CanvasVersionSummaryResponse", "CanvasVersionResponse", "CanvasSummaryResponse", "CanvasDetailResponse",
    # Clustering
    "StorePoint", "ClusteringSolveRequest", "ClusterResult", "ClusteringSolveResponse",
    "ScheduleSolveRequest", "ScheduleSolveResponse", "SaveClusterPlanRequest", "SaveScheduleRequest",
    # Routing
    "RoutePoint", "TruckProfile", "RoutingSolveRequest", "RouteResult", "RoutingSolveResponse",
    "SaveRoutingPlanRequest",
    # Depot
    "DepotBase", "DepotCreate", "DepotUpdate", "DepotResponse",
    # Location
    "DemandPoint", "LocationSolveRequest", "LocationCandidate", "LocationSolveResponse",
    # History
    "TaskHistoryBase", "TaskHistoryCreate", "TaskHistoryResponse",
    # System
    "AMapConfigRequest", "AMapConfigResponse",
]
