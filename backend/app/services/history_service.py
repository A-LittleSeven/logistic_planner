"""任务历史与归档服务 (TaskHistoryService)。

负责管理所有求解计算任务 (ROUTING / CLUSTERING / CLUSTER_SCHEDULE) 的运行历史查询、归档详情检索与清空。
"""
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.db.models import DBTaskHistory
from app.models.dto.HistoryDTO import TaskHistoryCreate


class TaskHistoryService:
    """任务历史服务"""

    @classmethod
    def create_history(cls, db: Session, req: TaskHistoryCreate) -> DBTaskHistory:
        """创建任务历史记录"""
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
            updated_at=datetime.now(),
        )
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        return db_task

    @classmethod
    def get_histories(
        cls,
        db: Session,
        task_type: Optional[str] = None,
        save_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[DBTaskHistory]:
        """获取任务历史列表"""
        query = db.query(DBTaskHistory)
        if task_type:
            query = query.filter(DBTaskHistory.task_type == task_type)
        if save_type:
            query = query.filter(DBTaskHistory.save_type == save_type)
        return (
            query.order_by(DBTaskHistory.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @classmethod
    def get_history(cls, db: Session, task_id: str) -> DBTaskHistory:
        """获取指定任务历史记录详情"""
        task = db.query(DBTaskHistory).filter(DBTaskHistory.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        return task

    @classmethod
    def clear_all_history(cls, db: Session) -> Dict[str, str]:
        """清空所有历史记录"""
        db.query(DBTaskHistory).delete()
        db.commit()
        return {"status": "success", "message": "所有历史记录已清空"}

    @classmethod
    def delete_history(cls, db: Session, task_id: str) -> Dict[str, str]:
        """删除指定历史记录"""
        task = db.query(DBTaskHistory).filter(DBTaskHistory.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        db.delete(task)
        db.commit()
        return {"status": "success", "message": f"任务记录 {task_id} 已删除"}
