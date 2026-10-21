"""店群排班求解器实现与注册。

支持通过 schedule_registry 灵活拓展多种排班方法 (例如: 店群负载均衡排班、频次平滑排班等)。
"""
from typing import Dict, Any, List
from app.models.dto.ClusteringDTO import ScheduleSolveRequest
from app.models.do.ClusterDO import ClusterNode
from app.models.do.StoreDO import StoreNode
from app.core.optimizer.truck_schedule import TruckSchedule
from app.core.optimizer.route_optimizer import RouteOptimizer
from app.core.optimizer.working_schedule import working_schedule, balance_schedule
from app.utils.distance import haversine
from app.utils.registry import schedule_registry




from app.models.converters import to_store_node


def solve_cluster_balanced_schedule(req: ScheduleSolveRequest) -> Dict[str, Any]:
    """基于店群拓扑与车型容量约束的排班均衡算法 (默认推荐算法)"""
    depot_lng = float(req.depot_lng)
    depot_lat = float(req.depot_lat)

    # 1 & 2. 构造 StoreNode 数据列表
    stores_list = []
    high_freq_stores = []
    total_store = []
    for idx, p in enumerate(req.points):
        store = to_store_node(p, default_idx=idx, depot_lng=depot_lng, depot_lat=depot_lat)
        total_store.append(store)
        if store.frequency > 2:
            high_freq_stores.append(store)
        else:
            stores_list.append(store)

    # 3. 构造 ClusterNode 数据列表
    cluster_ids = sorted(list(set(store.cluster_center_id for store in total_store if store.cluster_center_id is not None)))
    cluster_list = []
    for cid in cluster_ids:
        tmp_list = [store for store in stores_list if store.cluster_center_id == cid]
        if not tmp_list:
            continue
        cluster = ClusterNode(
            cluster_id=cid,
            cluster_lon=tmp_list[0].cluster_center_lon,
            cluster_lat=tmp_list[0].cluster_center_lat,
            cdist_warehouse=tmp_list[0].cdist_warehouse,
            cluster_store_detailed=tmp_list,
        )
        cluster_list.append(cluster)

    # 4. 执行排班策略与运力调度
    options = req.options or {}
    max_rate = float(options.get("max_truck_capacity_rate", 0.96))
    n_neighbor = int(options.get("search_n_neighbor", 1))
    simple_thres = int(options.get("simple_mode_thres", 0))
    detour_thres = float(options.get("detour_thres", 500.0))
    dist_thres = float(options.get("dist_thres", 0.9))
    one_way_dist_max = int(options.get("one_way_dist_max", 40))
    work_days = int(options.get("work_days", 6))
    fleet_classes = options.get("_fleet_classes") or options.get("truck_classes")

    # 上下文隔离的 ID 重置（并发安全）
    from app.models.do.VehicleDO import TruckIdAllocator
    TruckIdAllocator.reset(1)

    sorted_cluster = sorted(cluster_list, key=lambda x: x.cdist_warehouse)
    scheduler = TruckSchedule(
        max_truck_capacity_rate=max_rate,
        search_n_neighbor=n_neighbor,
        simple_mode_thres=simple_thres,
        dist_thres=dist_thres,
        one_way_dist_max=one_way_dist_max,
        detour_thres=detour_thres,
        truck_classes=fleet_classes,
    )

    if sorted_cluster:
        scheduler.schedule(sorted_cluster)
        RouteOptimizer.local_route_optimize(scheduler.plan_trucks)

        # 5. 分配至各作业日并进行多日平滑均衡
        schedule, loads = working_schedule(scheduler.plan_trucks, work_days=work_days)
        schedule, loads = balance_schedule(schedule, loads, scheduler.plan_trucks, work_days=work_days)
    else:
        schedule = {d: [] for d in range(work_days)}

    # 6. 提取每个门店被分配的排班日 (0..work_days-1)
    store_scheduled_days = {}
    for day, t_ids in schedule.items():
        for tid in t_ids:
            truck = next((t for t in scheduler.plan_trucks if t.truck_id == tid), None)
            if truck:
                for store in truck.truck_trace:
                    s_idx = store.point_idx
                    if s_idx is None:
                        try:
                            s_idx = int(store.shop_code)
                        except (ValueError, TypeError):
                            continue
                    if s_idx not in store_scheduled_days:
                        store_scheduled_days[s_idx] = set()
                    store_scheduled_days[s_idx].add(day)

    # 7. 针对高频门店 (frequency > 2) 进行跨日步长均衡分配
    daily_loads = {d: 0.0 for d in range(work_days)}
    for day, t_ids in schedule.items():
        for tid in t_ids:
            truck = next((t for t in scheduler.plan_trucks if t.truck_id == tid), None)
            if truck:
                daily_loads[day] += (truck.truck_current_load or 0.0)

    for store in high_freq_stores:
        freq = store.frequency
        if freq > 0:
            best_days = []
            min_load_sum = float('inf')
            for candidate_start in range(work_days):
                num_step2 = min(freq, max(1, work_days // 2))
                candidate_days = []
                for j in range(num_step2):
                    candidate_days.append((candidate_start + 2 * j) % work_days)

                remains_needed = freq - num_step2
                if remains_needed > 0:
                    unselected_days = [d for d in range(work_days) if d not in candidate_days]
                    unselected_days.sort(key=lambda d: daily_loads.get(d, 0.0))
                    candidate_days.extend(unselected_days[:remains_needed])

                load_sum = sum(daily_loads.get(d, 0.0) for d in candidate_days)
                if load_sum < min_load_sum:
                    min_load_sum = load_sum
                    best_days = candidate_days
            
            for d in best_days:
                daily_loads[d] += (store.avg_loads or 0.0)
            
            s_idx = store.point_idx
            if s_idx is None:
                try:
                    s_idx = int(store.shop_code)
                except (ValueError, TypeError):
                    continue
            store_scheduled_days[s_idx] = set(best_days)

    # 8. 映射为规范中文作业日字符串
    day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    enriched_points = []
    for idx, p in enumerate(req.points):
        scheduled_indices = sorted(list(store_scheduled_days.get(idx, [])))
        days_str = ",".join(day_names[d] for d in scheduled_indices if d < len(day_names))
        
        # 兜底保障
        if not days_str:
            freq = int(p.model_extra.get("frequency") if hasattr(p, 'model_extra') and p.model_extra else (getattr(p, 'frequency', 1) or 1))
            if freq >= 6:
                days_str = "周一,周二,周三,周四,周五,周六"
            elif freq >= 3:
                days_str = "周一,周三,周五"
            elif freq == 2:
                days_str = "周一,周四"
            else:
                days_str = "周一"

        pt_dict = p.model_dump()
        pt_dict["delivery_days_str"] = days_str
        pt_dict["schedule_day"] = days_str
        pt_dict["delivery_day"] = days_str.split(',')[0].strip()
        enriched_points.append(pt_dict)

    # 统计每日门店数与日均总装载
    daily_stats = {d: {"count": 0, "load": 0.0} for d in day_names}
    for pt in enriched_points:
        d_str = pt.get("delivery_days_str", "")
        for d in d_str.split(','):
            d_clean = d.strip()
            if d_clean in daily_stats:
                daily_stats[d_clean]["count"] += 1
                daily_stats[d_clean]["load"] += float(pt.get("avg_loads") or 10.0)

    return {
        "points": enriched_points,
        "daily_stats": daily_stats,
        "total_stores": len(enriched_points),
    }


# ----------------------------------------------------------------------
# 求解器注册
# ----------------------------------------------------------------------
schedule_registry.register("cluster_balanced", solve_cluster_balanced_schedule)
schedule_registry.register("default", solve_cluster_balanced_schedule)
schedule_registry.register("truck_schedule", solve_cluster_balanced_schedule)
