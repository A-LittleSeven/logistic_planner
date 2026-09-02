from __future__ import annotations

from math import floor
from typing import Any, Optional, Sequence, Union

from app.models.store import StoreNode
from app.utils.distance import haversine
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

_DISTANCE_SCALE = 1000
_LOAD_SCALE = 1000


def _normalize_store(store: Union[StoreNode, dict[str, Any]], index: int) -> dict[str, Any]:
    if isinstance(store, StoreNode):
        lon = store.store_lon
        lat = store.store_lat
        demand = store.avg_loads
        label = store.dept_id or store.shop_code or f"store_{index}"
        payload = store
        is_homepot = store.is_homepot
        store_warehouse_lon = store.warehouse_lon
        store_warehouse_lat = store.warehouse_lat
    else:
        lon = store.get("store_lon", store.get("lon"))
        lat = store.get("store_lat", store.get("lat"))
        demand = store.get("avg_loads", store.get("demand"))
        label = store.get("dept_id") or store.get("shop_code") or store.get("id") or f"store_{index}"
        payload = store
        is_homepot = store.get("is_homepot")
        store_warehouse_lon = store.get("warehouse_lon")
        store_warehouse_lat = store.get("warehouse_lat")

    if lon is None or lat is None:
        raise ValueError(f"门店 {label} 缺少经纬度信息")
    if demand is None:
        raise ValueError(f"门店 {label} 缺少需求货量信息")
    if demand < 0:
        raise ValueError(f"门店 {label} 的需求货量不能小于 0")

    # 本埠/外埠标识：is_homepot 为 1 表示本埠，0 表示外埠；缺失时默认按本埠(1)处理
    is_homepot = int(is_homepot) if is_homepot is not None else 1

    return {
        "label": str(label),
        "lon": float(lon),
        "lat": float(lat),
        "demand": float(demand),
        "scaled_demand": int(round(float(demand) * _LOAD_SCALE)),
        "payload": payload,
        "is_homepot": is_homepot,
        "warehouse_lon": None if store_warehouse_lon is None else float(store_warehouse_lon),
        "warehouse_lat": None if store_warehouse_lat is None else float(store_warehouse_lat),
    }


def _build_distance_matrix(
        normalized_stores: Sequence[dict[str, Any]],
        depot_lon: float,
        depot_lat: float,
) -> list[list[int]]:
    coordinates = [(depot_lon, depot_lat)] + [(store["lon"], store["lat"]) for store in normalized_stores]
    distance_matrix: list[list[int]] = []
    for from_lon, from_lat in coordinates:
        row = []
        for to_lon, to_lat in coordinates:
            distance = haversine(from_lon, from_lat, to_lon, to_lat)
            row.append(int(round(distance * _DISTANCE_SCALE)))
        distance_matrix.append(row)
    return distance_matrix


def _solve_routes_with_or(
        distance_matrix: Sequence[Sequence[int]],
        demands: Sequence[int],
        vehicle_capacity: int,
        vehicle_count: int,
        time_limit_seconds: int,
) -> list[list[int]]:

    manager = pywrapcp.RoutingIndexManager(len(distance_matrix), vehicle_count, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        return int(demands[from_node])

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,
        [vehicle_capacity] * vehicle_count,
        True,
        "Capacity",
    )

    vehicle_fixed_cost = max(max(row) for row in distance_matrix) * len(demands)
    routing.SetFixedCostOfAllVehicles(vehicle_fixed_cost)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.FromSeconds(int(time_limit_seconds))

    solution = routing.SolveWithParameters(search_parameters)
    if solution is None:
        raise ValueError("OR-Tools 未找到可行路径，请检查容量约束是否过严")

    routes: list[list[int]] = []
    for vehicle_id in range(vehicle_count):
        index = routing.Start(vehicle_id)
        route: list[int] = []
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            if node_index != 0:
                route.append(node_index - 1)
            index = solution.Value(routing.NextVar(index))
        if route:
            routes.append(route)
    return routes


