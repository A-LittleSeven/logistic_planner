"""基础主数据领域服务 (MasterDataService)。

统一管理门店 (Store)、中心仓/起点 (Depot)、车型运力 (Vehicle) 的数据访问、CRUD 操作及首次环境自动初始化与 CSV 播种。
"""
import os
import csv
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.db.models import DBStore, DBDepot, DBVehicle
from app.models.dto.StoreDTO import StoreCreate, StoreUpdate, BatchImportRequest
from app.models.dto.DepotDTO import DepotCreate, DepotUpdate
from app.models.dto.VehicleDTO import VehicleCreate, VehicleUpdate
from app.utils.logger import LogUtil

logger = LogUtil.get_logger(__name__)


class StoreService:
    """门店主数据业务服务"""

    @staticmethod
    def init_default_stores_from_csv(db: Session) -> int:
        """如果数据库为空，从根目录的 store_info_guangxi.csv 初始化基础门店数据"""
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        csv_path = os.path.join(base_dir, "store_info_guangxi.csv")
        if not os.path.exists(csv_path):
            return 0

        try:
            encodings = ["gbk", "utf-8-sig", "utf-8"]
            rows = None
            for enc in encodings:
                try:
                    with open(csv_path, "r", encoding=enc) as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)
                    break
                except Exception:
                    continue

            if not rows:
                return 0

            inserted_count = 0
            for r in rows:
                try:
                    store = DBStore(
                        shop_code=str(r.get("shop_code") or r.get("dept_id") or "").strip(),
                        name=str(r.get("shop_name") or r.get("name") or "").strip(),
                        dept_id=str(r.get("dept_id") or "").strip(),
                        district=str(r.get("district") or "").strip(),
                        warzone=str(r.get("warzone") or "").strip(),
                        longitude=float(r.get("longitude") or r.get("lng") or 0.0),
                        latitude=float(r.get("latitude") or r.get("lat") or 0.0),
                        avg_loads=float(r.get("avg_loads") or 0.0),
                        frequency=int(float(r.get("frequency") or 1)),
                        is_homepot=int(r.get("is_homepot") or 1),
                        service_time=float(r.get("dist_time") or 40) / 60.0
                        if r.get("dist_time")
                        else 0.65,
                        address=f"{r.get('city_name', '')}{r.get('district_sub', '')}",
                        available_truck=str(r.get("dis_way") or ""),
                        is_active=True,
                    )
                    if store.shop_code and store.longitude and store.latitude:
                        db.add(store)
                        inserted_count += 1
                except Exception:
                    continue
            db.commit()
            return inserted_count
        except Exception as e:
            logger.error(f"从 CSV 自动播种门店数据失败: {e}")
            return 0

    @classmethod
    def get_stores(
        cls,
        db: Session,
        district: Optional[str] = None,
        warehouse: Optional[str] = None,
        cluster_id: Optional[int] = None,
        is_homepot: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 1000,
    ) -> List[DBStore]:
        """获取门店列表支持多条件筛选"""
        query = db.query(DBStore)
        if district:
            query = query.filter(DBStore.district == district)
        if warehouse:
            query = query.filter(
                (DBStore.warehouse_name == warehouse) | (DBStore.dc_code == warehouse)
            )
        if cluster_id is not None:
            query = query.filter(DBStore.cluster_center_id == cluster_id)
        if is_homepot is not None:
            query = query.filter(DBStore.is_homepot == is_homepot)
        if search:
            s = f"%{search}%"
            query = query.filter(
                (DBStore.name.ilike(s))
                | (DBStore.shop_code.ilike(s))
                | (DBStore.district.ilike(s))
                | (DBStore.warehouse_name.ilike(s))
                | (DBStore.dc_code.ilike(s))
            )
        return query.offset(skip).limit(limit).all()

    @classmethod
    def create_store(cls, db: Session, store_in: StoreCreate) -> DBStore:
        """创建单家门店"""
        existing = db.query(DBStore).filter(DBStore.shop_code == store_in.shop_code).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"门店编号 {store_in.shop_code} 已存在")
        db_store = DBStore(**store_in.model_dump())
        db.add(db_store)
        db.commit()
        db.refresh(db_store)
        return db_store

    @classmethod
    def batch_import_stores(cls, db: Session, req: BatchImportRequest) -> Dict[str, Any]:
        """批量导入或覆盖门店"""
        if not req.stores:
            raise HTTPException(status_code=400, detail="导入门店列表不能为空")

        if req.mode == "overwrite":
            db.query(DBStore).delete()
            db.commit()

        inserted = 0
        updated = 0
        errors = []

        for item in req.stores:
            try:
                existing = db.query(DBStore).filter(DBStore.shop_code == item.shop_code).first()
                if existing:
                    for k, v in item.model_dump(exclude_unset=True).items():
                        setattr(existing, k, v)
                    updated += 1
                else:
                    db_store = DBStore(**item.model_dump())
                    db.add(db_store)
                    inserted += 1
            except Exception as e:
                errors.append(f"{item.shop_code}: {str(e)}")

        db.commit()
        return {
            "status": "success",
            "inserted": inserted,
            "updated": updated,
            "total": len(req.stores),
            "errors": errors,
        }

    @classmethod
    def update_store(cls, db: Session, store_id: int, store_in: StoreUpdate) -> DBStore:
        """更新门店信息"""
        db_store = db.query(DBStore).filter(DBStore.id == store_id).first()
        if not db_store:
            raise HTTPException(status_code=404, detail="门店不存在")
        update_data = store_in.model_dump(exclude_unset=True)
        for field, val in update_data.items():
            setattr(db_store, field, val)
        db.commit()
        db.refresh(db_store)
        return db_store

    @classmethod
    def delete_store(cls, db: Session, store_id: int) -> Dict[str, str]:
        """删除指定门店"""
        db_store = db.query(DBStore).filter(DBStore.id == store_id).first()
        if not db_store:
            raise HTTPException(status_code=404, detail="门店不存在")
        db.delete(db_store)
        db.commit()
        return {"status": "success", "message": f"门店 {store_id} 已删除"}

    @classmethod
    def clear_all_stores(cls, db: Session) -> Dict[str, str]:
        """清空全部门店"""
        db.query(DBStore).delete()
        db.commit()
        return {"status": "success", "message": "所有门店数据已清空"}


