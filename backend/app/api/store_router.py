"""门店主数据管理 API 控制器 (Store API Router)。

纯粹负责 HTTP 请求接入、参数校验、服务委派与结果响应。
数据查询、CRUD 与 CSV 播种等业务逻辑统一由 StoreService 处理。
"""
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.dto.StoreDTO import (
    StoreCreate,
    StoreUpdate,
    StoreResponse,
    BatchImportRequest,
)
from app.services.master_data_service import StoreService

router = APIRouter()


@router.get("/", response_model=List[StoreResponse], summary="查询门店列表")
def get_stores(
    district: Optional[str] = None,
    warehouse: Optional[str] = None,
    cluster_id: Optional[int] = None,
    is_homepot: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db),
):
    return StoreService.get_stores(
        db=db,
        district=district,
        warehouse=warehouse,
        cluster_id=cluster_id,
        is_homepot=is_homepot,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.post("/init_default", summary="手动初始化示例门店数据")
def init_default_stores(db: Session = Depends(get_db)):
    count = StoreService.init_default_stores_from_csv(db)
    return {"status": "success", "message": f"已成功初始化默认门店数据，共导入/刷新 {count} 家门店"}


@router.post("/", response_model=StoreResponse, summary="新增门店")
def create_store(store: StoreCreate, db: Session = Depends(get_db)):
    return StoreService.create_store(db, store)


@router.post("/batch", summary="批量导入门店")
def batch_import_stores(req: BatchImportRequest, db: Session = Depends(get_db)):
    return StoreService.batch_import_stores(db, req)


@router.put("/{store_id}", response_model=StoreResponse, summary="修改门店信息")
def update_store(store_id: int, store_in: StoreUpdate, db: Session = Depends(get_db)):
    return StoreService.update_store(db, store_id, store_in)


@router.delete("/clear/all", summary="清空所有门店数据")
def clear_all_stores(db: Session = Depends(get_db)):
    return StoreService.clear_all_stores(db)


@router.delete("/{store_id}", summary="删除门店")
def delete_store(store_id: int, db: Session = Depends(get_db)):
    return StoreService.delete_store(db, store_id)
