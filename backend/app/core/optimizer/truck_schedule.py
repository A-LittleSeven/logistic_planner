from typing import List, Optional, Dict, Set, cast

from app.models.cluster import ClusterNode
from app.models.store import StoreNode
from app.models.truck import Truck420, BaseTruck
from app.core.utils.logutils import LogUtil
from app.core.utils.route_optimizer import RouteOptimizer

logger = LogUtil.get_logger(__name__)


class TruckSchedule(object):
    """
    物流运筹优化统一调度引擎
    """

    def __init__(self,
                 max_truck_capacity_rate: float = 0.92,
                 search_n_neighbor: int = 2,
                 simple_mode_thres: int = 2,
                 dist_thres: float = 0.9,
                 one_way_dist_max: int = 40,
                 detour_thres: float = 40):
        # 局部搜索邻居数量
        self.search_n_neighbor = search_n_neighbor
        # 直接规划模式阈值
        self.simple_mode_thres = simple_mode_thres
        # 路径优化判断(临近店距离阈值 && 临近店单程距离max)
        self.dist_thres: float = dist_thres
        self.one_way_dist_max: int = one_way_dist_max
        self.detour_thres: float = 100 if detour_thres is None else detour_thres
        # 卡车装载率设定
        self.max_truck_capacity_rate = max_truck_capacity_rate
        self.plan_trucks: List[BaseTruck] = []
        self._cluster_store_snapshot: Dict[int, List[StoreNode]] = {}

    @staticmethod
    def _add_store_with_adaptation(truck: BaseTruck, store: StoreNode):
        """
        默认车型为 420；特殊门店按 available_truck 定向切换车型
        """
        adapted_truck = truck.convert_for_store(store)
        target_truck_cls = adapted_truck.__class__
        if adapted_truck.add_trace(store):
            return adapted_truck
        raise ValueError(
            f"门店 {store.shop_code} 无法装入车型 {target_truck_cls.__name__}，请检查载重或车型限制"
        )

    @staticmethod
    def _find_stepped_target_store(truck_trace: List[StoreNode], candidates: List[StoreNode]) -> tuple[
        Optional[StoreNode], Optional[StoreNode]]:
        """
        阶梯逻辑寻址：按卡车中已有门店距离仓库远近形成阶梯。
        基于“距离容忍度”的两阶段筛选机制：
        1. 获取卡车中每个门店最近的候选店
        2. 选出绝对最小距离并在宽容度范围内的门店
        3. 优先选择挂靠点离仓库最远的候选店
        """
        if not candidates or not truck_trace:
            return None, None

        sorted_truck_stores = sorted(truck_trace, key=lambda s: s.sdist_warehouse, reverse=True)
        candidates_info = []

        for e_store in sorted_truck_stores:
            nearest_c = e_store.find_nearest_store(candidates)
            if nearest_c:
                dist = e_store.calc_haversine_distance(nearest_c)
                candidates_info.append({
                    'e_store': e_store,
                    'c_store': nearest_c,
                    'dist': dist
                })

        if not candidates_info:
            return None, None

        # 1. 找到绝对距离最小的值
        min_dist = min(info['dist'] for info in candidates_info)

        # 2. 设定距离宽容度 (例如: 最小距离的1.2倍，且至少比最小值多给2公里的宽容度)
        tolerance_dist = max(min_dist * 1.2, min_dist + 2.0)

        # 3. 在宽容度范围内的门店中，选择所属已有门店离仓最远（sdist_warehouse最大）的
        valid_candidates = [info for info in candidates_info if info['dist'] <= tolerance_dist]
        best_candidate_info = max(valid_candidates, key=lambda x: x['e_store'].sdist_warehouse)

        return best_candidate_info['c_store'], best_candidate_info['e_store']

    def schedule(self, clusters: List[ClusterNode]):
        """
        全局调度入口：按仓库距离从远到近依次规划各簇。
        """
        if not clusters:
            logger.warning("⚠️ 没有待规划的簇")
            return

        for cluster in clusters:
            self._cluster_store_snapshot[cluster.cluster_id] = list(
                [store for store in cluster.cluster_store_detailed])

        unplanned_store = [store for store in clusters[0].cluster_store_detailed if store.frequency > 2]
        sorted_clusters = sorted(clusters, key=lambda x: x.cdist_warehouse, reverse=True)
        planned_cluster_ids: Set[int] = set()

        for idx, current_cluster in enumerate(sorted_clusters):
            logger.info(
                f"========== 🏁 开始规划簇 {current_cluster.cluster_id} ({idx + 1}/{len(sorted_clusters)}) ==========")
            self._schedule_single_cluster(
                cluster_plan=current_cluster,
                all_clusters=clusters,
                planned_cluster_ids=planned_cluster_ids
            )
            planned_cluster_ids.add(current_cluster.cluster_id)
            current_cluster.is_planned = True

        logger.info(f"========== ✅ 全局调度完成，总出车数: {len(self.plan_trucks)} ==========")
        return unplanned_store

    def _schedule_single_cluster(
            self,
            cluster_plan: ClusterNode,
            all_clusters: List[ClusterNode],
            planned_cluster_ids: Set[int]
    ):
        """
        单簇规划
        1. 当簇中包含高频配送门店（配送频次>2门店数量少于3，直接规划）反之使用分层规划
        2. 分层规划中，优先将配送频次高频的门店放入同一辆车（同一条路线），高频门店规划完后使用配送频次为1次的低频门店填充。
        3. 当前簇规划完后如果有车辆未达到满载率需求，从其他簇借门店进行规划（优先借配送频次等于1次的门店进行规划）
        """
        plan_stores = cast(List[StoreNode], self._cluster_store_snapshot.get(cluster_plan.cluster_id, []))
        # 判定是否开启分层模式（高频店足够多才开启，否则直接混合规划）
        high_freq_stores = [x for x in plan_stores if x.frequency > 1]
        is_simple_mode = len(high_freq_stores) <= self.simple_mode_thres

        logger.info(f"🔍 簇 {cluster_plan.cluster_id} 模式: {'直接规划' if is_simple_mode else '分层规划'} "
                    f"(高频店统计: {len(high_freq_stores)})")

        current_plan_trucks: List[BaseTruck] = []
        active_stores = sorted(plan_stores, key=lambda x: x.sdist_warehouse)

        # 准备邻域借店候选池
        borrow_candidates = self._prepare_borrow_candidates(cluster_plan, all_clusters, planned_cluster_ids)

        while any(s.store_freq_remains > 0 for s in active_stores):
            # 1. 选取种子点（高频优先，远端优先）
            seed_store = self._pick_seed_store(active_stores, is_simple_mode)
            if not seed_store: break

            truck = Truck420()
            # 设定本埠外埠卡车
            if truck.is_homepot is None:
                truck.is_homepot = seed_store.is_homepot

            truck = self._add_store_with_adaptation(truck, seed_store)
            if truck:
                seed_store.update_freq_remains()

                # 为当前车辆准备一个贯穿全程的黑名单，防止在不同阶段重复尝试加不进的点
                truck_black_list: Set[str] = set()

                # --- 第一阶段：本簇高频店规划 ---
                if not is_simple_mode:
                    truck = self._fill_truck_logic(
                        truck, active_stores,
                        use_eco_check=True,
                        black_list=truck_black_list,
                        freq_mode='high'
                    )

                # --- 第二阶段：本簇低频店填充 ---
                if truck.truck_current_load < truck.max_capacity * self.max_truck_capacity_rate:
                    truck = self._fill_truck_logic(
                        truck, active_stores,
                        use_eco_check=(not is_simple_mode),
                        black_list=truck_black_list,
                        freq_mode='low' if not is_simple_mode else 'all'
                    )

                # --- 第三阶段：跨簇借店填充  ---
                if truck.truck_current_load < truck.max_capacity * self.max_truck_capacity_rate:
                    truck = self._borrow_stores_from_candidates(truck, borrow_candidates, truck_black_list)

                truck.calc_max_frequency()
                current_plan_trucks.append(truck)

        self.plan_trucks.extend(current_plan_trucks)

    def _fill_truck_logic(
            self,
            truck: BaseTruck,
            candidate_pool: List[StoreNode],
            use_eco_check: bool,
            black_list: Set[str],
            freq_mode: str = 'all'
    ):
        """
        核心装载逻辑：支持分层过滤、距离保护、同车去重。
        """
        while truck.truck_current_load < truck.max_capacity * self.max_truck_capacity_rate:
            target_store = None
            # 当前门店
            current_node = truck.truck_trace[-1]

            # 当前车辆已安排门店
            stores_in_truck = {s.dept_id for s in truck.truck_trace}

            # 当前规划中的门店候选集合
            candidate = [s for s in candidate_pool if s.store_freq_remains > 0
                         and s.dept_id not in black_list
                         and s.dept_id not in stores_in_truck]

            if not candidate: break

            # 寻找地理上的绝对最近点作为参照
            abs_nearest = current_node.find_nearest_store(candidate)
            dist_min = current_node.calc_haversine_distance(abs_nearest)

            # 分层决策
            if freq_mode == 'high':
                # 调整：高频筛选条件 - 剩余频次大于1或者是偶数频次且未全部分配完
                # 这里针对“奇数频次最后一次变成低频”的逻辑：对于偶数频次（或奇数频次还没到最后1次）始终保持高频，
                # 如果是奇数频次且剩余频次余 1 次，则不当做高频，留给低频阶段放入其他镜像车辆中。
                high_freqs = [s for s in candidate if
                              s.frequency >= 2 and not (s.frequency % 2 != 0 and s.store_freq_remains == 1)]
                if high_freqs:
                    nearest_high = current_node.find_nearest_store(high_freqs)
                    dist_high = current_node.calc_haversine_distance(nearest_high)
                    # 距离保护：防止为了凑高频而满地图乱跑
                    if dist_high <= dist_min * self.detour_thres:
                        target_store = nearest_high
                    else:
                        break  # 太远了，本车的高频骨架阶段提前结束
                else:
                    break
            elif freq_mode == 'low':
                # 调整：低频筛选条件 - 包含本身就是低频(总频次1)的，以及奇数频次余1次的门店
                low_freqs = [s for s in candidate if s.frequency == 1 or (s.frequency % 2 != 0)]
                if low_freqs:
                    target_store, best_e_store = self._find_stepped_target_store(truck.truck_trace, low_freqs)
                    if not target_store:
                        break
                    if best_e_store:
                        current_node = best_e_store
                else:
                    break
            else:
                target_store = abs_nearest

            if not target_store: break

            # 路线经济性校验
            eco_pass = not use_eco_check or RouteOptimizer.is_eco_route(
                current_node,
                target_store,
                threshold=self.dist_thres,
                one_way_dist_max=self.one_way_dist_max
            )

            # 如果路线合适并且卡车可以装下更新门店频次，否则加入当前车辆黑名单
            if not eco_pass:
                black_list.add(target_store.dept_id)
                continue

            try:
                truck = self._add_store_with_adaptation(truck, target_store)
                target_store.update_freq_remains()
            except ValueError:
                black_list.add(target_store.dept_id)

        return truck

    def _borrow_stores_from_candidates(
            self,
            truck: BaseTruck,
            borrow_candidates: Dict[int, List[StoreNode]],
            black_list: Set[str]
    ):
        """
        从邻域簇或DC近端簇借店填充，优先借频次为1的。本埠与外埠不允许互拼
        """
        while truck.truck_current_load < truck.max_capacity * self.max_truck_capacity_rate:
            current_node = truck.truck_trace[-1]
            stores_in_truck = {s.dept_id for s in truck.truck_trace}

            all_cands = []
            for cluster_id, stores in borrow_candidates.items():
                available = [s for s in stores if s.store_freq_remains > 0
                             and s.dept_id not in black_list
                             and s.dept_id not in stores_in_truck
                             and s.is_homepot == truck.is_homepot]
                all_cands.extend(available)

            if not all_cands: break

            # 优先借 频次=1 的店（或者奇数频次最后剩余1次的门店），这对仓库作业均衡最有利
            f1_cands = [s for s in all_cands if
                        s.frequency == 1 or (s.frequency % 2 != 0 and s.store_freq_remains == 1)]
            if f1_cands:
                target, best_e_store = self._find_stepped_target_store(truck.truck_trace, f1_cands)
                if not target:
                    break

                eval_node = best_e_store if best_e_store else current_node

                # 借店同样受绕路距离保护（邻居可以远，但不能远的离谱）
                # 用全局 all_cands 计算出的阶梯最佳点作为参照
                fallback_target, fallback_e_store = self._find_stepped_target_store(truck.truck_trace, all_cands)
                if fallback_target and fallback_e_store:
                    abs_min_dist = fallback_e_store.calc_haversine_distance(fallback_target)
                    if eval_node.calc_haversine_distance(target) > abs_min_dist * self.detour_thres:
                        target = fallback_target
            else:
                break

            if not target:
                break

            try:
                truck = self._add_store_with_adaptation(truck, target)
                target.update_freq_remains()
                logger.info(f"  📥 借店成功: 门店 {target.dept_id} (来自邻居/DC簇)")
            except ValueError:
                black_list.add(target.dept_id)
                break

        return truck

    def _prepare_borrow_candidates(self, current_cluster, all_clusters, planned_cluster_ids) -> Dict[
        int, List[StoreNode]]:
        """
        局部搜索, 搜索相邻n个cluster的合法门店形成门店池。
        """
        candidates = {}

        geo_near = current_cluster.get_nearest_n_cluster(all_clusters, n=self.search_n_neighbor)
        unplanned = [c for c in all_clusters if
                     c.cluster_id not in planned_cluster_ids and c.cluster_id != current_cluster.cluster_id]

        target_ids = {c.cluster_id for c in geo_near}
        if unplanned:
            # 找离仓库最近的地理簇，加入到目标簇
            dc_near = min(unplanned, key=lambda x: x.cdist_warehouse)
            target_ids.add(dc_near.cluster_id)

        for cid in target_ids:
            if cid not in planned_cluster_ids and cid != current_cluster.cluster_id:
                candidates[cid] = self._cluster_store_snapshot.get(cid, [])
        return candidates

    def _pick_seed_store(self, stores: List[StoreNode], is_simple_mode: bool) -> Optional[StoreNode]:
        """
        选择种子门店：优先选择距离最远的高频店
        """
        candidates = [s for s in stores if s.store_freq_remains > 0]
        if not candidates: return None

        if not is_simple_mode:
            high_freq = [s for s in candidates if
                         s.frequency >= 2 and not (s.frequency % 2 != 0 and s.store_freq_remains == 1)]
            if high_freq:
                return high_freq[-1]  # active_stores 已按距离升序，故 -1 为最远
        return candidates[-1]

    def post_process(self, truck_capacity_limit: float = 0.5):
        """
        后处理逻辑：将低负载车辆合并到最近的同波次顺序的镜像卡车中，
        保证多次配送的门店合并后仍然保持一致，不破坏周排班的间隔约束。
        """
        logger.info(f"========== 📈 开始后处理 (阈值: {truck_capacity_limit:.0%}) ==========")

        groups: Dict[frozenset, List[BaseTruck]] = {}
        for truck in self.plan_trucks:
            # 提取高频门店 ID 作为镜像签名
            high_freq_depts = frozenset(s.dept_id for s in truck.truck_trace if s.frequency > 1)
            if high_freq_depts:
                sig = high_freq_depts
            else:
                # 纯低频车，使用唯一的 truck_id 确保其独立，不被归为同组
                sig = frozenset([truck.truck_id])
            groups.setdefault(sig, []).append(truck)

        satis_groups = []
        unsatis_groups = []

        for sig, t_list in groups.items():
            # 组内车辆负载可能因填充了不同的低频店而略有不同，取最大负载判断是否达标
            load = max(t.truck_current_load for t in t_list)
            max_load = t_list[0].max_capacity
            if load >= max_load * truck_capacity_limit:
                satis_groups.append(t_list)
            else:
                unsatis_groups.append(t_list)

        final_groups = list(satis_groups)

        for low_group in unsatis_groups:
            low_len = len(low_group)

            best_target_idx = -1
            min_dist = float('inf')

            for idx, target_group in enumerate(final_groups):
                # 条件1: 镜像卡车数量相同 (同波次顺序)
                if len(target_group) == low_len:
                    # 条件2: 所有对应车辆的载重均允许
                    load_ok = True
                    for i in range(low_len):
                        if target_group[i].truck_current_load + low_group[i].truck_current_load > target_group[
                            i].max_capacity:
                            load_ok = False
                            break
                    if not load_ok:
                        continue

                    # 条件3: 所有对应车辆的门店均不重复
                    overlap = False
                    for i in range(low_len):
                        target_depts = {s.dept_id for s in target_group[i].truck_trace}
                        for s in low_group[i].truck_trace:
                            if s.dept_id in target_depts:
                                overlap = True
                                break
                        if overlap:
                            break
                    if overlap:
                        continue

                    # 条件4: 计算距离 (取 target_group 任意门店 与 low_group 任意门店 的最短距离)
                    current_min_dist = min(
                        t_store.calc_haversine_distance(l_store)
                        for t in target_group
                        for l in low_group
                        for t_store in t.truck_trace
                        for l_store in l.truck_trace
                    )
                    if current_min_dist < min_dist:
                        min_dist = current_min_dist
                        best_target_idx = idx

            if best_target_idx != -1:
                # 执行合并
                target_group = final_groups[best_target_idx]
                merged_group = [truck.model_copy(deep=True) for truck in target_group]
                merge_success = True
                for i in range(low_len):
                    for store in low_group[i].truck_trace:
                        try:
                            merged_group[i] = self._add_store_with_adaptation(merged_group[i], store)
                        except ValueError:
                            merge_success = False
                            break
                    if not merge_success:
                        break

                if merge_success:
                    final_groups[best_target_idx] = merged_group
                    logger.info(f"🔄 成功将 {low_len} 辆低负载车 合并到目标镜像车组")
                else:
                    final_groups.append(low_group)
                    logger.info(f"🗑️ {low_len} 辆低负载车 因车型限制无法合并，保持独立")
            else:
                # 无法合并，保留独立出车
                final_groups.append(low_group)
                logger.info(f"🗑️ {low_len} 辆低负载车 无法找到合适镜像车组合并，保持独立")

        # 展平 final_groups 更新到 plan_trucks
        self.plan_trucks = [truck for g in final_groups for truck in g]