def _build_route_results(
        route_indexes: Sequence[Sequence[int]],
        normalized_stores: Sequence[dict[str, Any]],
        depot_lon: float,
        depot_lat: float,
        effective_capacity: float,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for route_no, route_index_list in enumerate(route_indexes, start=1):
        route_stores = [normalized_stores[store_index] for store_index in route_index_list]
        route_load = sum(store["demand"] for store in route_stores)
        route_distance = _calc_route_distance(route_stores, depot_lon=depot_lon, depot_lat=depot_lat)
        results.append(
            {
                "route_no": route_no,
                "load": route_load,
                "capacity_limit": effective_capacity,
                "distance_km": route_distance,
                "path_store_ids": [store["label"] for store in route_stores],
                "stops": [store["payload"] for store in route_stores],
            }
        )
    return results


def plan_daily_routes_with_or(
        stores: Sequence[Union[StoreNode, dict[str, Any]]],
        warehouse_lat: float,
        warehouse_lon: float,
        trucks: Optional[Sequence[Union[dict[str, Any], Any]]] = None,
        max_truck_capacity_rate: float = 1.1,
        time_limit_seconds: int = 60,
        return_to_depot: bool = False,
) -> list[dict[str, Any]]:
    """
    每日异构车辆路线重规划。
    本埠与外埠门店（按 is_homepot 区分）不能互相拼车，因此先按 is_homepot 分组，
    再对每组分别规划路线，最后合并结果并重新编号。
    目标：在满足载重限制下，最小化未使用的车辆容量（最大化满载率），并最小化总距离。
    """
    if not stores:
        return []

    normalized_stores = [_normalize_store(store, idx) for idx, store in enumerate(stores, start=1)]

    # 按 is_homepot 分组：本埠(1)与外埠(0)分别规划，组间不拼车
    grouped_stores = _group_stores_by_homepot(normalized_stores)

    all_results: list[dict[str, Any]] = []
    route_no = 1
    for group_stores in grouped_stores:
        group_results = _plan_routes_for_group(
            normalized_stores=group_stores,
            warehouse_lon=warehouse_lon,
            warehouse_lat=warehouse_lat,
            trucks=trucks,
            max_truck_capacity_rate=max_truck_capacity_rate,
            time_limit_seconds=time_limit_seconds,
            return_to_depot=return_to_depot,
        )
        for result in group_results:
            result["route_no"] = route_no
            route_no += 1
        all_results.extend(group_results)
    return all_results


def _group_stores_by_homepot(
        normalized_stores: Sequence[dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    """
    按 is_homepot 取值对门店分组，保证组内同质、组间不拼车。
    返回分组列表，按 is_homepot 取值升序排列以保证结果稳定。
    """
    groups: dict[int, list[dict[str, Any]]] = {}
    for store in normalized_stores:
        groups.setdefault(store["is_homepot"], []).append(store)
    return [groups[key] for key in sorted(groups)]


def _plan_routes_for_group(
        normalized_stores: Sequence[dict[str, Any]],
        warehouse_lon: float,
        warehouse_lat: float,
        trucks: Optional[Sequence[Union[dict[str, Any], Any]]] = None,
        max_truck_capacity_rate: float = 1.0,
        time_limit_seconds: int = 60,
        return_to_depot: bool = False,
) -> list[dict[str, Any]]:
    """对一组同质（同 is_homepot）门店执行异构车辆路线规划。"""
    depot_lon, depot_lat = warehouse_lon, warehouse_lat

    # 构建异构车辆容量与车型名称数组
    vehicle_capacities_raw: list[int] = []
    vehicle_names_raw: list[str] = []

    if trucks:
        for t in trucks:
            if isinstance(t, dict):
                cap = int(round(float(t.get("capacity", 230))))
                cnt = int(t.get("count", 1))
                name = str(t.get("name", f"{cap}箱车型"))
            else:
                cap = int(round(float(getattr(t, "capacity", 230))))
                cnt = int(getattr(t, "count", 1))
                name = str(getattr(t, "name", f"{cap}箱车型"))
            vehicle_capacities_raw.extend([cap] * cnt)
            vehicle_names_raw.extend([name] * cnt)
    else:
        default_count = max(1, len(normalized_stores))
        vehicle_capacities_raw = [230] * default_count
        vehicle_names_raw = ["默认4.2米厢车"] * default_count

    if not vehicle_capacities_raw:
        vehicle_capacities_raw = [230] * len(normalized_stores)
        vehicle_names_raw = ["默认4.2米厢车"] * len(normalized_stores)

    # 乘以 max_truck_capacity_rate
    vehicle_capacities = [
        floor(cap * max_truck_capacity_rate) * _LOAD_SCALE
        for cap in vehicle_capacities_raw
    ]

    # 检查是否有单个门店需求超出了最大可用车型的容量
    max_cap = max(vehicle_capacities)
    oversized_stores = [
        store["label"] for store in normalized_stores if store["scaled_demand"] > max_cap
    ]
    if oversized_stores:
        raise ValueError(
            f"存在门店需求超过最大单车可用载重限制: {oversized_stores}，"
            f"最大可用载重={max_cap / _LOAD_SCALE}"
        )

    distance_matrix = _build_distance_matrix(normalized_stores, depot_lon=depot_lon, depot_lat=depot_lat)
    demands = [0] + [store["scaled_demand"] for store in normalized_stores]

    route_indexes = _solve_heterogeneous_routes_with_or(
        distance_matrix=distance_matrix,
        demands=demands,
        vehicle_capacities=vehicle_capacities,
        time_limit_seconds=time_limit_seconds,
        return_to_depot=return_to_depot,
    )

    return _build_heterogeneous_route_results(
        route_indexes=route_indexes,
        normalized_stores=normalized_stores,
        depot_lon=depot_lon,
        depot_lat=depot_lat,
        vehicle_capacities_raw=vehicle_capacities_raw,
        vehicle_names_raw=vehicle_names_raw,
        max_truck_capacity_rate=max_truck_capacity_rate,
        return_to_depot=return_to_depot,
    )


def _calc_route_distance(
        route_stores: Sequence[dict[str, Any]],
        depot_lon: float,
        depot_lat: float,
        return_to_depot: bool = True,
) -> float:
    if not route_stores:
        return 0.0

    distance = haversine(depot_lon, depot_lat, route_stores[0]["lon"], route_stores[0]["lat"])
    for index in range(len(route_stores) - 1):
        current_store = route_stores[index]
        next_store = route_stores[index + 1]
        distance += haversine(current_store["lon"], current_store["lat"], next_store["lon"], next_store["lat"])
    if return_to_depot:
        distance += haversine(route_stores[-1]["lon"], route_stores[-1]["lat"], depot_lon, depot_lat)
    return distance


def _solve_heterogeneous_routes_with_or(
        distance_matrix: Sequence[Sequence[int]],
        demands: Sequence[int],
        vehicle_capacities: Sequence[int],
        time_limit_seconds: int,
        return_to_depot: bool = True,
) -> list[list[int]]:
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except ImportError as exc:
        raise ImportError("请先安装 ortools：pip install ortools") from exc

    vehicle_count = len(vehicle_capacities)
    manager = pywrapcp.RoutingIndexManager(len(distance_matrix), vehicle_count, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        # 如果不需要返回仓库，且目标节点为仓库(0)，则距离成本为0
        if not return_to_depot and to_node == 0:
            return 0
        return distance_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        return int(demands[from_node])

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,
        vehicle_capacities,
        True,
        "Capacity",
    )
    # 我们设置一个非常大的基础固定成本来尽量减少使用的车辆总数，
    # 同时对容量大的车辆给予一定的成本减免（减去与其容量成正比的值），从而让求解器更倾向于选用大车。
    base_cost = max(max(row) for row in distance_matrix) * len(demands) * 100
    for i in range(vehicle_count):
        # 车辆容量越大，扣减的成本越多，最终固定成本越小
        cost = int(base_cost - (vehicle_capacities[i] / _LOAD_SCALE) * 1000)
        cost = max(cost, 0)
        routing.SetFixedCostOfVehicle(cost, i)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    # 使用 SAVINGS 或 PARALLEL_CHEAPEST_INSERTION 算法作为初始解，通常能获得形状更好的（不交叉的）初始路径
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.LOCAL_CHEAPEST_INSERTION
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.FromSeconds(int(time_limit_seconds))

    solution = routing.SolveWithParameters(search_parameters)
    if solution is None:
        raise ValueError("OR-Tools 未找到可行路径，请检查容量约束是否过严")

    routes: list[list[int]] = []
    for vehicle_id in range(vehicle_count):
        index = routing.Start(vehicle_id)
        route: list[int] = []
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            if node_index != 0:
                route.append(node_index - 1)
            index = solution.Value(routing.NextVar(index))
        routes.append(route)  # 异构车辆需要保留每辆车的路径记录，即使为空，以对应车型
    return routes


def _build_heterogeneous_route_results(
        route_indexes: Sequence[Sequence[int]],
        normalized_stores: Sequence[dict[str, Any]],
        depot_lon: float,
        depot_lat: float,
        vehicle_capacities_raw: Sequence[int],
        vehicle_names_raw: Optional[Sequence[str]] = None,
        max_truck_capacity_rate: float = 1.0,
        return_to_depot: bool = True,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    route_no = 1
    for vehicle_id, route_index_list in enumerate(route_indexes):
        if not route_index_list:
            continue

        route_stores = [normalized_stores[store_index] for store_index in route_index_list]
        route_load = sum(store["demand"] for store in route_stores)
        route_distance = _calc_route_distance(
            route_stores, depot_lon=depot_lon, depot_lat=depot_lat, return_to_depot=return_to_depot
        )

        raw_capacity = vehicle_capacities_raw[vehicle_id] if vehicle_id < len(vehicle_capacities_raw) else 230
        if vehicle_names_raw and vehicle_id < len(vehicle_names_raw):
            truck_name = vehicle_names_raw[vehicle_id]
        else:
            truck_name = f"{raw_capacity}箱车型"
        effective_capacity = float(floor(raw_capacity * max_truck_capacity_rate))

        results.append(
            {
                "route_no": route_no,
                "truck_name": truck_name,
                "vehicle_type": raw_capacity,
                "is_homepot": route_stores[0]["is_homepot"],
                "load": route_load,
                "capacity_limit": effective_capacity,
                "distance_km": route_distance,
                "path_store_ids": [store["label"] for store in route_stores],
                "stops": [store["payload"] for store in route_stores],
            }
        )
        route_no += 1
    return results
