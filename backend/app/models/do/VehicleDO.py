"""车辆/卡车算法领域模型对象 (Vehicle DO / BaseTruck)。

专职用于排班调度、装载运筹计算与路径规划的运行时实体。
维护单车装载状态、运行轨迹、动态容量限制与车型自动升降级机制。
"""
import contextvars
import threading
from typing import Optional, Type, List, Set, Dict, Any
from pydantic import BaseModel, Field, create_model
from app.utils.logger import LogUtil

logger = LogUtil.get_logger(__name__)

# 协程/上下文局部 ID 计数器，消除多任务并发规划时的全局竞态
_truck_id_counter_ctx: contextvars.ContextVar[int] = contextvars.ContextVar('truck_id_counter', default=1)
_allocator_lock = threading.Lock()

# 车型别名映射表，集中管理便于维护
TRUCK_ALIAS_MAP: Dict[str, Type['VehicleNode']] = {}


def _register_aliases(truck_cls: Type['VehicleNode'], aliases: List[str]):
    """注册车型别名到全局映射表"""
    for alias in aliases:
        TRUCK_ALIAS_MAP[alias.strip().upper().replace(' ', '')] = truck_cls


class TruckIdAllocator:
    """并发安全的车辆 ID 分配器。优先使用上下文变量隔离，消除多请求/任务并发冲突。"""
    _global_counter: int = 1

    @classmethod
    def next_id(cls) -> int:
        try:
            val = _truck_id_counter_ctx.get()
            _truck_id_counter_ctx.set(val + 1)
            return val
        except Exception:
            with _allocator_lock:
                tid = cls._global_counter
                cls._global_counter += 1
                return tid

    @classmethod
    def reset(cls, start: int = 1):
        _truck_id_counter_ctx.set(start)
        with _allocator_lock:
            cls._global_counter = start


