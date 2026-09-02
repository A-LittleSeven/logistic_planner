from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class DepotBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dc_code: str = Field(..., description="DC编码/仓库代码")
    name: str = Field(..., description="DC名称/中心仓名称")
    longitude: float = Field(..., description="经度")
    latitude: float = Field(..., description="纬度")
    address: Optional[str] = Field(None, description="详细地址")
    capacity: Optional[float] = Field(None, description="吞吐容量(吨/箱)")
    contact_person: Optional[str] = Field(None, description="联系人")
    contact_phone: Optional[str] = Field(None, description="联系电话")
    is_default: Optional[bool] = Field(False, description="是否默认中心仓")
    is_active: Optional[bool] = Field(True, description="启用状态")


class DepotCreate(DepotBase):
    pass


class DepotUpdate(BaseModel):
    dc_code: Optional[str] = None
    name: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    address: Optional[str] = None
    capacity: Optional[float] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class DepotResponse(DepotBase):
    id: int
