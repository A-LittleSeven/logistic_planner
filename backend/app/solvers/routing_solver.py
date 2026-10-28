"""
物流路线规划求解器 (Google OR-Tools CVRP 约束优化求解)。
"""
from app.utils.distance import DistanceProvider
from app.utils.registry import routing_registry
from app.models.dto.RoutingDTO import RoutingSolveRequest


def solve_or_tools_vrp(req: RoutingSolveRequest, provider: DistanceProvider) -> dict:
    if not req.points:
        raise ValueError("至少需要 1 个点")

    depot_idx = 0
    for i, p in enumerate(req.points):
        if p.is_depot:
            depot_idx = i
            break

    depot_point = req.points[depot_idx]
    customers = [p for i, p in enumerate(req.points) if i != depot_idx]

    if not customers:
        return {
            "algorithm": "ortools",
            "routes": [],
            "total_distance": 0.0,
            "total_stores": 0,
            "points": [p.model_dump() for p in req.points]
        }

    # Count of trucks and capacity
    # Convert customers to stores dict list for route_replanner
    stores_data = []
    for idx, p in enumerate(customers):
        # Extract is_homepot safely from RoutePoint or model_extra (未提供时默认外埠 0)
        is_hp = getattr(p, "is_homepot", None)
        if (is_hp is None or is_hp == "") and hasattr(p, "model_extra") and p.model_extra:
            is_hp = p.model_extra.get("is_homepot")

        if is_hp is None or is_hp == "":
            is_hp = 0

        try:
            is_hp = int(is_hp)
        except (ValueError, TypeError):
            is_hp = 0


        stores_data.append({
            "lon": float(p.lng),
            "lat": float(p.lat),
            "avg_loads": float(p.avg_loads or 10.0),
            "shop_code": f"cust_{idx}",
            "dept_id": f"cust_{idx}",
            "name": p.name or f"store_{idx}",
            "is_homepot": is_hp,
            "warehouse_lon": float(depot_point.lng),
            "warehouse_lat": float(depot_point.lat)
        })

    opts = req.options or {}
    max_truck_capacity_rate = float(opts.get("max_capacity_rate", opts.get("max_truck_capacity_rate", 1.0)))
    time_limit_seconds = int(opts.get("time_limit_seconds", opts.get("time_limit", 5)))
    return_to_depot = bool(opts.get("return_to_depot", False))
    distance_factor = float(opts.get("distance_factor", opts.get("detour_factor", 1.3)))
    cost_per_km = float(opts.get("cost_per_km", 4.0))
    vehicle_fixed_cost = float(opts.get("vehicle_fixed_cost", opts.get("fixed_cost", 200.0)))
    underfill_penalty_per_unit = float(opts.get("underfill_penalty_per_unit", opts.get("underfill_penalty", 0.5)))
    span_cost_coefficient = int(opts.get("span_cost_coefficient", 0))
    max_distance_km = float(opts.get("max_distance_km", 1500.0))
    max_stop_distance_km = float(opts.get("max_stop_distance_km", opts.get("max_relative_distance_km", 35.0)))
    inter_stop_penalty_factor = float(opts.get("inter_stop_penalty_factor", 4.0))

    # Pass the heterogeneous vehicle fleet (trucks)
    trucks_data = [t.model_dump() if hasattr(t, "model_dump") else dict(t) for t in req.trucks]

    from app.core.optimizer.route_replanner import plan_daily_routes_with_or
    daily_routes = plan_daily_routes_with_or(
        stores=stores_data,
        trucks=trucks_data,
        max_truck_capacity_rate=max_truck_capacity_rate,
        warehouse_lon=depot_point.lng,
        warehouse_lat=depot_point.lat,
        time_limit_seconds=time_limit_seconds,
        return_to_depot=return_to_depot,
        distance_factor=distance_factor,
        cost_per_km=cost_per_km,
        vehicle_fixed_cost=vehicle_fixed_cost,
        underfill_penalty_per_unit=underfill_penalty_per_unit,
        span_cost_coefficient=span_cost_coefficient,
        max_distance_km=max_distance_km,
        max_stop_distance_km=max_stop_distance_km,
        inter_stop_penalty_factor=inter_stop_penalty_factor,
    )

    routes_list = []
    total_dist = 0.0
    for r_idx, route in enumerate(daily_routes):
        # label 恒为 "cust_{idx}"（构造 stores_data 时生成），直接解析索引
        order_indices = []
        for label in route.get("path_store_ids", []):
            c_idx = int(str(label).split("_")[1])
            order_indices.append(c_idx)

        # Wrap route with depot indicator (-1)
        if return_to_depot:
            order_indices = [-1] + order_indices + [-1]
        else:
            order_indices = [-1] + order_indices

        truck_name = route.get("truck_name") or f"货车 ({route.get('vehicle_type', 230)}箱)"

        routes_list.append({
            "truck_name": truck_name,
            "order": order_indices,
            "distance": float(route.get("distance_km", 0.0)),
            "load": float(route.get("load", 0.0)),
            "is_homepot": int(route.get("is_homepot") if route.get("is_homepot") is not None else 0),
            "return_to_depot": bool(return_to_depot),
            "fill_rate": float(route.get("fill_rate", 0.0)),
            "cost_per_km": float(route.get("cost_per_km", cost_per_km)),
            "fixed_cost": float(route.get("fixed_cost", vehicle_fixed_cost)),
            "transport_cost": float(route.get("transport_cost", 0.0)),
            "total_cost": float(route.get("total_cost", 0.0)),
            "max_stop_distance_km": float(route.get("max_stop_distance_km", 0.0)),
            "max_store_distance_km": float(route.get("max_store_distance_km", 0.0)),
        })
        total_dist += route.get("distance_km", 0.0)

    total_cost_sum = sum(r.get("total_cost", 0.0) for r in routes_list)
    return {
        "algorithm": "ortools",
        "routes": routes_list,
        "total_distance": round(float(total_dist), 2),
        "total_cost": round(float(total_cost_sum), 2),
        "total_stores": len(customers),
        "return_to_depot": bool(return_to_depot),
        "points": [p.model_dump() for p in req.points]
    }


routing_registry.register("ortools", solve_or_tools_vrp)
