"""系统管理与高德配置数据传输对象 (System DTO)。

专职负责高德 Web Key 与安全密钥配置存取的 HTTP API 请求/响应模型。
"""
from typing import Optional
from pydantic import BaseModel, Field


class AMapConfigRequest(BaseModel):
    amap_key: str = Field(..., description="高德 Web端 (JS API) Key")
    amap_secret: Optional[str] = Field("", description="高德安全密钥 (Security Secret / jscode)")


class AMapConfigResponse(BaseModel):
    amap_key: str
    amap_secret: str = Field("", description="安全密钥掩码 (安全规范：不向前端回传明文)")
    amap_secret_md5: str
    is_custom: bool
    has_secret: bool = Field(False, description="是否已配置安全密钥")
    message: Optional[str] = None
