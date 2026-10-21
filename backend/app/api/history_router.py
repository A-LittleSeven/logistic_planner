"""任务运行历史管理 API 控制器 (History API Router)。

纯粹负责 HTTP 请求接入、参数校验、服务委派与结果响应。
业务逻辑与数据持久化统一由 TaskHistoryService 处理。
"""
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.history import (
    TaskHistoryCreate,
    TaskHistoryResponse,
)
from app.services.history_service import TaskHistoryService

router = APIRouter()


@router.post("/", response_model=TaskHistoryResponse, summary="新增任务历史")
def create_history(req: TaskHistoryCreate, db: Session = Depends(get_db)):
    return TaskHistoryService.create_history(db, req)


@router.get("/", response_model=List[TaskHistoryResponse], summary="查询任务历史列表")
def get_histories(
    task_type: Optional[str] = None,
    save_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return TaskHistoryService.get_histories(
        db, task_type=task_type, save_type=save_type, skip=skip, limit=limit
    )


@router.get("/{task_id}", response_model=TaskHistoryResponse, summary="查询任务历史详情")
def get_history(task_id: str, db: Session = Depends(get_db)):
    return TaskHistoryService.get_history(db, task_id)


@router.delete("/clear/all", summary="清空所有任务历史")
def clear_all_history(db: Session = Depends(get_db)):
    return TaskHistoryService.clear_all_history(db)


@router.delete("/{task_id}", summary="删除指定任务历史")
def delete_history(task_id: str, db: Session = Depends(get_db)):
    return TaskHistoryService.delete_history(db, task_id)
