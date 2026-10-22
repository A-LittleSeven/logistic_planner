from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.db.database import Base

class DBStore(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    shop_code = Column(String, unique=True, index=True) # 门店编号
    name = Column(String, index=True)                  # 门店名称
    dept_id = Column(String, nullable=True)            # 部门ID
    district = Column(String, nullable=True)           # 行政区划
    warzone = Column(String, nullable=True)            # 战区
    longitude = Column(Float)                          # 经度 (store_lon)
    latitude = Column(Float)                           # 纬度 (store_lat)
    avg_loads = Column(Float, default=0.0)             # 门店箱数 / 需求量
    frequency = Column(Integer, default=1)             # 配送频次 (周配送次数)
    store_freq_remains = Column(Integer, nullable=True)# 门店剩余频次
    is_homepot = Column(Integer, default=1)            # 是否本埠门店 (1:本埠, 0:外埠)
    store_is_need_dist = Column(Boolean, default=True) # 门店是否需要配送
    service_time = Column(Float, default=0.5)         # 门店卸货服务时间(小时)
    available_truck = Column(String, nullable=True)    # 可配送车型 (以逗号分隔或JSON字符串)
    sdist_warehouse = Column(Float, nullable=True)     # 门店距离仓库距离(km)
    
    # 仓库相关信息
    dc_code = Column(String, nullable=True)            # 仓库编码
    warehouse_name = Column(String, nullable=True)     # 仓库名称 / 归属仓库
    warehouse_lon = Column(Float, nullable=True)       # 仓库经度
    warehouse_lat = Column(Float, nullable=True)       # 仓库纬度
    
    # 门店簇中心信息 (选址/聚类衍生)
    cluster_center_id = Column(Integer, nullable=True) # 聚类中心id
    cluster_center_lon = Column(Float, nullable=True)  # 区域中心经度
    cluster_center_lat = Column(Float, nullable=True)  # 区域中心纬度
    cdist_warehouse = Column(Float, nullable=True)     # 聚类中心距离仓库距离
    
    address = Column(String, nullable=True)            # 详细地址
    is_active = Column(Boolean, default=True)          # 启用状态
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DBVehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_code = Column(String, unique=True, index=True)
    name = Column(String)
    capacity_weight = Column(Float) # 载重
    capacity_volume = Column(Float) # 体积
    cost_per_km = Column(Float) # 成本
    max_distance = Column(Float, default=500.0)
    available_count = Column(Integer, default=10)
    is_active = Column(Boolean, default=True)


class DBDepot(Base):
    __tablename__ = "depots"

    id = Column(Integer, primary_key=True, index=True)
    dc_code = Column(String, unique=True, index=True) # 起点/DC编码
    name = Column(String, index=True)                # 起点/中心仓名称
    longitude = Column(Float)                        # 经度
    latitude = Column(Float)                         # 纬度
    address = Column(String, nullable=True)          # 详细地址
    capacity = Column(Float, nullable=True)          # 日最大吞吐/装载能力
    contact_person = Column(String, nullable=True)   # 联系人
    contact_phone = Column(String, nullable=True)    # 联系电话
    is_default = Column(Boolean, default=False)      # 是否默认中心仓
    is_active = Column(Boolean, default=True)        # 启用状态
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DBTaskHistory(Base):
    __tablename__ = "task_histories"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True)
    task_type = Column(String, index=True) # "ROUTING", "GLOBAL_ROUTING", "CLUSTERING", "CLUSTER_SCHEDULE"
    save_type = Column(String, default="AUTO", index=True) # "MANUAL" (用户手动保存), "AUTO" (算法自动运行)
    status = Column(String, default="PENDING") # PENDING, RUNNING, SUCCESS, FAILED
    parameters = Column(Text, nullable=True) # JSON string of inputs
    result = Column(Text, nullable=True) # JSON string of outputs
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DBSystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String, unique=True, index=True, default="amap_config")
    amap_key = Column(String, nullable=True)             # 高德 Web端 Key
    amap_secret = Column(String, nullable=True)          # 高德安全密钥
    amap_secret_md5 = Column(String, nullable=True)      # 高德安全密钥 MD5 加密值
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class DBCanvas(Base):
    __tablename__ = "canvases"

    id = Column(Integer, primary_key=True, index=True)
    canvas_id = Column(String, unique=True, index=True)      # 业务UUID，例如 canvas_abc123
    name = Column(String, index=True)                         # 画布名称，例如 "南宁仓库2026Q3配送规划"
    dc_code = Column(String, nullable=True, index=True)       # 关联仓库编码
    depot_name = Column(String, nullable=True)                # 仓库名称
    depot_lng = Column(Float, nullable=True)                  # 仓库经度
    depot_lat = Column(Float, nullable=True)                  # 仓库纬度
    depot_address = Column(String, nullable=True)             # 仓库物理地址
    description = Column(Text, nullable=True)                 # 画布描述/备注
    stage = Column(String, default="INIT")                    # 当前规划阶段: INIT, CLUSTERED, SCHEDULED, ROUTED, FINALIZED
    current_version_id = Column(Integer, nullable=True)       # 当前激活的版本ID
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class DBCanvasVersion(Base):
    __tablename__ = "canvas_versions"

    id = Column(Integer, primary_key=True, index=True)
    canvas_id = Column(String, index=True)                    # 对应 DBCanvas.canvas_id
    version_number = Column(Integer, default=1)               # 版本号 (1, 2, 3, 4...)
    version_name = Column(String, nullable=True)              # 版本名称，如 "V1-初始导入", "V2-智能店群划分"
    change_summary = Column(Text, nullable=True)              # 变更摘要说明
    parent_version_id = Column(Integer, nullable=True)        # 基于哪一个版本演进修改
    stage = Column(String, default="INIT")                    # 该版本所处阶段
    snapshot_data = Column(Text, nullable=False)              # 完整快照数据 JSON (门店池、店群、排班、路线、算法参数等)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

