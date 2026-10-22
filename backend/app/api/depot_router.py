"""中心仓/起点主数据管理 API 控制器 (Depot API Router)。

纯粹负责 HTTP 请求接入、参数校验、服务委派与结果响应。
业务逻辑与数据持久化统一由 DepotService 处理。
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.dto.DepotDTO import (
    DepotCreate,
    DepotUpdate,
    DepotResponse,
)
from app.services.master_data_service import DepotService

router = APIRouter()


@router.get("/", response_model=List[DepotResponse], summary="获取中心仓列表")
def get_depots(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return DepotService.get_depots(db, skip=skip, limit=limit)


@router.post("/init_default", summary="手动初始化示例中心仓")
def init_default_depots(db: Session = Depends(get_db)):
    return DepotService.init_default_depots(db)


@router.post("/", response_model=DepotResponse, summary="新增中心仓")
def create_depot(depot: DepotCreate, db: Session = Depends(get_db)):
    return DepotService.create_depot(db, depot)


@router.put("/{depot_id}", response_model=DepotResponse, summary="修改中心仓")
def update_depot(depot_id: int, depot_in: DepotUpdate, db: Session = Depends(get_db)):
    return DepotService.update_depot(db, depot_id, depot_in)


@router.post("/{depot_id}/set_default", response_model=DepotResponse, summary="设为默认中心仓")
def set_default_depot(depot_id: int, db: Session = Depends(get_db)):
    return DepotService.set_default_depot(db, depot_id)


@router.delete("/{depot_id}", summary="删除中心仓")
def delete_depot(depot_id: int, db: Session = Depends(get_db)):
    return DepotService.delete_depot(db, depot_id)
