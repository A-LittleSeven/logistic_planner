"""物流选址 API。"""
from fastapi import APIRouter, Depends, HTTPException

from app.core import get_distance_provider
from app.utils.distance import DistanceProvider
from app.core import location_registry
from app.models.location import LocationSolveRequest, LocationSolveResponse
from app.solvers import location_solver  # noqa: F401  导入即注册求解器

router = APIRouter()


@router.get("/algorithms")
def algorithms():
    """列出可用算法 (供前端下拉选择 / 展示拓展能力)。"""
    return {"algorithms": location_registry.list()}


@router.post("/solve", response_model=LocationSolveResponse)
def solve(
    req: LocationSolveRequest,
    provider: DistanceProvider = Depends(get_distance_provider),
):
    try:
        solver = location_registry.get(req.algorithm)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        return solver(req, provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