class VehicleNode(BaseModel):
    """
    运力/车辆算法领域模型（排班调度与装载计算运行时实体）。
    维护单车装载状态、运行轨迹与动态容量限制。
    """
    truck_id: Optional[int] = None
    vehicle_code: Optional[str] = Field(None, title="车型编码")
    name: Optional[str] = Field(None, title="车型名称")
    cost_per_km: Optional[float] = Field(None, title="每公里运输成本")
    max_capacity: int = Field(..., title="车辆最大载重")
    soft_capacity: int = Field(20, title="车辆软载重")
    truck_current_load: float = Field(0, title="车辆当前载重")
    truck_distance_overall: float = Field(0, title="车辆总距离")
    truck_frequency_max: int = Field(0, title="车辆配送路径中最大门店配送频次")
    is_homepot: Optional[int] = Field(None, title="是否本埠车辆")
    truck_trace: list = Field(default_factory=list, title="车辆轨迹")
    truck_is_borrow: bool = Field(False, title="车辆是否需要跨区域配送")
    max_distance: float = Field(..., title="车辆可配送最大距离")
    truck_price: Optional[float] = Field(None, title="车辆运费")

    _dynamic_truck_classes: List[Type['VehicleNode']] = []

    def __init__(self, **kwargs):
        allocate_truck_id = kwargs.pop('_allocate_truck_id', True)
        super().__init__(**kwargs)
        if allocate_truck_id and self.truck_id is None:
            self.truck_id = TruckIdAllocator.next_id()

    def _add_load(self, load: float) -> bool:
        if self.truck_current_load + load > self.max_capacity + self.soft_capacity:
            return False
        self.truck_current_load += load
        return True

    def calc_truck_distance(self) -> float:
        if not self.truck_trace:
            return 0
        distance = self.truck_trace[0].sdist_warehouse
        for i in range(len(self.truck_trace) - 1):
            distance += self.truck_trace[i].calc_haversine_distance(self.truck_trace[i + 1])
        distance += self.truck_trace[-1].sdist_warehouse
        return distance

    def add_trace(self, store_node) -> bool:
        if self._add_load(store_node.avg_loads):
            self.truck_trace.append(store_node)
            return True
        return False

    def calc_max_frequency(self):
        self.truck_frequency_max = max(store.frequency for store in self.truck_trace)

    @classmethod
    def set_supported_truck_classes(cls, classes: List[Type['VehicleNode']]):
        """设置全局/上下文动态启用的车型列表"""
        cls._dynamic_truck_classes = list(classes)

    @classmethod
    def supported_truck_classes(cls):
        """当前系统支持的车型。若配置了动态车型则优先采用，否则回退至内置标准车型"""
        if cls._dynamic_truck_classes:
            return tuple(cls._dynamic_truck_classes)
        return Truck420, Truck270, Truck960, Express

    @staticmethod
    def get_truck_field_default(truck_cls: Type['VehicleNode'], field_name: str):
        """获取车型字段默认值"""
        model_fields = getattr(truck_cls, 'model_fields', None)
        if model_fields and field_name in model_fields:
            return model_fields[field_name].default
        raise AttributeError(f"{truck_cls.__name__} 不存在字段 {field_name}")

    @classmethod
    def normalize_truck_cls(cls, truck_value):
        """将车型标识标准化为车型类"""
        if isinstance(truck_value, type) and issubclass(truck_value, VehicleNode):
            return truck_value
        if isinstance(truck_value, VehicleNode):
            return truck_value.__class__
        if truck_value is None:
            return None
        lookup_key = str(truck_value).strip().upper().replace(' ', '')
        if not lookup_key:
            return None

        # 1. 别名表匹配
        if lookup_key in TRUCK_ALIAS_MAP:
            return TRUCK_ALIAS_MAP[lookup_key]

        # 2. 启发式模糊模式匹配
        if '4.2' in lookup_key or '420' in lookup_key:
            return Truck420
        elif '2.7' in lookup_key or '270' in lookup_key or '依维柯' in lookup_key or '微卡' in lookup_key:
            return Truck270
        elif '9.6' in lookup_key or '960' in lookup_key or '重卡' in lookup_key or '大货车' in lookup_key:
            return Truck960
        elif '7.6' in lookup_key or '760' in lookup_key or '中型' in lookup_key:
            return Truck960
        elif '快递' in lookup_key or 'EXPRESS' in lookup_key:
            return Express

        return None

    @classmethod
    def resolve_store_allowed_truck_classes(cls, store) -> Set[Type['VehicleNode']]:
        """获取门店允许的车型列表；空列表表示不限制车型"""
        if not store.available_truck:
            return set(cls.supported_truck_classes())

        allowed_classes = set()
        invalid_values = []
        for truck_value in store.available_truck:
            if not truck_value:
                continue
            truck_cls = cls.normalize_truck_cls(truck_value)
            if truck_cls is None:
                invalid_values.append(truck_value)
                continue
            allowed_classes.add(truck_cls)

        if not allowed_classes:
            # 宽容容错：如果配置的车型均未直接识别，尝试模糊匹配或回退为全部可用车型
            logger.warning(
                f"门店 {getattr(store, 'shop_code', '')} 的 available_truck ({invalid_values}) 未能精准识别，已自动回退为全部车型"
            )
            return set(cls.supported_truck_classes())

        return allowed_classes

    def resolve_trace_allowed_truck_classes(self) -> Set[Type['VehicleNode']]:
        """获取当前整条路径允许的车型交集"""
        allowed_classes = set(self.supported_truck_classes())
        for store in self.truck_trace:
            allowed_classes &= self.resolve_store_allowed_truck_classes(store)
        return allowed_classes

    def _select_target_truck_cls(self, store, allow_overload: bool = False):
        """
        根据门店车型限制和载重需求，选择目标车型类。
        返回 (target_truck_cls, allowed_classes_or_None)
        """
        required_load = self.truck_current_load + store.avg_loads
        target_truck_cls = self.__class__
        allowed_classes = None

        if store.available_truck:
            allowed_classes = self.resolve_store_allowed_truck_classes(store)
            if self.truck_trace:
                allowed_classes &= self.resolve_trace_allowed_truck_classes()

            if not allowed_classes:
                raise ValueError(
                    f"门店 {store.shop_code} 与当前路径的车型限制无交集，无法安排车辆"
                )

            if self.__class__ not in allowed_classes:
                for truck_cls in self.supported_truck_classes():
                    if truck_cls not in allowed_classes:
                        continue
                    target_load_max = self.get_truck_field_default(truck_cls, 'max_capacity')
                    if allow_overload or required_load <= target_load_max or issubclass(truck_cls, Express):
                        target_truck_cls = truck_cls
                        break
                else:
                    max_allowed_cls = max(allowed_classes, key=lambda cls: self.get_truck_field_default(cls, 'max_capacity'))
                    logger.warning(
                        f"门店 {store.shop_code} 要求车型 {[c.__name__ for c in allowed_classes]} 且运量为 {required_load} 箱，"
                        f"已选择最大允许车型 {max_allowed_cls.__name__} 进行承载"
                    )
                    target_truck_cls = max_allowed_cls

        return target_truck_cls, allowed_classes

    def _log_truck_conversion(self, target_truck_cls, store, allowed_classes, required_load):
        """记录车型切换日志"""
        current_load_max = self.get_truck_field_default(self.__class__, 'max_capacity')
        target_load_max = self.get_truck_field_default(target_truck_cls, 'max_capacity')
        switch_direction = '降级' if target_load_max < current_load_max else '升级'

        switch_reasons = []
        if allowed_classes and self.__class__ not in allowed_classes:
            switch_reasons.append(
                f"门店车型限制为 {[cls.__name__ for cls in allowed_classes]}，当前车型 {self.__class__.__name__} 不可配送"
            )
        if required_load > current_load_max:
            switch_reasons.append(
                f"预计装载量 {required_load} 超过当前车型载重上限 {current_load_max}"
            )
        if not switch_reasons:
            switch_reasons.append("特殊门店触发定向车型切换")

        logger.info(
            f"🚚 车辆{switch_direction}: truck_id={self.truck_id}, 门店={store.shop_code}/{store.dept_id}, "
            f"{self.__class__.__name__} -> {target_truck_cls.__name__}, 当前载重={self.truck_current_load}, "
            f"门店载重={store.avg_loads}, 预计总载重={required_load}, 当前车型上限={current_load_max}, "
            f"目标车型上限={target_load_max}, available_truck={store.available_truck or '无限制'}, "
            f"原因={'；'.join(switch_reasons)}"
        )

    def convert_for_store(self, store, allow_overload: bool = False):
        """针对单个门店执行定向车型切换"""
        required_load = self.truck_current_load + store.avg_loads
        target_truck_cls, allowed_classes = self._select_target_truck_cls(store, allow_overload)
        # 转换车型记录 log
        if target_truck_cls is not self.__class__:
            self._log_truck_conversion(target_truck_cls, store, allowed_classes, required_load)

        return self.convert_to(target_truck_cls, allow_overload=allow_overload)

    def convert_to(self, target_truck_cls: Type['VehicleNode'], allow_overload: bool = False):
        """将当前卡车转换成目标车型，并保留当前运行状态"""
        if not issubclass(target_truck_cls, VehicleNode):
            raise TypeError("target_truck_cls 必须是 VehicleNode/BaseTruck 的子类")

        if isinstance(self, target_truck_cls):
            return self

        target_load_max = self.get_truck_field_default(target_truck_cls, 'max_capacity')
        if not allow_overload and self.truck_current_load > target_load_max and not issubclass(target_truck_cls, Express):
            raise ValueError(
                f"当前载重 {self.truck_current_load} 超过目标车型载重上限 {target_load_max}，无法降级"
            )

        new_truck = target_truck_cls(_allocate_truck_id=False)
        new_truck.truck_id = self.truck_id
        new_truck.truck_trace = list(self.truck_trace)
        new_truck.truck_current_load = self.truck_current_load
        new_truck.truck_distance_overall = self.calc_truck_distance() if self.truck_trace else 0
        new_truck.truck_frequency_max = self.truck_frequency_max
        new_truck.truck_is_borrow = self.truck_is_borrow
        new_truck.truck_price = self.truck_price
        return new_truck


