from __future__ import annotations

from math import floor
from typing import Any, Optional, Sequence, Union

from app.models.do.StoreDO import StoreNode
from app.utils.distance import DistanceProvider, ensure_provider
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

_DISTANCE_SCALE = 1000
_LOAD_SCALE = 100
_TARGET_FILL_RATE = 0.75


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

    # 本埠/外埠标识：is_homepot 为 1 表示本埠，0 表示外埠；缺失时默认按外埠(0)处理
    is_homepot = int(is_homepot) if is_homepot not in (None, "") else 0

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
        distance_factor: float = 1.3,
        provider: Optional[DistanceProvider] = None,
) -> list[list[int]]:
    prov = ensure_provider(provider)
    coordinates = [(float(depot_lon), float(depot_lat))] + [
        (float(store["lon"]), float(store["lat"])) for store in normalized_stores
    ]
    raw_km_matrix = prov.matrix_km(coordinates, as_list=False)
    scale = distance_factor * _DISTANCE_SCALE
    return [
        [int(round(d * scale)) for d in row]
        for row in raw_km_matrix
    ]


def plan_daily_routes_with_or(
        stores: Sequence[Union[StoreNode, dict[str, Any]]],
        warehouse_lon: float,
        warehouse_lat: float,
        trucks: Optional[Sequence[Union[dict[str, Any], Any]]] = None,
        max_truck_capacity_rate: float = 1.1,
        time_limit_seconds: int = 60,
        return_to_depot: bool = False,
        distance_factor: float = 1.3,
        cost_per_km: float = 4.0,
        vehicle_fixed_cost: float = 200.0,
        underfill_penalty_per_unit: float = 0.5,
        span_cost_coefficient: int = 0,
        max_distance_km: float = 1500.0,
        max_stop_distance_km: float = 35.0,
        inter_stop_penalty_factor: float = 4.0,
        return_arc_cost_factor: float = 0.25,
        max_inter_store_dist_km: Optional[float] = None,
        provider: Optional[DistanceProvider] = None,
) -> list[dict[str, Any]]:
    """
    每日异构车辆路线重规划。
    本埠与外埠门店（按 is_homepot 区分）不能互相拼车，因此先按 is_homepot 分组，
    再对每组分别规划路线，最后合并结果并重新编号。
    目标：兼顾运力成本最优（固定发车成本 + 每公里行驶运费 + 满载率弹性惩罚），
    同时引入同路线门店相对距离约束（max_stop_distance_km 与超距惩罚）、距仓径向差惩罚、
    回仓边内部评估权重折减与门店间累计游走里程维度软上限，保证同路线门店高度聚集，消除跨区长线跳跃。
    """
    if not stores:
        return []

    prov = ensure_provider(provider)
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
            distance_factor=distance_factor,
            cost_per_km=cost_per_km,
            vehicle_fixed_cost=vehicle_fixed_cost,
            underfill_penalty_per_unit=underfill_penalty_per_unit,
            span_cost_coefficient=span_cost_coefficient,
            max_distance_km=max_distance_km,
            max_stop_distance_km=max_stop_distance_km,
            inter_stop_penalty_factor=inter_stop_penalty_factor,
            return_arc_cost_factor=return_arc_cost_factor,
            max_inter_store_dist_km=max_inter_store_dist_km,
            provider=prov,
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
        max_truck_capacity_rate: float = 1.1,
        time_limit_seconds: int = 60,
        return_to_depot: bool = False,
        distance_factor: float = 1.3,
        cost_per_km: float = 4.0,
        vehicle_fixed_cost: float = 200.0,
        underfill_penalty_per_unit: float = 0.5,
        span_cost_coefficient: int = 0,
        max_distance_km: float = 1500.0,
        max_stop_distance_km: float = 35.0,
        inter_stop_penalty_factor: float = 4.0,
        return_arc_cost_factor: float = 0.25,
        max_inter_store_dist_km: Optional[float] = None,
        provider: Optional[DistanceProvider] = None,
) -> list[dict[str, Any]]:
    """对一组同质（同 is_homepot）门店执行异构车辆路线规划。"""
    depot_lon, depot_lat = warehouse_lon, warehouse_lat

    # 构建异构车辆容量、车型名称与真实运费参数数组
    vehicle_capacities_raw: list[int] = []
    vehicle_names_raw: list[str] = []
    vehicle_fixed_costs_raw: list[float] = []
    vehicle_costs_per_km_raw: list[float] = []

    if trucks:
        for t in trucks:
            if isinstance(t, dict):
                cap = int(round(float(t.get("capacity", 230))))
                cnt = int(t.get("count", 1))
                name = str(t.get("name", f"{cap}箱车型"))
                f_cost = float(t.get("fixed_cost", vehicle_fixed_cost)) if t.get("fixed_cost") is not None else vehicle_fixed_cost
                c_km = float(t.get("cost_per_km", cost_per_km)) if t.get("cost_per_km") is not None else cost_per_km
            else:
                cap = int(round(float(getattr(t, "capacity", 230))))
                cnt = int(getattr(t, "count", 1))
                name = str(getattr(t, "name", f"{cap}箱车型"))
                t_f = getattr(t, "fixed_cost", None)
                f_cost = float(t_f) if t_f is not None else vehicle_fixed_cost
                t_c = getattr(t, "cost_per_km", None)
                c_km = float(t_c) if t_c is not None else cost_per_km

            vehicle_capacities_raw.extend([cap] * cnt)
            vehicle_names_raw.extend([name] * cnt)
            vehicle_fixed_costs_raw.extend([f_cost] * cnt)
            vehicle_costs_per_km_raw.extend([c_km] * cnt)
    else:
        default_count = max(1, len(normalized_stores))
        vehicle_capacities_raw = [230] * default_count
        vehicle_names_raw = ["默认4.2米厢车"] * default_count
        vehicle_fixed_costs_raw = [vehicle_fixed_cost] * default_count
        vehicle_costs_per_km_raw = [cost_per_km] * default_count

    if not vehicle_capacities_raw:
        vehicle_capacities_raw = [230] * len(normalized_stores)
        vehicle_names_raw = ["默认4.2米厢车"] * len(normalized_stores)
        vehicle_fixed_costs_raw = [vehicle_fixed_cost] * len(normalized_stores)
        vehicle_costs_per_km_raw = [cost_per_km] * len(normalized_stores)

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

    # 如果总运力不足以承载该组门店总需求，自动以车队中最大车型补充车辆，确保 OR-Tools 能够找到可行解
    total_group_demand = sum(s["scaled_demand"] for s in normalized_stores)
    while sum(vehicle_capacities) < total_group_demand:
        max_idx = vehicle_capacities_raw.index(max(vehicle_capacities_raw))
        vehicle_capacities_raw.append(vehicle_capacities_raw[max_idx])
        vehicle_names_raw.append(vehicle_names_raw[max_idx])
        vehicle_fixed_costs_raw.append(vehicle_fixed_costs_raw[max_idx])
        vehicle_costs_per_km_raw.append(vehicle_costs_per_km_raw[max_idx])
        vehicle_capacities.append(vehicle_capacities[max_idx])

    distance_matrix = _build_distance_matrix(
        normalized_stores,
        depot_lon=depot_lon,
        depot_lat=depot_lat,
        distance_factor=distance_factor,
        provider=provider,
    )
    demands = [0] + [store["scaled_demand"] for store in normalized_stores]

    route_indexes = _solve_heterogeneous_routes_with_or(
        distance_matrix=distance_matrix,
        demands=demands,
        vehicle_capacities=vehicle_capacities,
        vehicle_capacities_raw=vehicle_capacities_raw,
        vehicle_fixed_costs_raw=vehicle_fixed_costs_raw,
        vehicle_costs_per_km_raw=vehicle_costs_per_km_raw,
        underfill_penalty_per_unit=underfill_penalty_per_unit,
        span_cost_coefficient=span_cost_coefficient,
        max_distance_km=max_distance_km,
        max_stop_distance_km=max_stop_distance_km,
        inter_stop_penalty_factor=inter_stop_penalty_factor,
        return_arc_cost_factor=return_arc_cost_factor,
        max_inter_store_dist_km=max_inter_store_dist_km,
        time_limit_seconds=time_limit_seconds,
        return_to_depot=return_to_depot,
    )

    return _build_heterogeneous_route_results(
        route_indexes=route_indexes,
        normalized_stores=normalized_stores,
        distance_matrix=distance_matrix,
        vehicle_capacities_raw=vehicle_capacities_raw,
        vehicle_names_raw=vehicle_names_raw,
        vehicle_fixed_costs_raw=vehicle_fixed_costs_raw,
        vehicle_costs_per_km_raw=vehicle_costs_per_km_raw,
        max_truck_capacity_rate=max_truck_capacity_rate,
        return_to_depot=return_to_depot,
    )


