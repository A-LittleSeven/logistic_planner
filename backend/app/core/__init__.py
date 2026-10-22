"""app.core 兼容性导出层 (向后兼容旧版 from app.core import XXX 调用)。

所有导入均为惰性 (lazy), 避免模块循环初始化问题。
"""

from app.utils.config import settings, get_distance_provider  # noqa: F401
from app.utils.registry import location_registry, routing_registry, clustering_registry, schedule_registry  # noqa: F401



def __getattr__(name: str):
    """懒加载 - 仅在真正使用时才导入重型模块。"""
    if name == "BaseCluster":
        from app.core.cluster.base_cluster import BaseCluster
        return BaseCluster
    if name == "ConstrainedKmeansCluster":
        from app.core.cluster.constrained_kmeans_cluster import ConstrainedKmeansCluster
        return ConstrainedKmeansCluster
    if name == "DistrictCluster":
        from app.core.cluster.district_cluster import DistrictCluster
        return DistrictCluster
    if name == "DistrictExtensionCluster":
        from app.core.cluster.district_extension_cluster import DistrictExtensionCluster
        return DistrictExtensionCluster
    if name == "LogUtil":
        from app.utils.logger import LogUtil
        return LogUtil
    if name == "RouteOptimizer":
        from app.core.optimizer.route_optimizer import RouteOptimizer
        return RouteOptimizer
    if name == "TruckSchedule":
        from app.core.optimizer.truck_schedule import TruckSchedule
        return TruckSchedule
    if name == "working_schedule":
        from app.core.optimizer.schedule_balancer import working_schedule
        return working_schedule
    if name == "balance_schedule":
        from app.core.optimizer.schedule_balancer import balance_schedule
        return balance_schedule
    if name == "plan_daily_routes_with_or":
        from app.core.optimizer.route_replanner import plan_daily_routes_with_or
        return plan_daily_routes_with_or
    if name in ("haversine", "baidu_driving_distance"):
        from app.utils.distance import haversine, baidu_driving_distance
        return haversine if name == "haversine" else baidu_driving_distance
    raise AttributeError(f"module 'app.core' has no attribute {name!r}")
