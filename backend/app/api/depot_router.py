from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import DBDepot
from app.models.depot import (
    DepotCreate,
    DepotUpdate,
    DepotResponse,
)

router = APIRouter()

@router.get("/", response_model=List[DepotResponse])
def get_depots(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    depots = db.query(DBDepot).offset(skip).limit(limit).all()
    return depots

@router.post("/init_default")
def init_default_depots(db: Session = Depends(get_db)):
    """手动初始化默认示例中心仓数据（仅在数据库为空时生效）"""
    existing_count = db.query(DBDepot).count()
    if existing_count > 0:
        return {"status": "skipped", "message": f"已有 {existing_count} 个中心仓，跳过初始化"}
    samples = [
        DBDepot(
            dc_code="DC_NN_01",
            name="南宁中心仓",
            longitude=108.318344,
            latitude=22.846367,
            address="广西南宁市西乡塘区安吉大道物流产业园A区",
            capacity=50000.0,
            contact_person="张主管",
            contact_phone="13800000001",
            is_default=True,
            is_active=True
        ),
        DBDepot(
            dc_code="DC_LZ_02",
            name="柳州分拨中心",
            longitude=109.402860,
            latitude=24.304495,
            address="广西柳州市柳南区柳邕路物流港",
            capacity=30000.0,
            contact_person="李主管",
            contact_phone="13800000002",
            is_default=False,
            is_active=True
        ),
        DBDepot(
            dc_code="DC_GL_03",
            name="桂林分拔仓",
            longitude=110.299121,
            latitude=25.274215,
            address="广西桂林市象山区环城南路物流枢纽",
            capacity=20000.0,
            contact_person="王主管",
            contact_phone="13800000003",
            is_default=False,
            is_active=True
        )
    ]
    for d in samples:
        db.add(d)
    db.commit()
    return {"status": "success", "message": f"已初始化 {len(samples)} 个默认中心仓"}

@router.post("/", response_model=DepotResponse)
def create_depot(depot: DepotCreate, db: Session = Depends(get_db)):
    existing = db.query(DBDepot).filter(DBDepot.dc_code == depot.dc_code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"DC编码 {depot.dc_code} 已存在")
    
    if depot.is_default:
        db.query(DBDepot).update({DBDepot.is_default: False})
        
    db_depot = DBDepot(**depot.model_dump())
    db.add(db_depot)
    db.commit()
    db.refresh(db_depot)
    return db_depot

@router.put("/{depot_id}", response_model=DepotResponse)
def update_depot(depot_id: int, depot_in: DepotUpdate, db: Session = Depends(get_db)):
    db_depot = db.query(DBDepot).filter(DBDepot.id == depot_id).first()
    if not db_depot:
        raise HTTPException(status_code=404, detail="起点/DC不存在")
    update_data = depot_in.model_dump(exclude_unset=True)
    if "dc_code" in update_data and update_data["dc_code"]:
        existing = db.query(DBDepot).filter(DBDepot.dc_code == update_data["dc_code"], DBDepot.id != depot_id).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"仓库编码 {update_data['dc_code']} 已被其他起点仓库占用")

    if update_data.get("is_default") is True:
        db.query(DBDepot).filter(DBDepot.id != depot_id).update({DBDepot.is_default: False})
        
    for field, val in update_data.items():
        setattr(db_depot, field, val)
    db.commit()
    db.refresh(db_depot)
    return db_depot

@router.post("/{depot_id}/set_default", response_model=DepotResponse)
def set_default_depot(depot_id: int, db: Session = Depends(get_db)):
    db_depot = db.query(DBDepot).filter(DBDepot.id == depot_id).first()
    if not db_depot:
        raise HTTPException(status_code=404, detail="起点/DC不存在")
    
    db.query(DBDepot).update({DBDepot.is_default: False})
    db_depot.is_default = True
    db.commit()
    db.refresh(db_depot)
    return db_depot

@router.delete("/{depot_id}")
def delete_depot(depot_id: int, db: Session = Depends(get_db)):
    db_depot = db.query(DBDepot).filter(DBDepot.id == depot_id).first()
    if not db_depot:
        raise HTTPException(status_code=404, detail="起点/DC不存在")
    db.delete(db_depot)
    db.commit()
    return {"status": "success", "message": f"起点 {depot_id} 已删除"}
