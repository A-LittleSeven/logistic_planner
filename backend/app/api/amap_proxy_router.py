"""高德地图 JS API 2.0 官方安全代理路由 (_AMapService Proxy)。

根据高德开放平台 JS API 2.0 官方安全规范，前端无需配置明文安全密钥 (securityJsCode)，
统一通过 serviceHost (/_AMapService) 将地图底层 WebAPI 请求反向代理到高德服务端。
后端安全代理自动附加安全密钥 (jscode) 后转发，彻底杜绝前端代码、环境变量与本地存储中的密钥泄露风险。
"""
import logging
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, Request, Response
import httpx
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import DBSystemSetting
from app.utils.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

UPSTREAM_PREFIX_MAP: Dict[str, str] = {
    "v4/map/styles": "https://webapi.amap.com/v4/map/styles",
    "v3/vectormap": "https://fmap01.amap.com/v3/vectormap",
}
DEFAULT_UPSTREAM_BASE = "https://restapi.amap.com"


def get_active_amap_secret(db: Session) -> str:
    """获取当前生效的高德安全密钥（优先读取 SQLite 用户自定义配置，次选环境变量内置配置）。"""
    db_setting = db.query(DBSystemSetting).filter(DBSystemSetting.setting_key == "amap_config").first()
    if db_setting and db_setting.amap_secret and db_setting.amap_secret.strip():
        return db_setting.amap_secret.strip()
    return (settings.amap_security_secret or "").strip()


@router.api_route("/{path:path}", methods=["GET", "POST", "HEAD", "OPTIONS"])
async def proxy_amap_service(path: str, request: Request, db: Session = Depends(get_db)):
    """高德 JS API 服务透明反向代理。"""
    # 1. 匹配目标高德服务地址
    target_url = f"{DEFAULT_UPSTREAM_BASE}/{path}"
    for prefix, target in UPSTREAM_PREFIX_MAP.items():
        if path == prefix or path.startswith(f"{prefix}/"):
            sub = path[len(prefix):]
            target_url = f"{target}{sub}"
            break

    # 2. 注入服务端托管的安全密钥 (jscode)
    query_params = dict(request.query_params)
    secret = get_active_amap_secret(db)
    if secret:
        query_params["jscode"] = secret

    # 3. 准备转发请求头，过滤客户端 hop-by-hop 头
    headers = dict(request.headers)
    for h in ("host", "content-length", "connection", "keep-alive"):
        headers.pop(h, None)

    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.request(
                method=request.method,
                url=target_url,
                params=query_params,
                content=body if body else None,
                headers=headers,
            )
            # 过滤不需要的响应头
            excluded_headers = {
                "content-encoding",
                "content-length",
                "transfer-encoding",
                "connection",
            }
            response_headers = {
                k: v for k, v in resp.headers.items() if k.lower() not in excluded_headers
            }
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=response_headers,
                media_type=resp.headers.get("content-type"),
            )
    except Exception as e:
        logger.error("AMap proxy forward failed for %s: %s", target_url, e)
        raise HTTPException(status_code=502, detail=f"高德地图代理服务异常: {str(e)}")
