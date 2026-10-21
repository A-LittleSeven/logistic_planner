"""店群规划与周排班 API 控制器 (Clustering API Router)。

纯粹负责 HTTP 请求接入、参数校验、求解服务委派与结果响应。
所有聚类算法组织、周排班均衡与任务持久化逻辑均下沉至 PlanExecutionService。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import get_distance_provider
from app.utils.distance import DistanceProvider
from app.core import clustering_registry, schedule_registry
from app.core.database import get_db
from app.models.dto.ClusteringDTO import (
    ClusteringSolveRequest,
    ClusteringSolveResponse,
    ScheduleSolveRequest,
    ScheduleSolveResponse,
    SaveClusterPlanRequest,
    SaveScheduleRequest,
)
from app.solvers import clustering_solver  # noqa: F401  导入即注册求解器
from app.solvers import schedule_solver    # noqa: F401  导入即注册排班求解器
from app.services.plan_service import PlanExecutionService

router = APIRouter()


@router.get("/algorithms", summary="获取支持的店群聚类算法列表")
def algorithms():
    return {"algorithms": clustering_registry.list()}


@router.get("/schedule/algorithms", summary="获取支持的排班算法列表")
def schedule_algorithms():
    return {"algorithms": schedule_registry.list()}


@router.post("/solve", response_model=ClusteringSolveResponse, summary="店群聚类规划求解")
def solve(
    req: ClusteringSolveRequest,
    provider: DistanceProvider = Depends(get_distance_provider),
    db: Session = Depends(get_db),
):
    return PlanExecutionService.execute_clustering(db, req, provider)


@router.post("/solve_schedule", response_model=ScheduleSolveResponse, summary="店群多日排班均衡求解")
def solve_schedule(
    req: ScheduleSolveRequest,
    provider: DistanceProvider = Depends(get_distance_provider),
    db: Session = Depends(get_db),
):
    return PlanExecutionService.execute_schedule(db, req, provider)


@router.post("/save_plan", summary="保存店群规划方案至历史存盘")
def save_plan(req: SaveClusterPlanRequest, db: Session = Depends(get_db)):
    return PlanExecutionService.save_clustering_plan(db, req)


@router.post("/save_schedule", summary="保存排班规划方案至历史存盘")
def save_schedule(req: SaveScheduleRequest, db: Session = Depends(get_db)):
    return PlanExecutionService.save_schedule_plan(db, req)
