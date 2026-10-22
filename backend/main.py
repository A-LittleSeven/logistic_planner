"""FastAPI 应用入口。

启动:
    cd backend
    .venv/bin/uvicorn main:app --reload --port 8000

文档: http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.utils.config import settings
from app.api import (
    location_router,
    routing_router,
    clustering_router,
    store_router,
    vehicle_router,
    history_router,
    depot_router,
    system_router,
    canvas_router,
)
from app.db.database import Base, engine

# 自动创建本地 SQLite 数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="物流规划调度系统 API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"name": "物流规划调度系统 API", "docs": "/docs", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok", "distance_provider": settings.distance_provider}


app.include_router(canvas_router.router, prefix="/api/canvas", tags=["规划画布"])
app.include_router(location_router.router, prefix="/api/location", tags=["物流选址"])
app.include_router(routing_router.router, prefix="/api/routing", tags=["路线规划"])
app.include_router(clustering_router.router, prefix="/api/clustering", tags=["店群规划"])
app.include_router(store_router.router, prefix="/api/store", tags=["门店管理"])
app.include_router(vehicle_router.router, prefix="/api/vehicle", tags=["车辆管理"])
app.include_router(depot_router.router, prefix="/api/depot", tags=["起点管理"])
app.include_router(history_router.router, prefix="/api/history", tags=["历史记录"])
app.include_router(system_router.router, prefix="/api/system", tags=["系统管理"])