class DepotService:
    """中心仓/起点主数据业务服务"""

    @classmethod
    def get_depots(cls, db: Session, skip: int = 0, limit: int = 100) -> List[DBDepot]:
        """获取中心仓列表"""
        return db.query(DBDepot).offset(skip).limit(limit).all()

    @classmethod
    def init_default_depots(cls, db: Session) -> Dict[str, Any]:
        """初始化默认中心仓示例数据"""
        existing_count = db.query(DBDepot).count()
        if existing_count > 0:
            return {"status": "skipped", "message": f"已有 {existing_count} 个中心仓，跳过初始化"}
        samples = [
            DBDepot(
                dc_code="DC_NN_01",
                name="南宁中心仓",
                longitude=108.318344,
                latitude=22.846367,
                address="广西南宁市西乡塘区安吉大道物流产业园A区",
                capacity=50000.0,
                contact_person="张主管",
                contact_phone="13800000001",
                is_default=True,
                is_active=True,
            ),
            DBDepot(
                dc_code="DC_LZ_02",
                name="柳州分拨中心",
                longitude=109.402860,
                latitude=24.304495,
                address="广西柳州市柳南区柳邕路物流港",
                capacity=30000.0,
                contact_person="李主管",
                contact_phone="13800000002",
                is_default=False,
                is_active=True,
            ),
            DBDepot(
                dc_code="DC_GL_03",
                name="桂林分拔仓",
                longitude=110.299121,
                latitude=25.274215,
                address="广西桂林市象山区环城南路物流枢纽",
                capacity=20000.0,
                contact_person="王主管",
                contact_phone="13800000003",
                is_default=False,
                is_active=True,
            ),
        ]
        for d in samples:
            db.add(d)
        db.commit()
        return {"status": "success", "message": f"已初始化 {len(samples)} 个默认中心仓"}

    @classmethod
    def create_depot(cls, db: Session, depot_in: DepotCreate) -> DBDepot:
        """创建中心仓"""
        existing = db.query(DBDepot).filter(DBDepot.dc_code == depot_in.dc_code).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"DC编码 {depot_in.dc_code} 已存在")

        if depot_in.is_default:
            db.query(DBDepot).update({DBDepot.is_default: False})

        db_depot = DBDepot(**depot_in.model_dump())
        db.add(db_depot)
        db.commit()
        db.refresh(db_depot)
        return db_depot

    @classmethod
    def update_depot(cls, db: Session, depot_id: int, depot_in: DepotUpdate) -> DBDepot:
        """更新中心仓"""
        db_depot = db.query(DBDepot).filter(DBDepot.id == depot_id).first()
        if not db_depot:
            raise HTTPException(status_code=404, detail="起点/DC不存在")

        update_data = depot_in.model_dump(exclude_unset=True)
        if "dc_code" in update_data and update_data["dc_code"]:
            existing = (
                db.query(DBDepot)
                .filter(DBDepot.dc_code == update_data["dc_code"], DBDepot.id != depot_id)
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=400, detail=f"仓库编码 {update_data['dc_code']} 已被其他起点仓库占用"
                )

        if update_data.get("is_default") is True:
            db.query(DBDepot).filter(DBDepot.id != depot_id).update({DBDepot.is_default: False})

        for field, val in update_data.items():
            setattr(db_depot, field, val)
        db.commit()
        db.refresh(db_depot)
        return db_depot

    @classmethod
    def set_default_depot(cls, db: Session, depot_id: int) -> DBDepot:
        """设为默认中心仓"""
        db_depot = db.query(DBDepot).filter(DBDepot.id == depot_id).first()
        if not db_depot:
            raise HTTPException(status_code=404, detail="起点/DC不存在")

        db.query(DBDepot).update({DBDepot.is_default: False})
        db_depot.is_default = True
        db.commit()
        db.refresh(db_depot)
        return db_depot

    @classmethod
    def delete_depot(cls, db: Session, depot_id: int) -> Dict[str, str]:
        """删除中心仓"""
        db_depot = db.query(DBDepot).filter(DBDepot.id == depot_id).first()
        if not db_depot:
            raise HTTPException(status_code=404, detail="起点/DC不存在")
        db.delete(db_depot)
        db.commit()
        return {"status": "success", "message": f"起点 {depot_id} 已删除"}


