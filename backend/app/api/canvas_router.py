from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.canvas_schema import (
    CanvasCreate,
    CanvasUpdate,
    CanvasVersionCreate,
    CanvasSummaryResponse,
    CanvasDetailResponse,
    CanvasVersionResponse,
)
from app.services.canvas_service import CanvasService

router = APIRouter()


@router.post("", response_model=CanvasDetailResponse, summary="创建新规划画布")
def create_canvas(req: CanvasCreate, db: Session = Depends(get_db)):
    return CanvasService.create_canvas(db, req)


@router.get("", response_model=List[CanvasSummaryResponse], summary="获取画布列表")
def list_canvases(
    keyword: Optional[str] = None,
    dc_code: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return CanvasService.list_canvases(db, keyword=keyword, dc_code=dc_code)


@router.get("/{canvas_id}", response_model=CanvasDetailResponse, summary="获取画布详情及当前工作快照")
def get_canvas_detail(canvas_id: str, db: Session = Depends(get_db)):
    return CanvasService.get_canvas_detail(db, canvas_id)


@router.put("/{canvas_id}", response_model=CanvasSummaryResponse, summary="修改画布基础信息")
def update_canvas(canvas_id: str, req: CanvasUpdate, db: Session = Depends(get_db)):
    return CanvasService.update_canvas(db, canvas_id, req)


@router.delete("/{canvas_id}", summary="删除画布")
def delete_canvas(canvas_id: str, db: Session = Depends(get_db)):
    return CanvasService.delete_canvas(db, canvas_id)


@router.get("/{canvas_id}/versions", response_model=List[CanvasVersionResponse], summary="获取画布历史版本列表")
def list_canvas_versions(canvas_id: str, db: Session = Depends(get_db)):
    return CanvasService.list_canvas_versions(db, canvas_id)


@router.get("/{canvas_id}/versions/{version_id}", response_model=CanvasVersionResponse, summary="获取指定版本快照")
def get_canvas_version(canvas_id: str, version_id: int, db: Session = Depends(get_db)):
    return CanvasService.get_canvas_version(db, canvas_id, version_id)


@router.post("/{canvas_id}/versions", response_model=CanvasVersionResponse, summary="在画布中基于上一版本保存新版本 (增量演进)")
def create_canvas_version(canvas_id: str, req: CanvasVersionCreate, db: Session = Depends(get_db)):
    return CanvasService.create_canvas_version(db, canvas_id, req)


@router.post("/{canvas_id}/rollback/{version_id}", response_model=CanvasDetailResponse, summary="回滚/切换当前工作版本至历史指定版本")
def rollback_canvas_version(canvas_id: str, version_id: int, db: Session = Depends(get_db)):
    return CanvasService.rollback_canvas_version(db, canvas_id, version_id)


@router.post("/{canvas_id}/clone", response_model=CanvasDetailResponse, summary="克隆画布 (创建规划分支)")
def clone_canvas(canvas_id: str, new_name: Optional[str] = None, db: Session = Depends(get_db)):
    return CanvasService.clone_canvas(db, canvas_id, new_name=new_name)