def _calc_route_distance_from_matrix(
        route_index_list: Sequence[int],
        distance_matrix: Sequence[Sequence[int]],
        return_to_depot: bool = False,
) -> float:
    if not route_index_list:
        return 0.0

    # distance_matrix 中索引 0 为 depot，1..N 对应 store_index 0..N-1
    total_m = distance_matrix[0][route_index_list[0] + 1]
    for idx in range(len(route_index_list) - 1):
        u = route_index_list[idx] + 1
        v = route_index_list[idx + 1] + 1
        total_m += distance_matrix[u][v]
    if return_to_depot:
        total_m += distance_matrix[route_index_list[-1] + 1][0]
    return float(total_m) / _DISTANCE_SCALE


def _solve_heterogeneous_routes_with_or(
        distance_matrix: Sequence[Sequence[int]],
        demands: Sequence[int],
        vehicle_capacities: Sequence[int],
        vehicle_capacities_raw: Sequence[int],
        vehicle_fixed_costs_raw: Sequence[float],
        vehicle_costs_per_km_raw: Sequence[float],
        underfill_penalty_per_unit: float = 0.5,
        span_cost_coefficient: int = 0,
        max_distance_km: float = 1500.0,
        max_stop_distance_km: float = 35.0,
        inter_stop_penalty_factor: float = 4.0,
        return_arc_cost_factor: float = 0.25,
        max_inter_store_dist_km: Optional[float] = None,
        time_limit_seconds: int = 60,
        return_to_depot: bool = False,
) -> list[list[int]]:
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except ImportError as exc:
        raise ImportError("请先安装 ortools：pip install ortools") from exc

    vehicle_count = len(vehicle_capacities)
    manager = pywrapcp.RoutingIndexManager(len(distance_matrix), vehicle_count, 0)
    routing = pywrapcp.RoutingModel(manager)

    # 1. 注册每辆车的边行驶成本 (Arc Cost Evaluator)
    # 采用真实运费量纲：内部单位统一为 0.001 元 (毫)
    # distance_matrix[i][j] 单位为米 (km * 1000)
    # 针对回仓路线与门店跨线边施加双重聚集度机制：
    # (a) 回仓边 (to_node == 0) 在闭环模式下按 return_arc_cost_factor 折减内部评估权重，
    #     消除“反正要回仓所以顺路白捡沿途远近门店”的椭圆顺路走廊效应（最终真实里程与运费仍按 100% 核算）；
    # (b) 门店与门店之间的边 (from_node != 0 且 to_node != 0) 施加紧凑半径渐进惩罚、距仓径向差惩罚及超距阶梯阻尼。
    compact_radius_km = max_stop_distance_km * 0.45 if max_stop_distance_km > 0 else 0.0
    eff_return_factor = max(0.0, min(1.0, float(return_arc_cost_factor)))

    for i in range(vehicle_count):
        c_km = vehicle_costs_per_km_raw[i]

        def _make_cost_callback(v_cost_per_km: float):
            def _cost_cb(from_index: int, to_index: int) -> int:
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                if to_node == 0:
                    if not return_to_depot:
                        return 0
                    ret_dist_m = distance_matrix[from_node][0]
                    return int(round(ret_dist_m * v_cost_per_km * eff_return_factor))

                dist_m = distance_matrix[from_node][to_node]
                cost_units = int(round(dist_m * v_cost_per_km))

                # 同路线门店相对距离、距仓径向差与集中度惩罚 (仅针对门店与门店之间的边)
                if from_node != 0 and to_node != 0 and max_stop_distance_km > 0:
                    dist_km = dist_m / _DISTANCE_SCALE
                    penalty_rmb = 0.0

                    # (1) 超过紧凑半径时施加平滑累进惩罚，抑制中等间距连续跳跃
                    if dist_km > compact_radius_km:
                        compact_excess_km = dist_km - compact_radius_km
                        penalty_rmb += compact_excess_km * (v_cost_per_km * inter_stop_penalty_factor * 0.5)

                    # (2) 距仓径向差惩罚：抑制远郊店与近郊店在同一路线内跨圈层混拼
                    radial_diff_km = abs(distance_matrix[0][from_node] - distance_matrix[0][to_node]) / _DISTANCE_SCALE
                    if radial_diff_km > compact_radius_km:
                        radial_excess_km = radial_diff_km - compact_radius_km
                        penalty_rmb += radial_excess_km * (v_cost_per_km * inter_stop_penalty_factor * 0.5)

                    # (3) 超过最大单步相对距离阈值时施加起步阻尼 + 强线性惩罚
                    if dist_km > max_stop_distance_km:
                        excess_km = dist_km - max_stop_distance_km
                        penalty_rmb += 50.0 + excess_km * (v_cost_per_km * inter_stop_penalty_factor)

                    if penalty_rmb > 0.0:
                        cost_units += int(round(penalty_rmb * 1000))

                return cost_units

            return _cost_cb

        transit_callback_index = routing.RegisterTransitCallback(_make_cost_callback(c_km))
        routing.SetArcCostEvaluatorOfVehicle(transit_callback_index, i)

    # 2. 载重约束维度
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
    capacity_dimension = routing.GetDimensionOrDie("Capacity")

    # 3. 距离约束维度 (全路线物理里程上限)
    def distance_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        if not return_to_depot and to_node == 0:
            return 0
        return distance_matrix[from_node][to_node]

    distance_callback_index = routing.RegisterTransitCallback(distance_callback)
    max_distance_capacity = int(round(max_distance_km * _DISTANCE_SCALE))
    routing.AddDimension(
        distance_callback_index,
        0,  # 无松弛等待
        max_distance_capacity,
        True,  # 累加里程从 0 开始
        "Distance",
    )

    if span_cost_coefficient > 0:
        distance_dimension = routing.GetDimensionOrDie("Distance")
        distance_dimension.SetGlobalSpanCostCoefficient(int(span_cost_coefficient))

    # 3b. 纯门店间累计游走里程维度 (InterStoreDistance，不含出仓 0->s1 与回仓 sk->0)
    # 根据三角不等式，同路线任意两门店间跨度直径 max_store_distance_km <= 门店间累计游走里程，
    # 对该维度终点施加软上限可从拓扑结构上阻断“蜈蚣链式串联”与“回程顺路长距离跨区扫货”。
    def inter_store_distance_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        if from_node == 0 or to_node == 0:
            return 0
        return distance_matrix[from_node][to_node]

    inter_store_dist_cb_idx = routing.RegisterTransitCallback(inter_store_distance_callback)
    routing.AddDimension(
        inter_store_dist_cb_idx,
        0,
        max_distance_capacity,
        True,
        "InterStoreDistance",
    )
    if max_stop_distance_km > 0:
        inter_store_dim = routing.GetDimensionOrDie("InterStoreDistance")
        eff_inter_store_limit_km = (
            float(max_inter_store_dist_km)
            if max_inter_store_dist_km is not None and max_inter_store_dist_km > 0
            else max_stop_distance_km * 1.25
        )
        soft_span_limit_m = int(round(eff_inter_store_limit_km * _DISTANCE_SCALE))
        for i in range(vehicle_count):
            c_km = vehicle_costs_per_km_raw[i]
            span_penalty_per_m = max(1, int(round(c_km * inter_stop_penalty_factor)))
            inter_store_dim.SetCumulVarSoftUpperBound(
                routing.End(i),
                soft_span_limit_m,
                span_penalty_per_m,
            )

    # 4. 设定基于真实业务成本的单车固定成本与满载率软下界经济学模型
    # 对每辆车在 Capacity 维度终点设置目标满载率软下界 (target_load_scaled)，
    # 同时在 SetFixedCostOfVehicle 中补偿未启用车辆的零载基准惩罚，使得：
    # - 未启用车辆 (load=0) 净增成本为 0；
    # - 达到目标满载率 (load >= target) 的车辆仅支付真实固定发车费 f_cost；
    # - 低满载尾车 (0 < load < target) 按差额支付 underfill_penalty_per_unit * (target - load)，抑制尾车空载跨区乱跑。
    underfill_coeff = max(0, int(round(underfill_penalty_per_unit * (1000.0 / _LOAD_SCALE))))
    for i in range(vehicle_count):
        raw_cap = vehicle_capacities_raw[i]
        f_cost = vehicle_fixed_costs_raw[i]
        target_load_scaled = min(
            vehicle_capacities[i],
            int(round(raw_cap * _TARGET_FILL_RATE * _LOAD_SCALE)),
        )
        base_fixed_units = int(round(f_cost * 1000))
        if underfill_coeff > 0 and target_load_scaled > 0:
            capacity_dimension.SetCumulVarSoftLowerBound(
                routing.End(i),
                target_load_scaled,
                underfill_coeff,
            )
            fixed_cost_units = base_fixed_units + target_load_scaled * underfill_coeff
        else:
            fixed_cost_units = base_fixed_units
        routing.SetFixedCostOfVehicle(max(0, fixed_cost_units), i)

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
        routes.append(route)
    return routes


