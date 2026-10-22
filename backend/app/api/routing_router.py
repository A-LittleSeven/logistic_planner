"""物流路线规划 API 控制器 (Routing API Router)。

纯粹负责 HTTP 请求接入、参数校验、求解服务委派与结果响应。
所有算法组织与任务持久化逻辑均下沉至 PlanExecutionService。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import get_distance_provider
from app.utils.distance import DistanceProvider
from app.core import routing_registry
from app.db.database import get_db
from app.models.dto.RoutingDTO import (
    RoutingSolveRequest,
    RoutingSolveResponse,
    GlobalRoutingSolveRequest,
    GlobalRoutingSolveResponse,
    SaveRoutingPlanRequest,
)
from app.solvers import routing_solver  # noqa: F401  导入即注册求解器
from app.services.plan_service import PlanExecutionService

router = APIRouter()


@router.get("/algorithms", summary="获取支持的路线规划算法列表")
def algorithms():
    return {"algorithms": routing_registry.list()}


@router.post("/solve", response_model=RoutingSolveResponse, summary="单日路线规划求解")
def solve(
    req: RoutingSolveRequest,
    provider: DistanceProvider = Depends(get_distance_provider),
    db: Session = Depends(get_db),
):
    return PlanExecutionService.execute_routing(db, req, provider)


@router.post("/solve_global", response_model=GlobalRoutingSolveResponse, summary="全周全局路线规划求解")
def solve_global(
    req: GlobalRoutingSolveRequest,
    provider: DistanceProvider = Depends(get_distance_provider),
    db: Session = Depends(get_db),
):
    return PlanExecutionService.execute_global_routing(db, req, provider)


@router.post("/save_plan", summary="保存路线规划方案至历史存盘")
def save_plan(req: SaveRoutingPlanRequest, db: Session = Depends(get_db)):
    return PlanExecutionService.save_routing_plan(db, req)
