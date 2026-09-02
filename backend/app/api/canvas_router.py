import json
import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.database import get_db
from app.db.models import DBCanvas, DBCanvasVersion
from app.models.canvas_schema import (
    CanvasCreate,
    CanvasUpdate,
    CanvasVersionCreate,
    CanvasSummaryResponse,
    CanvasDetailResponse,
    CanvasVersionResponse,
)

router = APIRouter()


def _parse_snapshot(snapshot_raw: Any) -> dict:
    if isinstance(snapshot_raw, dict):
        return snapshot_raw
    if isinstance(snapshot_raw, str):
        try:
            return json.loads(snapshot_raw)
        except Exception:
            return {}
    return {}


@router.post("", response_model=CanvasDetailResponse, summary="创建新规划画布")
def create_canvas(req: CanvasCreate, db: Session = Depends(get_db)):
    canvas_uuid = f"canvas_{uuid.uuid4().hex[:12]}"
    
    # 1. 组装初始快照数据
    stores_data = [p.model_dump() if hasattr(p, 'model_dump') else p.dict() for p in req.points]
    depot_data = {
        "dc_code": req.dc_code,
        "name": req.depot_name or "中心仓",
        "lng": req.depot_lng,
        "lat": req.depot_lat,
        "address": req.depot_address,
    }
    
    snapshot = {
        "stores": stores_data,
        "depot": depot_data,
        "clustering_data": {
            "points": stores_data,
            "clusters": [],
            "algorithm": req.algorithm_configs.get("clustering_algorithm", "kmeans"),
            "k": req.algorithm_configs.get("clustering_k", 6),
            "minZoneSize": req.algorithm_configs.get("minZoneSize", 5),
            "maxZoneSize": req.algorithm_configs.get("maxZoneSize", 30),
        },
        "schedule_data": {
            "points": stores_data,
            "schedule_results": [],
            "daily_stats": {},
        },
        "routing_data": {
            "points": stores_data,
            "routes": [],
            "trucks": req.algorithm_configs.get("trucks", []),
            "route_metrics": {},
        },
        "algorithm_configs": req.algorithm_configs or {},
    }

    # 2. 判断初始阶段（若包含排班信息则直接初始化为 SCHEDULED，若包含店群信息则初始化为 CLUSTERED）
    has_schedule = any(s.get("delivery_days_str") or s.get("schedule_day") for s in stores_data)
    has_cluster = any(s.get("cluster_id") is not None for s in stores_data)
    
    initial_stage = "INIT"
    v1_name = "V1 - 初始规划范围创建"
    v1_summary = f"初始创建规划画布，载入 {len(stores_data)} 家门店与起点配置"
    
    if has_schedule:
        initial_stage = "SCHEDULED"
        v1_name = "V1 - 初始导入数据(含排班)"
        v1_summary = f"初始创建规划画布，载入 {len(stores_data)} 家门店（包含作业日排班）与起点配置"
    elif has_cluster:
        initial_stage = "CLUSTERED"
        v1_name = "V1 - 初始导入数据(含店群)"
        v1_summary = f"初始创建规划画布，载入 {len(stores_data)} 家门店（包含店群划分）与起点配置"

    new_canvas = DBCanvas(
        canvas_id=canvas_uuid,
        name=req.name,
        dc_code=req.dc_code,
        depot_name=req.depot_name,
        depot_lng=req.depot_lng,
        depot_lat=req.depot_lat,
        depot_address=req.depot_address,
        description=req.description,
        stage=initial_stage,
        is_active=True,
    )
    db.add(new_canvas)
    db.flush()

    # 3. 创建初始 V1 版本
    v1_version = DBCanvasVersion(
        canvas_id=canvas_uuid,
        version_number=1,
        version_name=v1_name,
        change_summary=v1_summary,
        parent_version_id=None,
        stage=initial_stage,
        snapshot_data=json.dumps(snapshot, ensure_ascii=False),
    )
    db.add(v1_version)
    db.flush()

    new_canvas.current_version_id = v1_version.id
    db.commit()
    db.refresh(new_canvas)
    db.refresh(v1_version)

    return CanvasDetailResponse(
        id=new_canvas.id,
        canvas_id=new_canvas.canvas_id,
        name=new_canvas.name,
        dc_code=new_canvas.dc_code,
        depot_name=new_canvas.depot_name,
        depot_lng=new_canvas.depot_lng,
        depot_lat=new_canvas.depot_lat,
        depot_address=new_canvas.depot_address,
        description=new_canvas.description,
        stage=new_canvas.stage,
        current_version_id=new_canvas.current_version_id,
        current_version_number=1,
        version_count=1,
        current_version=CanvasVersionResponse(
            id=v1_version.id,
            canvas_id=v1_version.canvas_id,
            version_number=v1_version.version_number,
            version_name=v1_version.version_name,
            change_summary=v1_version.change_summary,
            parent_version_id=v1_version.parent_version_id,
            stage=v1_version.stage,
            snapshot_data=snapshot,
            created_at=v1_version.created_at,
        ),
        created_at=new_canvas.created_at,
        updated_at=new_canvas.updated_at,
    )