def _build_heterogeneous_route_results(
        route_indexes: Sequence[Sequence[int]],
        normalized_stores: Sequence[dict[str, Any]],
        distance_matrix: Sequence[Sequence[int]],
        vehicle_capacities_raw: Sequence[int],
        vehicle_names_raw: Optional[Sequence[str]] = None,
        vehicle_fixed_costs_raw: Optional[Sequence[float]] = None,
        vehicle_costs_per_km_raw: Optional[Sequence[float]] = None,
        max_truck_capacity_rate: float = 1.1,
        return_to_depot: bool = False,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    route_no = 1
    for vehicle_id, route_index_list in enumerate(route_indexes):
        if not route_index_list:
            continue

        route_stores = [normalized_stores[store_index] for store_index in route_index_list]
        route_load = sum(store["demand"] for store in route_stores)
        route_distance = _calc_route_distance_from_matrix(
            route_index_list,
            distance_matrix=distance_matrix,
            return_to_depot=return_to_depot,
        )

        raw_capacity = vehicle_capacities_raw[vehicle_id] if vehicle_id < len(vehicle_capacities_raw) else 230
        if vehicle_names_raw and vehicle_id < len(vehicle_names_raw):
            truck_name = vehicle_names_raw[vehicle_id]
        else:
            truck_name = f"{raw_capacity}箱车型"

        c_km = vehicle_costs_per_km_raw[vehicle_id] if vehicle_costs_per_km_raw and vehicle_id < len(vehicle_costs_per_km_raw) else 4.0
        f_cost = vehicle_fixed_costs_raw[vehicle_id] if vehicle_fixed_costs_raw and vehicle_id < len(vehicle_fixed_costs_raw) else 200.0

        effective_capacity = float(floor(raw_capacity * max_truck_capacity_rate))
        fill_rate = round(route_load / raw_capacity, 4) if raw_capacity > 0 else 1.0
        transport_cost = round(route_distance * c_km, 2)
        total_cost = round(transport_cost + f_cost, 2)

        # 直接复用 DistanceProvider 生成的 distance_matrix 计算同线路门店集中度与跨距指标
        consecutive_dists = [
            distance_matrix[route_index_list[s_idx] + 1][route_index_list[s_idx + 1] + 1] / _DISTANCE_SCALE
            for s_idx in range(len(route_index_list) - 1)
        ]
        max_stop_dist = max(consecutive_dists) if consecutive_dists else 0.0

        all_pair_dists = [
            distance_matrix[route_index_list[i_idx] + 1][route_index_list[j_idx] + 1] / _DISTANCE_SCALE
            for i_idx in range(len(route_index_list))
            for j_idx in range(i_idx + 1, len(route_index_list))
        ]
        max_store_dist = max(all_pair_dists) if all_pair_dists else 0.0

        results.append(
            {
                "route_no": route_no,
                "truck_name": truck_name,
                "vehicle_type": raw_capacity,
                "is_homepot": route_stores[0]["is_homepot"],
                "load": route_load,
                "capacity_limit": effective_capacity,
                "distance_km": round(route_distance, 2),
                "fill_rate": fill_rate,
                "cost_per_km": c_km,
                "fixed_cost": f_cost,
                "transport_cost": transport_cost,
                "total_cost": total_cost,
                "max_stop_distance_km": round(max_stop_dist, 2),
                "max_store_distance_km": round(max_store_dist, 2),
                "path_store_ids": [store["label"] for store in route_stores],
                "stops": [store["payload"] for store in route_stores],
            }
        )
        route_no += 1
    return results
