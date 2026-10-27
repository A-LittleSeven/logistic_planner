import hashlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import DBSystemSetting
from app.models.dto.SystemDTO import (
    AMapConfigRequest,
    AMapConfigResponse,
)
from app.utils.config import settings

router = APIRouter()


@router.get("/amap-config", response_model=AMapConfigResponse)
def get_amap_config(db: Session = Depends(get_db)):
    """获取当前生效的高德地图 Key 与安全密钥配置（从 SQLite 优先读取，密钥敏感信息不向前端明文回显）"""
    db_setting = db.query(DBSystemSetting).filter(DBSystemSetting.setting_key == "amap_config").first()
    
    if db_setting and db_setting.amap_key and db_setting.amap_secret:
        return AMapConfigResponse(
            amap_key=db_setting.amap_key,
            amap_secret="",  # 安全规范：不向前端回传明文安全密钥，由后端安全代理托管
            amap_secret_md5=db_setting.amap_secret_md5 or hashlib.md5(db_setting.amap_secret.encode("utf-8")).hexdigest(),
            is_custom=True,
            has_secret=True,
            message="从 SQLite 数据库加载用户自定义高德配置"
        )
    
    # 未配置自定义密钥时，不向前端暴露系统默认配置细节
    has_default_secret = bool(settings.amap_security_secret and settings.amap_security_secret.strip())
    return AMapConfigResponse(
        amap_key="",
        amap_secret="",
        amap_secret_md5="",
        is_custom=False,
        has_secret=has_default_secret,
        message="使用系统内置默认高德配置"
    )


@router.post("/amap-config", response_model=AMapConfigResponse)
def save_amap_config(payload: AMapConfigRequest, db: Session = Depends(get_db)):
    """保存用户的高德地图 Key 与安全密钥到 SQLite 数据库。若两项均为空则清除自定义配置使用默认密钥。"""
    key = (payload.amap_key or "").strip()
    secret = (payload.amap_secret or "").strip()
    
    db_setting = db.query(DBSystemSetting).filter(DBSystemSetting.setting_key == "amap_config").first()
    
    # 若均为空，清除自定义配置
    if not key and not secret:
        if db_setting:
            db.delete(db_setting)
            db.commit()
        return AMapConfigResponse(
            amap_key="",
            amap_secret="",
            amap_secret_md5="",
            is_custom=False,
            has_secret=bool(settings.amap_security_secret and settings.amap_security_secret.strip()),
            message="已清除自定义配置，恢复使用系统内置默认高德配置"
        )
    
    # 如果仅提供了 key 且 secret 为空：若已有配置则保留原有 secret，否则报错
    if key and not secret:
        if db_setting and db_setting.amap_secret:
            secret = db_setting.amap_secret
        else:
            raise HTTPException(status_code=400, detail="首次配置自定义密钥时，Key 与安全密钥均不能为空")
    elif not key and secret:
        raise HTTPException(status_code=400, detail="Key 不能为空")
    
    # 对安全密钥进行 MD5 摘要计算
    secret_md5 = hashlib.md5(secret.encode("utf-8")).hexdigest()
    
    if not db_setting:
        db_setting = DBSystemSetting(
            setting_key="amap_config",
            amap_key=key,
            amap_secret=secret,
            amap_secret_md5=secret_md5,
            is_active=True
        )
        db.add(db_setting)
    else:
        db_setting.amap_key = key
        db_setting.amap_secret = secret
        db_setting.amap_secret_md5 = secret_md5
        db_setting.is_active = True
        
    db.commit()
    db.refresh(db_setting)
    
    return AMapConfigResponse(
        amap_key=db_setting.amap_key,
        amap_secret="",  # 安全规范：响应中严禁明文回显安全密钥
        amap_secret_md5=db_setting.amap_secret_md5,
        is_custom=True,
        has_secret=True,
        message="高德地图配置已成功保存至后端 SQLite"
    )


@router.post("/amap-config/reset")
def reset_amap_config(db: Session = Depends(get_db)):
    """恢复为系统默认配置并清除 SQLite 中的自定义配置"""
    db_setting = db.query(DBSystemSetting).filter(DBSystemSetting.setting_key == "amap_config").first()
    if db_setting:
        db.delete(db_setting)
        db.commit()
    return {"status": "success", "message": "已恢复系统默认高德配置"}
