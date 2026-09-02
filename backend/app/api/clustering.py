"""店群规划 API。"""
import json
import logging
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core import get_distance_provider
from app.utils.distance import DistanceProvider
from app.core import clustering_registry, schedule_registry
from app.models.clustering import (
    ClusteringSolveRequest,
    ClusteringSolveResponse,
    ScheduleSolveRequest,
    ScheduleSolveResponse,
    SaveClusterPlanRequest,
    SaveScheduleRequest,
)
from app.solvers import clustering_solver  # noqa: F401  导入即注册求解器
from app.solvers import schedule_solver    # noqa: F401  导入即注册排班求解器
from app.core.database import get_db
from app.db.models import DBTaskHistory
from app.utils.serialization import safe_json_dumps

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/algorithms")
def algorithms():
    return {"algorithms": clustering_registry.list()}


@router.get("/schedule/algorithms")
def schedule_algorithms():
    return {"algorithms": schedule_registry.list()}

@router.post("/solve", response_model=ClusteringSolveResponse)
def solve(
    req: ClusteringSolveRequest,
    provider: DistanceProvider = Depends(get_distance_provider),
    db: Session = Depends(get_db),
):
    if not req.points:
        raise HTTPException(status_code=400, detail="请添加门店点")

    try:
        solver = clustering_registry.get(req.algorithm)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    task_id = str(uuid.uuid4())
    try:
        res = solver(req, provider)
        try:
            db_task = DBTaskHistory(
                task_id=task_id,
                task_type="CLUSTERING",
                save_type="AUTO",
                status="SUCCESS",
                parameters=safe_json_dumps(req),
                result=safe_json_dumps(res),
            )
            db.add(db_task)
            db.commit()
        except Exception:
            logger.exception("写入店群规划任务历史记录失败")
        return res
    except Exception as e:
        try:
            db_task = DBTaskHistory(
                task_id=task_id,
                task_type="CLUSTERING",
                save_type="AUTO",
                status="FAILED",
                parameters=safe_json_dumps(req),
                error_message=str(e),
            )
            db.add(db_task)
            db.commit()
        except Exception:
            logger.exception("写入店群规划失败任务历史记录失败")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/solve_schedule", response_model=ScheduleSolveResponse)
def solve_schedule(
    req: ScheduleSolveRequest,
    provider: DistanceProvider = Depends(get_distance_provider),
    db: Session = Depends(get_db),
):
    if not req.points:
        raise HTTPException(status_code=400, detail="请添加门店点")

    algorithm_name = req.algorithm or "cluster_balanced"
    try:
        solver = schedule_registry.get(algorithm_name)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))

    task_id = str(uuid.uuid4())
    try:
        resp_data = solver(req)

        try:
            db_task = DBTaskHistory(
                task_id=task_id,
                task_type="CLUSTER_SCHEDULE",
                save_type="AUTO",
                status="SUCCESS",
                parameters=req.model_dump_json() if hasattr(req, 'model_dump_json') else json.dumps(req.dict()),
                result=json.dumps(resp_data),
            )
            db.add(db_task)
            db.commit()
        except Exception:
            logger.exception("写入排班任务历史记录失败")

        return resp_data

    except Exception as e:
        try:
            db_task = DBTaskHistory(
                task_id=task_id,
                task_type="CLUSTER_SCHEDULE",
                save_type="AUTO",
                status="FAILED",
                parameters=req.model_dump_json() if hasattr(req, 'model_dump_json') else json.dumps(req.dict()),
                error_message=str(e),
            )
            db.add(db_task)
            db.commit()
        except Exception:
            logger.exception("写入排班失败任务历史记录失败")
        raise HTTPException(status_code=400, detail=str(e))




@router.post("/save_plan")
def save_plan(req: SaveClusterPlanRequest, db: Session = Depends(get_db)):
    if not req.points:
        raise HTTPException(status_code=400, detail="门店点列表不能为空")
    
    task_id = str(uuid.uuid4())
    params = {
        "title": req.title,
        "algorithm": req.algorithm,
        "depot_name": req.depot_name,
        "depot_lng": req.depot_lng,
        "depot_lat": req.depot_lat,
        "k": req.k or len(req.clusters),
        "points_count": len(req.points)
    }
    result_data = {
        "title": req.title,
        "algorithm": req.algorithm,
        "depot_name": req.depot_name,
        "depot_lng": req.depot_lng,
        "depot_lat": req.depot_lat,
        "points": req.points,
        "clusters": req.clusters,
        "assignments": req.assignments,
        "k": req.k or len(req.clusters)
    }
    try:
        db_task = DBTaskHistory(
            task_id=task_id,
            task_type="CLUSTERING",
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
            "message": "店群规划方案已成功保存至历史记录！"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")





@router.post("/save_schedule")
def save_schedule(req: SaveScheduleRequest, db: Session = Depends(get_db)):
    task_id = f"SCHED_{int(datetime.now().timestamp() * 1000)}"
    params = {
        "title": req.title,
        "depot_name": req.depot_name,
        "depot_lng": req.depot_lng,
        "depot_lat": req.depot_lat,
        "points_count": len(req.points)
    }
    result_data = {
        "title": req.title,
        "depot_name": req.depot_name,
        "depot_lng": req.depot_lng,
        "depot_lat": req.depot_lat,
        "points": req.points
    }
    try:
        db_task = DBTaskHistory(
            task_id=task_id,
            task_type="CLUSTER_SCHEDULE",
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
            "message": "店群排班方案已成功保存至历史记录！"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


