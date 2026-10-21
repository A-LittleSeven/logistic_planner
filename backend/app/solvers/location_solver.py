"""物流选址求解器。

v1: 加权重心法 (Center of Gravity)。
拓展: 在此新增 p_median 等函数并 register 进 location_registry。
"""
import numpy as np

from app.utils.distance import DistanceProvider
from app.core import location_registry
from app.models.location import LocationSolveRequest


def solve_center_of_gravity(req: LocationSolveRequest, provider: DistanceProvider) -> dict:
    if not req.points:
        raise ValueError("至少需要 1 个需求点")

    coords = np.array([[p.lng, p.lat] for p in req.points], dtype=float)
    weights = np.array([p.weight for p in req.points], dtype=float)
    total_w = weights.sum()

    # 加权重心: lng* = Σ(w·lng)/Σw,  lat* = Σ(w·lat)/Σw
    center_lng = float((weights * coords[:, 0]).sum() / total_w)
    center_lat = float((weights * coords[:, 1]).sum() / total_w)
    center = (center_lng, center_lat)

    # 总加权距离 (用所选距离提供者)
    twd = sum(
        p.weight * provider.distance(center_lng, center_lat, p.lng, p.lat) for p in req.points
    )

    return {
        "algorithm": "center_of_gravity",
        "optimal": {"lng": center_lng, "lat": center_lat},
        "total_weighted_distance": float(twd),
        "points": [p.model_dump() for p in req.points],
    }


location_registry.register("center_of_gravity", solve_center_of_gravity)
