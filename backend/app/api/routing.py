"""物流路线规划 API。"""
import json
import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core import get_distance_provider
from app.utils.distance import DistanceProvider
from app.core import routing_registry
from app.models.routing import (
    RoutingSolveRequest,
    RoutingSolveResponse,
    GlobalRoutingSolveRequest,
    GlobalRoutingSolveResponse,
    SaveRoutingPlanRequest,
)
from app.solvers import routing_solver  # noqa: F401  导入即注册求解器
from app.core.database import get_db
from app.db.models import DBTaskHistory
from app.utils.serialization import safe_json_dumps

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/algorithms")
def algorithms():
    return {"algorithms": routing_registry.list()}


@router.post("/solve", response_model=RoutingSolveResponse)
def solve(
    req: RoutingSolveRequest,
    provider: DistanceProvider = Depends(get_distance_provider),
    db: Session = Depends(get_db),
):
    try:
        solver = routing_registry.get(req.algorithm)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    task_id = str(uuid.uuid4())
    try:
        res = solver(req, provider)
        try:
            db_task = DBTaskHistory(
                task_id=task_id,
                task_type="ROUTING",
                save_type="AUTO",
                status="SUCCESS",
                parameters=safe_json_dumps(req),
                result=safe_json_dumps(res),
            )
            db.add(db_task)
            db.commit()
        except Exception:
            logger.exception("写入路线规划任务历史记录失败")
        return res
    except Exception as e:
        try:
            db_task = DBTaskHistory(
                task_id=task_id,
                task_type="ROUTING",
                save_type="AUTO",
                status="FAILED",
                parameters=safe_json_dumps(req),
                error_message=str(e),
            )
            db.add(db_task)
            db.commit()
        except Exception:
            logger.exception("写入路线规划失败任务历史记录失败")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/solve_global", response_model=GlobalRoutingSolveResponse)
def solve_global(
    req: GlobalRoutingSolveRequest,
    provider: DistanceProvider = Depends(get_distance_provider),
    db: Session = Depends(get_db),
):
    try:
        solver = routing_registry.get("global_optimization")
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    task_id = str(uuid.uuid4())
    try:
        res = solver(req, provider)
        try:
            db_task = DBTaskHistory(
                task_id=task_id,
                task_type="GLOBAL_ROUTING",
                save_type="AUTO",
                status="SUCCESS",
                parameters=safe_json_dumps(req),
                result=safe_json_dumps(res),
            )
            db.add(db_task)
            db.commit()
        except Exception:
            logger.exception("写入全局路线规划任务历史记录失败")
        return res
    except Exception as e:
        try:
            db_task = DBTaskHistory(
                task_id=task_id,
                task_type="GLOBAL_ROUTING",
                save_type="AUTO",
                status="FAILED",
                parameters=safe_json_dumps(req),
                error_message=str(e),
            )
            db.add(db_task)
            db.commit()
        except Exception:
            logger.exception("写入全局路线规划失败任务历史记录失败")
        raise HTTPException(status_code=400, detail=str(e))




@router.post("/save_plan")
def save_plan(req: SaveRoutingPlanRequest, db: Session = Depends(get_db)):
    task_id = f"ROUTE_{int(uuid.uuid4().int % 10000000000)}"
    params = {
        "title": req.title,
        "depot_name": req.depot_name,
        "depot_lng": req.depot_lng,
        "depot_lat": req.depot_lat,
        "day": req.day,
        "points_count": len(req.points)
    }
    result_data = {
        "title": req.title,
        "depot_name": req.depot_name,
        "depot_lng": req.depot_lng,
        "depot_lat": req.depot_lat,
        "day": req.day,
        "points": req.points,
        "trucks": req.trucks or [],
        "routes": req.routes or [],
        "total_distance": req.total_distance or 0.0,
        "total_stores": req.total_stores or len(req.points)
    }
    try:
        db_task = DBTaskHistory(
            task_id=task_id,
            task_type="ROUTING",
            save_type="MANUAL",
            status="SUCCESS",
            parameters=json.dumps(params, ensure_ascii=False),
            result=json.dumps(result_data, ensure_ascii=False)
        )
        db.add(db_task)
        db.commit()
        return {
            "status": "success",
            "task_id": task_id,
            "message": "路线规划方案已成功保存至历史记录！"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")

