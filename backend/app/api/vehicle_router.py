"""车型运力主数据管理 API 控制器 (Vehicle API Router)。

纯粹负责 HTTP 请求接入、参数校验、服务委派与结果响应。
业务逻辑与数据持久化统一由 VehicleService 处理。
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.vehicle import (
    VehicleCreate,
    VehicleUpdate,
    VehicleResponse,
)
from app.services.master_data_service import VehicleService

router = APIRouter()


@router.post("/", response_model=VehicleResponse, summary="新增车型")
def create_vehicle(vehicle: VehicleCreate, db: Session = Depends(get_db)):
    return VehicleService.create_vehicle(db, vehicle)


@router.get("/", response_model=List[VehicleResponse], summary="获取车型列表")
def get_vehicles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return VehicleService.get_vehicles(db, skip=skip, limit=limit)


@router.put("/{vehicle_id}", response_model=VehicleResponse, summary="修改车型信息")
def update_vehicle(vehicle_id: int, vehicle_in: VehicleUpdate, db: Session = Depends(get_db)):
    return VehicleService.update_vehicle(db, vehicle_id, vehicle_in)


@router.delete("/{vehicle_id}", summary="删除车型")
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    return VehicleService.delete_vehicle(db, vehicle_id)
