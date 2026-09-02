import hashlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import DBSystemSetting
from app.models.system import (
    AMapConfigRequest,
    AMapConfigResponse,
)
from app.utils.config import settings

router = APIRouter()


@router.get("/amap-config", response_model=AMapConfigResponse)
def get_amap_config(db: Session = Depends(get_db)):
    """获取当前生效的高德地图 Key 与安全密钥配置（从 SQLite 优先读取）"""
    db_setting = db.query(DBSystemSetting).filter(DBSystemSetting.setting_key == "amap_config").first()
    
    if db_setting and db_setting.amap_key and db_setting.amap_secret:
        return AMapConfigResponse(
            amap_key=db_setting.amap_key,
            amap_secret=db_setting.amap_secret,
            amap_secret_md5=db_setting.amap_secret_md5 or hashlib.md5(db_setting.amap_secret.encode("utf-8")).hexdigest(),
            is_custom=True,
            message="从 SQLite 数据库加载用户自定义高德配置"
        )
    
    # 未配置自定义密钥时，不向前端暴露系统默认密钥
    return AMapConfigResponse(
        amap_key="",
        amap_secret="",
        amap_secret_md5="",
        is_custom=False,
        message="使用系统内置默认高德配置"
    )


@router.post("/amap-config", response_model=AMapConfigResponse)
def save_amap_config(payload: AMapConfigRequest, db: Session = Depends(get_db)):
    """保存用户的高德地图 Key 与安全密钥到 SQLite 数据库。若两项均为空则清除自定义配置使用默认密钥。"""
    key = payload.amap_key.strip()
    secret = payload.amap_secret.strip()
    
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
            message="已清除自定义配置，恢复使用系统内置默认高德配置"
        )
    
    if not key or not secret:
        raise HTTPException(status_code=400, detail="如需自定义配置，Key 与安全密钥均不能为空")
    
    # 对安全密钥进行 MD5 加密
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
        amap_secret=db_setting.amap_secret,
        amap_secret_md5=db_setting.amap_secret_md5,
        is_custom=True,
        message="高德地图 Key 与安全密钥已成功加密并保存到 SQLite 数据库"
    )


@router.post("/amap-config/reset")
def reset_amap_config(db: Session = Depends(get_db)):
    """恢复为系统默认配置并清除 SQLite 中的自定义配置"""
    db_setting = db.query(DBSystemSetting).filter(DBSystemSetting.setting_key == "amap_config").first()
    if db_setting:
        db.delete(db_setting)
        db.commit()
    return {"status": "success", "message": "已恢复系统默认高德配置"}