class VehicleService:
    """车型运力主数据业务服务"""

    @classmethod
    def get_vehicles(cls, db: Session, skip: int = 0, limit: int = 100) -> List[DBVehicle]:
        """获取车型列表（若为空自动填充默认 3 种运力车型）"""
        vehicles = db.query(DBVehicle).offset(skip).limit(limit).all()
        if not vehicles and skip == 0:
            samples = [
                DBVehicle(
                    vehicle_code="V420",
                    name="新能源4.2米箱式货车",
                    capacity_weight=200.0,
                    capacity_volume=18.0,
                    cost_per_km=3.5,
                    max_distance=400.0,
                    available_count=8,
                ),
                DBVehicle(
                    vehicle_code="V680",
                    name="重型6.8米货车",
                    capacity_weight=450.0,
                    capacity_volume=35.0,
                    cost_per_km=5.2,
                    max_distance=600.0,
                    available_count=4,
                ),
                DBVehicle(
                    vehicle_code="V960",
                    name="干线9.6米货车",
                    capacity_weight=800.0,
                    capacity_volume=55.0,
                    cost_per_km=7.8,
                    max_distance=800.0,
                    available_count=2,
                ),
            ]
            for v in samples:
                db.add(v)
            db.commit()
            vehicles = db.query(DBVehicle).offset(skip).limit(limit).all()
        return vehicles

    @classmethod
    def create_vehicle(cls, db: Session, vehicle_in: VehicleCreate) -> DBVehicle:
        """创建新车型"""
        existing = (
            db.query(DBVehicle).filter(DBVehicle.vehicle_code == vehicle_in.vehicle_code).first()
        )
        if existing:
            raise HTTPException(
                status_code=400, detail=f"车型编号 {vehicle_in.vehicle_code} 已存在"
            )
        db_vehicle = DBVehicle(**vehicle_in.model_dump())
        db.add(db_vehicle)
        db.commit()
        db.refresh(db_vehicle)
        return db_vehicle

    @classmethod
    def update_vehicle(cls, db: Session, vehicle_id: int, vehicle_in: VehicleUpdate) -> DBVehicle:
        """更新车型"""
        db_vehicle = db.query(DBVehicle).filter(DBVehicle.id == vehicle_id).first()
        if not db_vehicle:
            raise HTTPException(status_code=404, detail="车型不存在")
        update_data = vehicle_in.model_dump(exclude_unset=True)
        for field, val in update_data.items():
            setattr(db_vehicle, field, val)
        db.commit()
        db.refresh(db_vehicle)
        return db_vehicle

    @classmethod
    def delete_vehicle(cls, db: Session, vehicle_id: int) -> Dict[str, str]:
        """删除车型"""
        db_vehicle = db.query(DBVehicle).filter(DBVehicle.id == vehicle_id).first()
        if not db_vehicle:
            raise HTTPException(status_code=404, detail="车型不存在")
        db.delete(db_vehicle)
        db.commit()
        return {"status": "success", "message": f"车型 {vehicle_id} 已删除"}
