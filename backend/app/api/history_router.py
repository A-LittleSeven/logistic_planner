from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import DBTaskHistory
from app.models.history import (
    TaskHistoryCreate,
    TaskHistoryResponse,
)

router = APIRouter()

@router.post("/", response_model=TaskHistoryResponse)
def create_history(req: TaskHistoryCreate, db: Session = Depends(get_db)):
    task_id = req.task_id or f"TASK_{int(datetime.now().timestamp() * 1000)}"
    db_task = DBTaskHistory(
        task_id=task_id,
        task_type=req.task_type,
        save_type=req.save_type or "AUTO",
        status=req.status,
        parameters=req.parameters,
        result=req.result,
        error_message=req.error_message,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.get("/", response_model=List[TaskHistoryResponse])
def get_histories(
    task_type: Optional[str] = None,
    save_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(DBTaskHistory)
    if task_type:
        query = query.filter(DBTaskHistory.task_type == task_type)
    if save_type:
        query = query.filter(DBTaskHistory.save_type == save_type)
    return query.order_by(DBTaskHistory.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/{task_id}", response_model=TaskHistoryResponse)
def get_history(task_id: str, db: Session = Depends(get_db)):
    task = db.query(DBTaskHistory).filter(DBTaskHistory.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task

@router.delete("/clear/all")
def clear_all_history(db: Session = Depends(get_db)):
    db.query(DBTaskHistory).delete()
    db.commit()
    return {"status": "success", "message": "所有历史记录已清空"}

@router.delete("/{task_id}")
def delete_history(task_id: str, db: Session = Depends(get_db)):
    task = db.query(DBTaskHistory).filter(DBTaskHistory.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    db.delete(task)
    db.commit()
    return {"status": "success", "message": f"任务记录 {task_id} 已删除"}
