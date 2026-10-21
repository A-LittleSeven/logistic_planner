"""数据模型转换与适配器模块 (Model Converters & Adapters)。

解决不同层次之间（DTO <-> ORM <-> Domain Node <-> Solver Dict/Matrix）的数据格式转换，
统一坐标字段映射 (lng/longitude/store_lon, lat/latitude/store_lat) 与默认值填充。
"""
from typing import Any, Dict, List, Optional, Tuple, Union
from app.models.do.StoreDO import StoreNode
from app.models.dto.StoreDTO import StoreBase
from app.utils.distance import haversine


def normalize_coordinates(data: Union[Dict[str, Any], Any]) -> Tuple[float, float]:
    """统一从各种字典/对象中提取 (lng, lat) 经纬度元组。"""
    if isinstance(data, dict):
        lng = data.get("lng") or data.get("longitude") or data.get("store_lon")
        lat = data.get("lat") or data.get("latitude") or data.get("store_lat")
    else:
        lng = getattr(data, "lng", None) or getattr(data, "longitude", None) or getattr(data, "store_lon", None)
        lat = getattr(data, "lat", None) or getattr(data, "latitude", None) or getattr(data, "store_lat", None)
        if (lng is None or lat is None) and hasattr(data, "model_extra") and data.model_extra:
            lng = lng or data.model_extra.get("lng") or data.model_extra.get("longitude") or data.model_extra.get("store_lon")
            lat = lat or data.model_extra.get("lat") or data.model_extra.get("latitude") or data.model_extra.get("store_lat")

    if lng is None or lat is None:
        raise ValueError(f"无法从对象中提取有效经纬度坐标: {data}")
    return float(lng), float(lat)


def parse_available_trucks(val: Any) -> List[str]:
    """将车型限制解析为规范的字符串列表。"""
    if isinstance(val, list):
        return [str(t).strip() for t in val if str(t).strip()]
    elif isinstance(val, str) and val.strip():
        return [t.strip() for t in val.split(",") if t.strip()]
    return []


def to_store_node(
    data: Union[Dict[str, Any], Any],
    default_idx: int = 0,
    depot_lng: Optional[float] = None,
    depot_lat: Optional[float] = None
) -> StoreNode:
    """将字典、Pydantic DTO 或 ORM 对象安全转换为启发式算法所需的 StoreNode 领域对象。"""
    if isinstance(data, StoreNode):
        return data

    if isinstance(data, dict):
        d = data
    elif hasattr(data, "model_dump"):
        d = data.model_dump()
        if hasattr(data, "model_extra") and data.model_extra:
            d.update(data.model_extra)
    elif hasattr(data, "__dict__"):
        d = {k: v for k, v in data.__dict__.items() if not k.startswith("_")}
    else:
        d = dict(data)

    lng, lat = normalize_coordinates(d)

    # 中心仓坐标与距离计算
    center_lng = d.get("center_lng") or d.get("cluster_center_lon") or lng
    center_lat = d.get("center_lat") or d.get("cluster_center_lat") or lat
    s_dist = d.get("sdist_warehouse") or d.get("s_dist") or 0.0
    c_dist = d.get("cdist_warehouse") or d.get("c_dist") or 0.0

    if (s_dist <= 0.0001) and (depot_lng is not None and depot_lat is not None):
        s_dist = haversine(float(lng), float(lat), float(depot_lng), float(depot_lat))
    if (c_dist <= 0.0001) and (depot_lng is not None and depot_lat is not None):
        c_dist = haversine(float(center_lng), float(center_lat), float(depot_lng), float(depot_lat))

    truck_list = parse_available_trucks(d.get("available_truck"))
    dept_id = str(d.get("dept_id") or d.get("shop_code") or default_idx)
    shop_code = str(d.get("shop_code") or d.get("dept_id") or default_idx)
    name = str(d.get("name") or d.get("shop_name") or f"store_{default_idx}")
    freq = int(float(d.get("frequency") or 1))
    avg_loads = float(d.get("avg_loads") or d.get("demand") or 10.0)

    try:
        is_homepot = int(d.get("is_homepot") if d.get("is_homepot") is not None else 1)
    except (ValueError, TypeError):
        is_homepot = 1

    return StoreNode(
        point_idx=default_idx,
        shop_code=shop_code,
        name=name,
        dept_id=dept_id,
        district=str(d.get("district") or ""),
        district_sub=str(d.get("district_sub") or ""),
        city_name=str(d.get("city_name") or ""),
        warzone=str(d.get("warzone") or "0"),
        store_lon=float(lng),
        store_lat=float(lat),
        cluster_center_lon=float(center_lng),
        cluster_center_lat=float(center_lat),
        sdist_warehouse=float(s_dist),
        cdist_warehouse=float(c_dist),
        frequency=freq,
        store_freq_remains=freq,
        is_homepot=is_homepot,
        service_time=float(d.get("service_time") or 0.5),
        available_truck=truck_list,
        address=str(d.get("address") or ""),
        avg_loads=avg_loads,
        demand=avg_loads,
        cluster_center_id=int(d.get("cluster_center_id") or d.get("cluster_id") or 0),
    )
