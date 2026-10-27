"""规划与排班算法业务编排服务 (PlanExecutionService)。

负责组织调用各领域纯算法求解器 (Solvers)，并负责自动持久化任务运行日志与历史方案 (DBTaskHistory)。
解耦 API 路由层与持久化事务逻辑，支持同步 API 调用及离线/后台批处理。
"""
import json
import uuid
from typing import Any, Dict
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core import routing_registry, clustering_registry, schedule_registry
from app.utils.distance import DistanceProvider
from app.db.models import DBTaskHistory
from app.utils.serialization import safe_json_dumps
from app.utils.logger import LogUtil
from app.models.dto.RoutingDTO import (
    RoutingSolveRequest,
    GlobalRoutingSolveRequest,
    SaveRoutingPlanRequest,
)
from app.models.dto.ClusteringDTO import (
    ClusteringSolveRequest,
    ScheduleSolveRequest,
    SaveClusterPlanRequest,
    SaveScheduleRequest,
)

logger = LogUtil.get_logger(__name__)


class PlanExecutionService:
    """规划与排班求解编排服务"""

    @staticmethod
    def _record_task_history(
        db: Session,
        task_id: str,
        task_type: str,
        save_type: str,
        status: str,
        parameters: str,
        result: str = None,
        error_message: str = None,
    ):
        """记录任务执行历史（静默记录，不破坏主流程）"""
        try:
            db_task = DBTaskHistory(
                task_id=task_id,
                task_type=task_type,
                save_type=save_type,
                status=status,
                parameters=parameters,
                result=result,
                error_message=error_message,
            )
            db.add(db_task)
            db.commit()
        except Exception:
            logger.exception(f"写入任务历史记录失败: task_id={task_id}, type={task_type}")

    @classmethod
    def execute_routing(
        cls, db: Session, req: RoutingSolveRequest, provider: DistanceProvider
    ) -> Dict[str, Any]:
        """执行单作业日/局部路线规划求解并归档历史"""
        try:
            solver = routing_registry.get(req.algorithm)
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e))

        task_id = str(uuid.uuid4())
        param_json = safe_json_dumps(req)
        try:
            res = solver(req, provider)
            cls._record_task_history(
                db,
                task_id=task_id,
                task_type="ROUTING",
                save_type="AUTO",
                status="SUCCESS",
                parameters=param_json,
                result=safe_json_dumps(res),
            )
            return res
        except Exception as e:
            cls._record_task_history(
                db,
                task_id=task_id,
                task_type="ROUTING",
                save_type="AUTO",
                status="FAILED",
                parameters=param_json,
                error_message=str(e),
            )
            raise HTTPException(status_code=400, detail=str(e))

    @classmethod
    def execute_global_routing(
        cls, db: Session, req: GlobalRoutingSolveRequest, provider: DistanceProvider
    ) -> Dict[str, Any]:
        """执行全周多日全局路线规划求解并归档历史"""
        try:
            solver = routing_registry.get("global_optimization")
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e))

        task_id = str(uuid.uuid4())
        param_json = safe_json_dumps(req)
        try:
            res = solver(req, provider)
            cls._record_task_history(
                db,
                task_id=task_id,
                task_type="GLOBAL_ROUTING",
                save_type="AUTO",
                status="SUCCESS",
                parameters=param_json,
                result=safe_json_dumps(res),
            )
            return res
        except Exception as e:
            cls._record_task_history(
                db,
                task_id=task_id,
                task_type="GLOBAL_ROUTING",
                save_type="AUTO",
                status="FAILED",
                parameters=param_json,
                error_message=str(e),
            )
            raise HTTPException(status_code=400, detail=str(e))

    @classmethod
    def save_routing_plan(cls, db: Session, req: SaveRoutingPlanRequest) -> Dict[str, Any]:
        """手动保存路线规划方案至历史存盘"""
        task_id = f"ROUTE_{int(uuid.uuid4().int % 10000000000)}"
        params = {
            "title": req.title,
            "depot_name": req.depot_name,
            "depot_lng": req.depot_lng,
            "depot_lat": req.depot_lat,
            "day": req.day,
            "points_count": len(req.points),
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
            "total_stores": req.total_stores or len(req.points),
        }
        try:
            db_task = DBTaskHistory(
                task_id=task_id,
                task_type="ROUTING",
                save_type="MANUAL",
                status="SUCCESS",
                parameters=json.dumps(params, ensure_ascii=False),
                result=json.dumps(result_data, ensure_ascii=False),
            )
            db.add(db_task)
            db.commit()
            return {
                "status": "success",
                "task_id": task_id,
                "message": "路线规划方案已成功保存至历史记录！",
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")

    @classmethod
    def execute_clustering(
        cls, db: Session, req: ClusteringSolveRequest, provider: DistanceProvider
    ) -> Dict[str, Any]:
        """执行店群聚类规划求解并归档历史"""
        if not req.points:
            raise HTTPException(status_code=400, detail="请添加门店点")

        try:
            solver = clustering_registry.get(req.algorithm)
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e))

        task_id = str(uuid.uuid4())
        param_json = safe_json_dumps(req)
        try:
            res = solver(req, provider)
            cls._record_task_history(
                db,
                task_id=task_id,
                task_type="CLUSTERING",
                save_type="AUTO",
                status="SUCCESS",
                parameters=param_json,
                result=safe_json_dumps(res),
            )
            return res
        except Exception as e:
            cls._record_task_history(
                db,
                task_id=task_id,
                task_type="CLUSTERING",
                save_type="AUTO",
                status="FAILED",
                parameters=param_json,
                error_message=str(e),
            )
            raise HTTPException(status_code=400, detail=str(e))

    @classmethod
    def execute_schedule(
        cls, db: Session, req: ScheduleSolveRequest, provider: DistanceProvider = None
    ) -> Dict[str, Any]:
        """执行全周排班均衡求解并归档历史"""
        if not req.points:
            raise HTTPException(status_code=400, detail="请添加门店点")

        algorithm_name = req.algorithm or "cluster_balanced"
        try:
            solver = schedule_registry.get(algorithm_name)
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e))

        task_id = str(uuid.uuid4())
        param_json = safe_json_dumps(req)

        # 尝试从数据库加载启用的车型主数据，动态打通排班运力池
        try:
            from app.db.models import DBVehicle
            from app.models.do.VehicleDO import load_fleet_classes
            active_vehicles = db.query(DBVehicle).filter(DBVehicle.is_active == True).all()
            if active_vehicles and "_fleet_classes" not in req.options:
                req.options["_fleet_classes"] = load_fleet_classes(active_vehicles)
        except Exception as e:
            logger.warning(f"加载数据库动态车型失败，自动降级为内置静态车型: {e}")
        try:
            resp_data = solver(req)
            cls._record_task_history(
                db,
                task_id=task_id,
                task_type="CLUSTER_SCHEDULE",
                save_type="AUTO",
                status="SUCCESS",
                parameters=param_json,
                result=json.dumps(resp_data),
            )
            return resp_data
        except Exception as e:
            cls._record_task_history(
                db,
                task_id=task_id,
                task_type="CLUSTER_SCHEDULE",
                save_type="AUTO",
                status="FAILED",
                parameters=param_json,
                error_message=str(e),
            )
            raise HTTPException(status_code=400, detail=str(e))

    @classmethod
    def save_clustering_plan(cls, db: Session, req: SaveClusterPlanRequest) -> Dict[str, Any]:
        """手动保存店群规划方案至历史记录"""
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
            "points_count": len(req.points),
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
            "k": req.k or len(req.clusters),
        }
        try:
            db_task = DBTaskHistory(
                task_id=task_id,
                task_type="CLUSTERING",
                save_type="MANUAL",
                status="SUCCESS",
                parameters=json.dumps(params, ensure_ascii=False),
                result=json.dumps(result_data, ensure_ascii=False),
            )
            db.add(db_task)
            db.commit()
            return {
                "status": "success",
                "task_id": task_id,
                "message": "店群规划方案已成功保存至历史记录！",
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")

    @classmethod
    def save_schedule_plan(cls, db: Session, req: SaveScheduleRequest) -> Dict[str, Any]:
        """手动保存排班规划方案至历史记录"""
        if not req.points:
            raise HTTPException(status_code=400, detail="门店点列表不能为空")

        task_id = str(uuid.uuid4())
        params = {
            "title": req.title,
            "depot_name": req.depot_name,
            "depot_lng": req.depot_lng,
            "depot_lat": req.depot_lat,
            "points_count": len(req.points),
            "work_days": req.work_days or 6,
        }
        result_data = {
            "title": req.title,
            "depot_name": req.depot_name,
            "depot_lng": req.depot_lng,
            "depot_lat": req.depot_lat,
            "points": req.points,
            "daily_stats": req.daily_stats,
            "work_days": req.work_days or 6,
            "total_stores": len(req.points),
        }
        try:
            db_task = DBTaskHistory(
                task_id=task_id,
                task_type="CLUSTER_SCHEDULE",
                save_type="MANUAL",
                status="SUCCESS",
                parameters=json.dumps(params, ensure_ascii=False),
                result=json.dumps(result_data, ensure_ascii=False),
            )
            db.add(db_task)
            db.commit()
            return {
                "status": "success",
                "task_id": task_id,
                "message": "排班方案已成功保存至历史记录！",
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")
