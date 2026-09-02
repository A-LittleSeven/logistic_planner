from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import DBVehicle
from app.models.vehicle import (
    VehicleCreate,
    VehicleUpdate,
    VehicleResponse,
)

router = APIRouter()

@router.post("/", response_model=VehicleResponse)
def create_vehicle(vehicle: VehicleCreate, db: Session = Depends(get_db)):
    existing = db.query(DBVehicle).filter(DBVehicle.vehicle_code == vehicle.vehicle_code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"车型编号 {vehicle.vehicle_code} 已存在")
    db_vehicle = DBVehicle(**vehicle.model_dump())
    db.add(db_vehicle)
    db.commit()
    db.refresh(db_vehicle)
    return db_vehicle

@router.get("/", response_model=List[VehicleResponse])
def get_vehicles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    vehicles = db.query(DBVehicle).offset(skip).limit(limit).all()
    if not vehicles and skip == 0:
        samples = [
            DBVehicle(vehicle_code="V420", name="新能源4.2米箱式货车", capacity_weight=200.0, capacity_volume=18.0, cost_per_km=3.5, max_distance=400.0, available_count=8),
            DBVehicle(vehicle_code="V680", name="重型6.8米货车", capacity_weight=450.0, capacity_volume=35.0, cost_per_km=5.2, max_distance=600.0, available_count=4),
            DBVehicle(vehicle_code="V960", name="干线9.6米货车", capacity_weight=800.0, capacity_volume=55.0, cost_per_km=7.8, max_distance=800.0, available_count=2),
        ]
        for v in samples:
            db.add(v)
        db.commit()
        vehicles = db.query(DBVehicle).offset(skip).limit(limit).all()
    return vehicles

@router.put("/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle(vehicle_id: int, vehicle_in: VehicleUpdate, db: Session = Depends(get_db)):
    db_vehicle = db.query(DBVehicle).filter(DBVehicle.id == vehicle_id).first()
    if not db_vehicle:
        raise HTTPException(status_code=404, detail="车型不存在")
    update_data = vehicle_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(db_vehicle, field, val)
    db.commit()
    db.refresh(db_vehicle)
    return db_vehicle

@router.delete("/{vehicle_id}")
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    db_vehicle = db.query(DBVehicle).filter(DBVehicle.id == vehicle_id).first()
    if not db_vehicle:
        raise HTTPException(status_code=404, detail="车型不存在")
    db.delete(db_vehicle)
    db.commit()
    return {"status": "success", "message": f"车型 {vehicle_id} 已删除"}