@router.get("", response_model=List[CanvasSummaryResponse], summary="获取画布列表")
def list_canvases(
    keyword: Optional[str] = None,
    dc_code: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(DBCanvas).filter(DBCanvas.is_active == True)
    if keyword:
        query = query.filter(
            (DBCanvas.name.ilike(f"%{keyword}%")) |
            (DBCanvas.depot_name.ilike(f"%{keyword}%")) |
            (DBCanvas.dc_code.ilike(f"%{keyword}%"))
        )
    if dc_code:
        query = query.filter(DBCanvas.dc_code == dc_code)

    canvases = query.order_by(desc(DBCanvas.updated_at)).all()
    results = []

    for c in canvases:
        # 查询版本数
        v_count = db.query(func.count(DBCanvasVersion.id)).filter(DBCanvasVersion.canvas_id == c.canvas_id).scalar() or 1
        
        # 获取当前版本或最新版本
        cur_v = None
        if c.current_version_id:
            cur_v = db.query(DBCanvasVersion).filter(DBCanvasVersion.id == c.current_version_id).first()
        if not cur_v:
            cur_v = db.query(DBCanvasVersion).filter(DBCanvasVersion.canvas_id == c.canvas_id).order_by(desc(DBCanvasVersion.version_number)).first()

        cur_v_num = cur_v.version_number if cur_v else 1
        store_count = 0
        total_loads = 0
        route_count = 0
        total_distance = 0.0
        cluster_count = 0

        if cur_v and cur_v.snapshot_data:
            try:
                snap = json.loads(cur_v.snapshot_data) if isinstance(cur_v.snapshot_data, str) else cur_v.snapshot_data
                stores_list = snap.get("stores", [])
                store_count = len(stores_list)

                def get_store_weekly_load(s):
                    freq = s.get("frequency")
                    if not freq:
                        days_str = s.get("delivery_days_str") or s.get("schedule_day") or ""
                        if days_str:
                            freq = len([d for d in str(days_str).split(",") if d.strip()])
                    try:
                        freq_val = max(1, int(freq or 1))
                    except Exception:
                        freq_val = 1
                    load_val = float(s.get("avg_loads", s.get("demand", s.get("weight", 10.0))) or 10.0)
                    return load_val * freq_val

                total_loads = round(sum(get_store_weekly_load(s) for s in stores_list))
                
                # 兼容解析店群数据
                clust_data = snap.get("clustering_data") or snap.get("clustering_result") or {}
                if isinstance(clust_data, dict):
                    cluster_count = len(clust_data.get("clusters", []))
                
                # 兼容解析路线规划数据 (嵌套 routing_data 或顶层 daily_results / routes)
                routing_data = snap.get("routing_data") or {}
                daily_res = (routing_data.get("daily_results") if isinstance(routing_data, dict) else None) or snap.get("daily_results", {})

                if daily_res and isinstance(daily_res, dict):
                    for day_k, day_v in daily_res.items():
                        if isinstance(day_v, dict):
                            r_list = day_v.get("routes", [])
                            route_count += len(r_list)
                            for r in r_list:
                                total_distance += float(r.get("distance") or r.get("distance_km") or 0.0)

                # 若 daily_results 未解析到路线，尝试从 direct routes 解析
                if route_count == 0:
                    r_list = (routing_data.get("routes") if isinstance(routing_data, dict) else None) or snap.get("routes", [])
                    if r_list and isinstance(r_list, list):
                        route_count = len(r_list)
                        for r in r_list:
                            total_distance += float(r.get("distance") or r.get("distance_km") or 0.0)

                total_distance = round(total_distance, 1)
            except Exception:
                pass

        results.append(
            CanvasSummaryResponse(
                id=c.id,
                canvas_id=c.canvas_id,
                name=c.name,
                dc_code=c.dc_code,
                depot_name=c.depot_name,
                depot_lng=c.depot_lng,
                depot_lat=c.depot_lat,
                depot_address=c.depot_address,
                description=c.description,
                stage=c.stage or (cur_v.stage if cur_v else "INIT"),
                current_version_id=c.current_version_id or (cur_v.id if cur_v else None),
                current_version_number=cur_v_num,
                version_count=v_count,
                store_count=store_count,
                total_loads=total_loads,
                route_count=route_count,
                total_distance=total_distance,
                cluster_count=cluster_count,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )

    return results


@router.get("/{canvas_id}", response_model=CanvasDetailResponse, summary="获取画布详情及当前工作快照")
def get_canvas_detail(canvas_id: str, db: Session = Depends(get_db)):
    canvas = db.query(DBCanvas).filter(DBCanvas.canvas_id == canvas_id, DBCanvas.is_active == True).first()
    if not canvas:
        raise HTTPException(status_code=404, detail="画布不存在或已被删除")

    # 查询所有版本数
    v_count = db.query(func.count(DBCanvasVersion.id)).filter(DBCanvasVersion.canvas_id == canvas_id).scalar() or 1

    # 获取当前版本
    cur_v = None
    if canvas.current_version_id:
        cur_v = db.query(DBCanvasVersion).filter(DBCanvasVersion.id == canvas.current_version_id).first()
    if not cur_v:
        cur_v = db.query(DBCanvasVersion).filter(DBCanvasVersion.canvas_id == canvas_id).order_by(desc(DBCanvasVersion.version_number)).first()

    if not cur_v:
        raise HTTPException(status_code=404, detail="画布版本数据损坏")

    cur_v_resp = CanvasVersionResponse(
        id=cur_v.id,
        canvas_id=cur_v.canvas_id,
        version_number=cur_v.version_number,
        version_name=cur_v.version_name,
        change_summary=cur_v.change_summary,
        parent_version_id=cur_v.parent_version_id,
        stage=cur_v.stage,
        snapshot_data=_parse_snapshot(cur_v.snapshot_data),
        created_at=cur_v.created_at,
    )

    return CanvasDetailResponse(
        id=canvas.id,
        canvas_id=canvas.canvas_id,
        name=canvas.name,
        dc_code=canvas.dc_code,
        depot_name=canvas.depot_name,
        depot_lng=canvas.depot_lng,
        depot_lat=canvas.depot_lat,
        depot_address=canvas.depot_address,
        description=canvas.description,
        stage=canvas.stage or cur_v.stage,
        current_version_id=cur_v.id,
        current_version_number=cur_v.version_number,
        version_count=v_count,
        current_version=cur_v_resp,
        created_at=canvas.created_at,
        updated_at=canvas.updated_at,
    )


@router.put("/{canvas_id}", response_model=CanvasSummaryResponse, summary="修改画布基础信息")
def update_canvas(canvas_id: str, req: CanvasUpdate, db: Session = Depends(get_db)):
    canvas = db.query(DBCanvas).filter(DBCanvas.canvas_id == canvas_id, DBCanvas.is_active == True).first()
    if not canvas:
        raise HTTPException(status_code=404, detail="画布不存在")

    if req.name is not None:
        canvas.name = req.name
    if req.dc_code is not None:
        canvas.dc_code = req.dc_code
    if req.depot_name is not None:
        canvas.depot_name = req.depot_name
    if req.depot_lng is not None:
        canvas.depot_lng = req.depot_lng
    if req.depot_lat is not None:
        canvas.depot_lat = req.depot_lat
    if req.depot_address is not None:
        canvas.depot_address = req.depot_address
    if req.description is not None:
        canvas.description = req.description
    if req.stage is not None:
        canvas.stage = req.stage

    db.commit()
    db.refresh(canvas)

    v_count = db.query(func.count(DBCanvasVersion.id)).filter(DBCanvasVersion.canvas_id == canvas_id).scalar() or 1
    return CanvasSummaryResponse(
        id=canvas.id,
        canvas_id=canvas.canvas_id,
        name=canvas.name,
        dc_code=canvas.dc_code,
        depot_name=canvas.depot_name,
        depot_lng=canvas.depot_lng,
        depot_lat=canvas.depot_lat,
        depot_address=canvas.depot_address,
        description=canvas.description,
        stage=canvas.stage,
        current_version_id=canvas.current_version_id,
        version_count=v_count,
        created_at=canvas.created_at,
        updated_at=canvas.updated_at,
    )


@router.delete("/{canvas_id}", summary="删除画布")
def delete_canvas(canvas_id: str, db: Session = Depends(get_db)):
    canvas = db.query(DBCanvas).filter(DBCanvas.canvas_id == canvas_id).first()
    if not canvas:
        raise HTTPException(status_code=404, detail="画布不存在")

    # 级联删除版本与画布
    db.query(DBCanvasVersion).filter(DBCanvasVersion.canvas_id == canvas_id).delete()
    db.delete(canvas)
    db.commit()
    return {"message": "画布及所有历史版本已成功删除"}


@router.get("/{canvas_id}/versions", response_model=List[CanvasVersionResponse], summary="获取画布历史版本列表")
def list_canvas_versions(canvas_id: str, db: Session = Depends(get_db)):
    versions = db.query(DBCanvasVersion).filter(
        DBCanvasVersion.canvas_id == canvas_id
    ).order_by(desc(DBCanvasVersion.version_number)).all()

    return [
        CanvasVersionResponse(
            id=v.id,
            canvas_id=v.canvas_id,
            version_number=v.version_number,
            version_name=v.version_name,
            change_summary=v.change_summary,
            parent_version_id=v.parent_version_id,
            stage=v.stage,
            snapshot_data=_parse_snapshot(v.snapshot_data),
            created_at=v.created_at,
        )
        for v in versions
    ]


@router.get("/{canvas_id}/versions/{version_id}", response_model=CanvasVersionResponse, summary="获取指定版本快照")
def get_canvas_version(canvas_id: str, version_id: int, db: Session = Depends(get_db)):
    version = db.query(DBCanvasVersion).filter(
        DBCanvasVersion.id == version_id,
        DBCanvasVersion.canvas_id == canvas_id
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="指定版本不存在")

    return CanvasVersionResponse(
        id=version.id,
        canvas_id=version.canvas_id,
        version_number=version.version_number,
        version_name=version.version_name,
        change_summary=version.change_summary,
        parent_version_id=version.parent_version_id,
        stage=version.stage,
        snapshot_data=_parse_snapshot(version.snapshot_data),
        created_at=version.created_at,
    )


@router.post("/{canvas_id}/versions", response_model=CanvasVersionResponse, summary="在画布中基于上一版本保存新版本 (增量演进)")
def create_canvas_version(canvas_id: str, req: CanvasVersionCreate, db: Session = Depends(get_db)):
    canvas = db.query(DBCanvas).filter(DBCanvas.canvas_id == canvas_id, DBCanvas.is_active == True).first()
    if not canvas:
        raise HTTPException(status_code=404, detail="画布不存在")

    # 查询当前最大版本号
    max_v = db.query(func.max(DBCanvasVersion.version_number)).filter(DBCanvasVersion.canvas_id == canvas_id).scalar() or 0
    next_v_num = max_v + 1

    stage = req.stage or canvas.stage or "CLUSTERED"
    v_name = req.version_name or f"V{next_v_num} - {req.change_summary or '规划演进更新'}"

    # 保存新版本
    new_version = DBCanvasVersion(
        canvas_id=canvas_id,
        version_number=next_v_num,
        version_name=v_name,
        change_summary=req.change_summary or f"版本 V{next_v_num} 演进保存",
        parent_version_id=req.parent_version_id or canvas.current_version_id,
        stage=stage,
        snapshot_data=json.dumps(req.snapshot_data, ensure_ascii=False),
    )
    db.add(new_version)
    db.flush()

    # 更新画布的主版本指向与阶段
    canvas.current_version_id = new_version.id
    canvas.stage = stage
    canvas.updated_at = func.now()
    db.commit()
    db.refresh(new_version)

    return CanvasVersionResponse(
        id=new_version.id,
        canvas_id=new_version.canvas_id,
        version_number=new_version.version_number,
        version_name=new_version.version_name,
        change_summary=new_version.change_summary,
        parent_version_id=new_version.parent_version_id,
        stage=new_version.stage,
        snapshot_data=_parse_snapshot(new_version.snapshot_data),
        created_at=new_version.created_at,
    )


@router.post("/{canvas_id}/rollback/{version_id}", response_model=CanvasDetailResponse, summary="回滚/切换当前工作版本至历史指定版本")
def rollback_canvas_version(canvas_id: str, version_id: int, db: Session = Depends(get_db)):
    canvas = db.query(DBCanvas).filter(DBCanvas.canvas_id == canvas_id, DBCanvas.is_active == True).first()
    if not canvas:
        raise HTTPException(status_code=404, detail="画布不存在")

    target_v = db.query(DBCanvasVersion).filter(
        DBCanvasVersion.id == version_id,
        DBCanvasVersion.canvas_id == canvas_id
    ).first()
    if not target_v:
        raise HTTPException(status_code=404, detail="目标回滚版本不存在")

    canvas.current_version_id = target_v.id
    canvas.stage = target_v.stage
    canvas.updated_at = func.now()
    db.commit()
    db.refresh(canvas)

    v_count = db.query(func.count(DBCanvasVersion.id)).filter(DBCanvasVersion.canvas_id == canvas_id).scalar() or 1

    return CanvasDetailResponse(
        id=canvas.id,
        canvas_id=canvas.canvas_id,
        name=canvas.name,
        dc_code=canvas.dc_code,
        depot_name=canvas.depot_name,
        depot_lng=canvas.depot_lng,
        depot_lat=canvas.depot_lat,
        depot_address=canvas.depot_address,
        description=canvas.description,
        stage=canvas.stage,
        current_version_id=target_v.id,
        current_version_number=target_v.version_number,
        version_count=v_count,
        current_version=CanvasVersionResponse(
            id=target_v.id,
            canvas_id=target_v.canvas_id,
            version_number=target_v.version_number,
            version_name=target_v.version_name,
            change_summary=target_v.change_summary,
            parent_version_id=target_v.parent_version_id,
            stage=target_v.stage,
            snapshot_data=_parse_snapshot(target_v.snapshot_data),
            created_at=target_v.created_at,
        ),
        created_at=canvas.created_at,
        updated_at=canvas.updated_at,
    )


@router.post("/{canvas_id}/clone", response_model=CanvasDetailResponse, summary="克隆画布 (创建规划分支)")
def clone_canvas(canvas_id: str, new_name: Optional[str] = None, db: Session = Depends(get_db)):
    source_canvas = db.query(DBCanvas).filter(DBCanvas.canvas_id == canvas_id, DBCanvas.is_active == True).first()
    if not source_canvas:
        raise HTTPException(status_code=404, detail="源画布不存在")

    # 获取源画布最新快照
    cur_v = None
    if source_canvas.current_version_id:
        cur_v = db.query(DBCanvasVersion).filter(DBCanvasVersion.id == source_canvas.current_version_id).first()
    if not cur_v:
        cur_v = db.query(DBCanvasVersion).filter(DBCanvasVersion.canvas_id == canvas_id).order_by(desc(DBCanvasVersion.version_number)).first()

    if not cur_v:
        raise HTTPException(status_code=400, detail="源画布无有效版本数据")

    new_uuid = f"canvas_{uuid.uuid4().hex[:12]}"
    cloned_name = new_name or f"{source_canvas.name} (副本)"

    new_canvas = DBCanvas(
        canvas_id=new_uuid,
        name=cloned_name,
        dc_code=source_canvas.dc_code,
        depot_name=source_canvas.depot_name,
        depot_lng=source_canvas.depot_lng,
        depot_lat=source_canvas.depot_lat,
        depot_address=source_canvas.depot_address,
        description=f"从「{source_canvas.name}」({cur_v.version_name or f'V{cur_v.version_number}'}) 克隆创建的分支规划",
        stage=cur_v.stage,
        is_active=True,
    )
    db.add(new_canvas)
    db.flush()

    # 创建新画布的 V1 版本
    v1_version = DBCanvasVersion(
        canvas_id=new_uuid,
        version_number=1,
        version_name=f"V1 - 克隆自 {source_canvas.name}",
        change_summary=f"从画布「{source_canvas.name}」的版本 V{cur_v.version_number} 克隆分支",
        parent_version_id=None,
        stage=cur_v.stage,
        snapshot_data=cur_v.snapshot_data,
    )
    db.add(v1_version)
    db.flush()

    new_canvas.current_version_id = v1_version.id
    db.commit()
    db.refresh(new_canvas)
    db.refresh(v1_version)

    return CanvasDetailResponse(
        id=new_canvas.id,
        canvas_id=new_canvas.canvas_id,
        name=new_canvas.name,
        dc_code=new_canvas.dc_code,
        depot_name=new_canvas.depot_name,
        depot_lng=new_canvas.depot_lng,
        depot_lat=new_canvas.depot_lat,
        depot_address=new_canvas.depot_address,
        description=new_canvas.description,
        stage=new_canvas.stage,
        current_version_id=v1_version.id,
        current_version_number=1,
        version_count=1,
        current_version=CanvasVersionResponse(
            id=v1_version.id,
            canvas_id=v1_version.canvas_id,
            version_number=v1_version.version_number,
            version_name=v1_version.version_name,
            change_summary=v1_version.change_summary,
            parent_version_id=v1_version.parent_version_id,
            stage=v1_version.stage,
            snapshot_data=_parse_snapshot(v1_version.snapshot_data),
            created_at=v1_version.created_at,
        ),
        created_at=new_canvas.created_at,
        updated_at=new_canvas.updated_at,
    )