# 向后兼容历史命名的别名映射
BaseTruck = VehicleNode


class Truck960(BaseTruck):
    """9.6m 厢式货车"""
    max_capacity: int = 800
    max_distance: float = 1500.0


class Truck420(BaseTruck):
    """新能源4.2m车型"""
    max_capacity: int = 230
    max_distance: float = 1000.0


class Truck420_1(BaseTruck):
    """新能源4.2m车型_宽体型"""
    max_capacity: int = 270
    max_distance: float = 1000.0


class Truck270(BaseTruck):
    """依维柯车型"""
    max_capacity: int = 80
    max_distance: float = 1000.0


class Express(BaseTruck):
    """快递/物流/零担/第三方物流"""
    max_capacity: int = 99999
    max_distance: float = 10000.0


# 注册车型别名（模块加载时执行一次）
_register_aliases(Truck270, ['TRUCK270', '270', '2.7', '2.7M', '2.7米', '2.7米厢车', '2.7米厢式货车', '2.7米货车', '依维柯', '小货车', '微卡'])
_register_aliases(Truck420, ['TRUCK420', '420', '4.2', '4.2M', '4.2米', '4.2米厢车', '4.2米厢式货车', '4.2米货车', '4.2米车', '4.2米箱车', '4.2米轻卡', '新能源4.2M', '新能源4.2米', '轻卡'])
_register_aliases(Truck420_1, ['TRUCK420_1', '420_1', '4.2宽体', '4.2米宽体', '4.2米宽体厢车'])
_register_aliases(Truck960, ['TRUCK960', '960', '9.6', '9.6M', '9.6米', '9.6米厢车', '9.6米厢式货车', '9.6米货车', '9.6米车', '重卡', '9.6米大货车', '重型货车', '7.6米', '7.6米中型货车', '7.6米货车', '7.6米厢车'])
_register_aliases(Express, ['EXPRESS', '快递', '快件', '快递物流', '物流', '第三方物流', '零担', '专线'])


