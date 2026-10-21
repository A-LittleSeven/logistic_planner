"""Models 模块统一入口。

提供 DTO (数据传输对象) 与 DO (算法领域模型) 双层架构支持：
- dto: app.models.dto (专注 HTTP 请求入参、响应序列化与 Schema 校验)
- do:  app.models.do  (专注运筹算法、装载调度与路径规划的运行时实体)
"""
from app.models import dto, do

# 便捷导出核心 DO 模型
from app.models.do.StoreDO import StoreNode
from app.models.do.ClusterDO import ClusterNode
from app.models.do.VehicleDO import (
    VehicleNode,
    BaseTruck,
    TruckIdAllocator,
    Truck420,
    Truck270,
    Truck960,
    Express,
    create_vehicle_class,
    load_fleet_classes,
)

# 便捷导出核心 DTO 模型
from app.models.dto.StoreDTO import (
    StoreBase, StoreCreate, StoreUpdate, StoreResponse, BatchImportRequest
)
from app.models.dto.VehicleDTO import (
    VehicleBase, VehicleCreate, VehicleUpdate, VehicleResponse
)
from app.models.dto.CanvasDTO import (
    CanvasCreate, CanvasUpdate, CanvasVersionCreate, CanvasDetailResponse, CanvasSummaryResponse
)

__all__ = [
    "dto",
    "do",
    # DO
    "StoreNode",
    "ClusterNode",
    "VehicleNode",
    "BaseTruck",
    "TruckIdAllocator",
    "Truck420",
    "Truck270",
    "Truck960",
    "Express",
    "create_vehicle_class",
    "load_fleet_classes",
    # DTO
    "StoreBase",
    "StoreCreate",
    "StoreUpdate",
    "StoreResponse",
    "BatchImportRequest",
    "VehicleBase",
    "VehicleCreate",
    "VehicleUpdate",
    "VehicleResponse",
    "CanvasCreate",
    "CanvasUpdate",
    "CanvasVersionCreate",
    "CanvasDetailResponse",
    "CanvasSummaryResponse",
]
