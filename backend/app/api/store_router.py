import os
import csv
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import DBStore
from app.models.store import (
    StoreBase,
    StoreCreate,
    StoreUpdate,
    StoreResponse,
    BatchImportRequest,
)

router = APIRouter()

def init_default_stores_from_csv(db: Session):
    """如果数据库为空，尝试从根目录的 store_info_guangxi.csv 初始化基础门店数据"""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    csv_path = os.path.join(base_dir, "store_info_guangxi.csv")
    if not os.path.exists(csv_path):
        return
    
    try:
        # Try reading gbk/utf-8
        encodings = ['gbk', 'utf-8-sig', 'utf-8']
        rows = None
        for enc in encodings:
            try:
                with open(csv_path, 'r', encoding=enc) as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                break
            except Exception:
                continue
        
        if rows:
            for r in rows:
                try:
                    store = DBStore(
                        shop_code=str(r.get("shop_code") or r.get("dept_id") or "").strip(),
                        name=str(r.get("shop_name") or r.get("name") or "").strip(),
                        dept_id=str(r.get("dept_id") or "").strip(),
                        district=str(r.get("district") or "").strip(),
                        warzone=str(r.get("warzone") or "").strip(),
                        longitude=float(r.get("longitude") or r.get("lng") or 0.0),
                        latitude=float(r.get("latitude") or r.get("lat") or 0.0),
                        avg_loads=float(r.get("avg_loads") or 0.0),
                        frequency=int(float(r.get("frequency") or 1)),
                        is_homepot=int(r.get("is_homepot") or 1),
                        service_time=float(r.get("dist_time") or 40) / 60.0 if r.get("dist_time") else 0.65,
                        address=f"{r.get('city_name', '')}{r.get('district_sub', '')}",
                        available_truck=str(r.get("dis_way") or ""),
                        is_active=True
                    )
                    if store.shop_code and store.longitude and store.latitude:
                        db.add(store)
                except Exception:
                    continue
            db.commit()
    except Exception as e:
        print(f"Failed to auto seed from csv: {e}")


@router.get("/", response_model=List[StoreResponse])
def get_stores(
    district: Optional[str] = None,
    warehouse: Optional[str] = None,
    cluster_id: Optional[int] = None,
    is_homepot: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    query = db.query(DBStore)
    if district:
        query = query.filter(DBStore.district == district)
    if warehouse:
        query = query.filter((DBStore.warehouse_name == warehouse) | (DBStore.dc_code == warehouse))
    if cluster_id is not None:
        query = query.filter(DBStore.cluster_center_id == cluster_id)
    if is_homepot is not None:
        query = query.filter(DBStore.is_homepot == is_homepot)
    if search:
        s = f"%{search}%"
        query = query.filter(
            (DBStore.name.ilike(s)) | 
            (DBStore.shop_code.ilike(s)) | 
            (DBStore.district.ilike(s)) |
            (DBStore.warehouse_name.ilike(s)) |
            (DBStore.dc_code.ilike(s))
        )
        
    stores = query.offset(skip).limit(limit).all()
    return stores


@router.post("/init_default")
def init_default_stores(db: Session = Depends(get_db)):
    """手动重新导入默认示例门店数据"""
    init_default_stores_from_csv(db)
    count = db.query(DBStore).count()
    return {"status": "success", "message": f"已成功初始化默认门店数据，当前共 {count} 家门店"}


@router.post("/", response_model=StoreResponse)
def create_store(store: StoreCreate, db: Session = Depends(get_db)):
    existing = db.query(DBStore).filter(DBStore.shop_code == store.shop_code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"门店编号 {store.shop_code} 已存在")
    db_store = DBStore(**store.model_dump())
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    return db_store


@router.post("/batch")
def batch_import_stores(req: BatchImportRequest, db: Session = Depends(get_db)):
    if not req.stores:
        raise HTTPException(status_code=400, detail="导入门店列表不能为空")
    
    if req.mode == "overwrite":
        db.query(DBStore).delete()
        db.commit()
        
    inserted = 0
    updated = 0
    errors = []
    
    for item in req.stores:
        try:
            existing = db.query(DBStore).filter(DBStore.shop_code == item.shop_code).first()
            if existing:
                for k, v in item.model_dump(exclude_unset=True).items():
                    setattr(existing, k, v)
                updated += 1
            else:
                db_store = DBStore(**item.model_dump())
                db.add(db_store)
                inserted += 1
        except Exception as e:
            errors.append(f"{item.shop_code}: {str(e)}")
            
    db.commit()
    return {
        "status": "success",
        "inserted": inserted,
        "updated": updated,
        "total": len(req.stores),
        "errors": errors
    }


@router.put("/{store_id}", response_model=StoreResponse)
def update_store(store_id: int, store_in: StoreUpdate, db: Session = Depends(get_db)):
    db_store = db.query(DBStore).filter(DBStore.id == store_id).first()
    if not db_store:
        raise HTTPException(status_code=404, detail="门店不存在")
    update_data = store_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(db_store, field, val)
    db.commit()
    db.refresh(db_store)
    return db_store


@router.delete("/clear/all")
def clear_all_stores(db: Session = Depends(get_db)):
    """清空所有门店数据"""
    db.query(DBStore).delete()
    db.commit()
    return {"status": "success", "message": "所有门店数据已清空"}


@router.delete("/{store_id}")
def delete_store(store_id: int, db: Session = Depends(get_db)):
    db_store = db.query(DBStore).filter(DBStore.id == store_id).first()
    if not db_store:
        raise HTTPException(status_code=404, detail="门店不存在")
    db.delete(db_store)
    db.commit()
    return {"status": "success", "message": f"门店 {store_id} 已删除"}