# ==========================================
# 动态车型配置工厂与主数据加载器
# ==========================================

def create_vehicle_class(
    vehicle_code: str,
    name: str,
    capacity: int,
    max_distance: float = 1000.0,
    cost_per_km: Optional[float] = None,
    aliases: Optional[List[str]] = None,
) -> Type[VehicleNode]:
    """根据主数据或外部配置动态创建 VehicleNode 子类，并自动注册别名"""
    clean_code = str(vehicle_code).replace(".", "_").replace("-", "_").replace(" ", "_").upper()
    class_name = f"DynamicTruck_{clean_code}"

    # 使用 Pydantic create_model 规范定义动态派生模型
    dynamic_cls = create_model(
        class_name,
        __base__=BaseTruck,
        max_capacity=(int, int(capacity)),
        max_distance=(float, float(max_distance)),
        vehicle_code=(Optional[str], str(vehicle_code)),
        name=(Optional[str], str(name)),
        cost_per_km=(Optional[float], float(cost_per_km) if cost_per_km is not None else None),
    )
    dynamic_cls.__doc__ = f"动态配置车型: {name} (编码: {vehicle_code}, 载重: {capacity})"

    # 注册别名支持
    reg_aliases = [vehicle_code, name, clean_code]
    if aliases:
        reg_aliases.extend(aliases)
    _register_aliases(dynamic_cls, reg_aliases)
    return dynamic_cls


def load_fleet_classes(vehicles_data: Optional[List[Any]] = None) -> List[Type[VehicleNode]]:
    """
    根据给定的车型主数据（ORM 模型 DBVehicle、Pydantic DTO 或字典）动态构建排班可用车型池。
    按载重规模合理排序，并附带兜底的快递车型。
    若列表为空则回退返回内置静态车型池 (Truck420, Truck270, Truck960, Express)。
    """
    if not vehicles_data:
        return list(VehicleNode.supported_truck_classes())

    dynamic_classes: List[Type[VehicleNode]] = []
    for v in vehicles_data:
        if isinstance(v, dict):
            code = v.get("vehicle_code") or v.get("code") or "CUSTOM"
            name = v.get("name") or code
            cap = int(v.get("capacity_weight") or v.get("capacity") or 230)
            max_dist = float(v.get("max_distance") or 1000.0)
            cost = float(v.get("cost_per_km")) if v.get("cost_per_km") is not None else None
        else:
            code = getattr(v, "vehicle_code", None) or getattr(v, "code", "CUSTOM")
            name = getattr(v, "name", code)
            cap = int(getattr(v, "capacity_weight", None) or getattr(v, "capacity", 230))
            max_dist = float(getattr(v, "max_distance", 1000.0) or 1000.0)
            cost = float(getattr(v, "cost_per_km", None)) if getattr(v, "cost_per_km", None) is not None else None

        cls_obj = create_vehicle_class(
            vehicle_code=code,
            name=name,
            capacity=cap,
            max_distance=max_dist,
            cost_per_km=cost,
        )
        dynamic_classes.append(cls_obj)

    # 确保有 Express 兜底
    if not any(issubclass(c, Express) or c is Express for c in dynamic_classes):
        dynamic_classes.append(Express)

    # 按照载重升序排列
    dynamic_classes.sort(key=lambda c: VehicleNode.get_truck_field_default(c, 'max_capacity'))
    return dynamic_classes
