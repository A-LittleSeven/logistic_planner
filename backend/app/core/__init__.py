"""app.core 兼容性导出层 (向后兼容旧版 from app.core import XXX 调用)。

所有导入均为惰性 (lazy), 避免模块循环初始化问题。
"""

from app.utils.config import settings, get_distance_provider  # noqa: F401
from app.utils.registry import location_registry, routing_registry, clustering_registry, schedule_registry  # noqa: F401



def __getattr__(name: str):
    """懒加载 - 仅在真正使用时才导入重型模块。"""
    if name == "BaseCluster":
        from app.core.cluster.baseCluster import BaseCluster
        return BaseCluster
    if name == "getClusterByConstrainedKmeans":
        from app.core.cluster.get_cluster_by_C_kmeans import getClusterByConstrainedKmeans
        return getClusterByConstrainedKmeans
    if name == "ClusterByDistinct":
        from app.core.cluster.get_cluster_by_district import ClusterByDistinct
        return ClusterByDistinct
    if name == "ClusterByDistrictExtension":
        from app.core.cluster.get_cluster_by_district_extension import ClusterByDistrictExtension
        return ClusterByDistrictExtension
    if name == "LogUtil":
        from app.core.utils.logutils import LogUtil
        return LogUtil
    if name == "RouteOptimizer":
        from app.core.utils.route_optimizer import RouteOptimizer
        return RouteOptimizer
    if name == "TruckSchedule":
        from app.core.optimizer.truck_schedule import TruckSchedule
        return TruckSchedule
    if name == "working_schedule":
        from app.core.optimizer.working_schedule import working_schedule
        return working_schedule
    if name == "balance_schedule":
        from app.core.optimizer.working_schedule import balance_schedule
        return balance_schedule
    if name == "plan_daily_routes_with_or":
        from app.core.optimizer.route_local_replaning_with_or import plan_daily_routes_with_or
        return plan_daily_routes_with_or
    if name == "build_store_node":
        from app.core.utils.datautils import build_store_node
        return build_store_node
    if name in ("haversine", "baidu_driving_distance"):
        from app.utils.distance import haversine, baidu_driving_distance
        return haversine if name == "haversine" else baidu_driving_distance
    raise AttributeError(f"module 'app.core' has no attribute {name!r}")
