"""车型与车辆主数据传输对象 (Vehicle DTO)。

专职负责车型主数据 CRUD 的 HTTP 请求入参校验与响应序列化。
"""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class VehicleBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vehicle_code: str = Field(..., description="车型编码")
    name: str = Field(..., description="车型名称")
    capacity_weight: float = Field(..., description="载重 (吨/箱)")
    capacity_volume: float = Field(..., description="体积 (m³)")
    cost_per_km: float = Field(..., description="每公里运输成本")
    max_distance: Optional[float] = Field(500.0, description="最大单次行驶里程(km)")
    available_count: Optional[int] = Field(10, description="可用车辆数量")
    is_active: Optional[bool] = Field(True, description="是否启用")


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    vehicle_code: Optional[str] = None
    name: Optional[str] = None
    capacity_weight: Optional[float] = None
    capacity_volume: Optional[float] = None
    cost_per_km: Optional[float] = None
    max_distance: Optional[float] = None
    available_count: Optional[int] = None
    is_active: Optional[bool] = None


class VehicleResponse(VehicleBase):
    id: int
