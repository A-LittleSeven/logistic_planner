from typing import List, Dict, Set

import numpy as np

from app.models.truck import BaseTruck
from app.core.utils.logutils import LogUtil

logger = LogUtil.get_logger(__name__)


def working_schedule(trucks: List[BaseTruck], work_days: int = 7):
    daily_load = np.zeros(work_days)
    schedule_results: Dict[int, List[int]] = {d: [] for d in range(work_days)}
    store_history: Dict[str, list] = {}

    sorted_trucks = sorted(trucks, key=lambda x: (x.truck_frequency_max, x.truck_current_load), reverse=True)

    for truck in sorted_trucks:

        possible_days_mask = np.ones(work_days)
        # 记录每个门店屏蔽了哪些日期，用于冲突诊断
        store_block_info: Dict[str, Set[int]] = {}

        for node in truck.truck_trace:
            history = store_history.get(node.dept_id, [])
            min_int = max(work_days // node.frequency - 1, 0)
            blocked_days = set()
            for past_day in history:
                for d in range(work_days):
                    dist = min(abs(d - past_day), work_days - abs(d - past_day))
                    if dist <= min_int:
                        possible_days_mask[d] = 0
                        blocked_days.add(d)
            if blocked_days:
                store_block_info[node.dept_id] = blocked_days

        valid_days = np.where(possible_days_mask == 1)[0]

        if len(valid_days) > 0:
            best_day = valid_days[np.argmin(daily_load[valid_days])]
            # 正常分配：更新历史记录
            schedule_results[best_day].append(truck.truck_id)
            daily_load[best_day] += truck.truck_current_load or 0
            for node in truck.truck_trace:
                store_history.setdefault(node.dept_id, []).append(best_day)
        else:
            # 无可用日期时，计算每天的冲突门店数，选择冲突最少的日期
            # 对于频次为2次的门店，放宽间隔约束：正常间隔2天，降级后至少间隔1天
            day_conflict_counts = np.zeros(work_days, dtype=int)
            day_conflict_details = {d: [] for d in range(work_days)}

            for day in range(work_days):
                for node in truck.truck_trace:
                    history = store_history.get(node.dept_id, [])
                    # 计算间隔天数
                    min_int = max(work_days // node.frequency - 1, 0)
                    # 频次为2次的门店，降级间隔：从间隔2天降为至少间隔1天
                    if node.frequency == 2:
                        min_int = 1  # 至少间隔1天
                    for past_day in history:
                        # 检查分配到当天是否会与历史配送产生冲突（考虑环形依赖，如周1与周6）
                        dist = min(abs(day - past_day), work_days - abs(day - past_day))
                        if dist <= min_int:
                            day_conflict_counts[day] += 1
                            conflict_type = "降级冲突" if node.frequency == 2 else "冲突"
                            day_conflict_details[day].append(
                                f"门店[{node.dept_id}] 频次={node.frequency}, 已安排于周{past_day + 1}, {conflict_type}周{day + 1}"
                            )
                            break  # 每个门店只计一次冲突

            # 选择冲突最少的日期，冲突相同时选择载重最小的
            min_conflict = np.min(day_conflict_counts)
            min_conflict_days = np.where(day_conflict_counts == min_conflict)[0]
            best_day = min_conflict_days[np.argmin(daily_load[min_conflict_days])]

            # 输出详细冲突诊断信息
            logger.warning(
                f"⚠️ 车辆 {truck.truck_id} 无可用日期, 开始冲突分析(频次2次门店已降级间隔约束)"
            )

            # 输出各天冲突情况
            for day in range(work_days):
                if day_conflict_counts[day] > 0:
                    logger.info(
                        f"   周{day + 1}: 冲突门店数={day_conflict_counts[day]}\n" +
                        "\n".join(f"      - {detail}" for detail in day_conflict_details[day])
                    )

            # 输出冲突门店详情
            conflict_stores = []
            for node in truck.truck_trace:
                if node.dept_id in store_history:
                    scheduled_days = store_history[node.dept_id]
                    freq_info = f"频次={node.frequency}"
                    if node.frequency == 2:
                        freq_info += "(降级间隔: 2天→1天)"
                    conflict_stores.append(
                        f"门店[{node.dept_id}] {freq_info}, 已安排于周{[d + 1 for d in scheduled_days]}"
                    )

            logger.warning(
                f"   冲突门店详情:\n" +
                "\n".join(f"   - {s}" for s in conflict_stores) +
                f"\n   ✅ 选择周{best_day + 1}（冲突门店数: {day_conflict_counts[best_day]}, 当日载重: {daily_load[best_day]:.1f}）"
            )

            # 强制分配：只更新调度结果，不更新 store_history 避免连锁影响后续车辆
            schedule_results[best_day].append(truck.truck_id)
            daily_load[best_day] += truck.truck_current_load or 0

    return schedule_results, daily_load


def balance_schedule(
        schedule_results: Dict[int, List[int]],
        daily_load: np.ndarray,
        trucks: List[BaseTruck],
        work_days: int = 6,
        balance_threshold: float = 0.2
) -> tuple:
    """
    后处理：负载均衡，从高发车日移动不易冲突的车辆到低发车日

    Args:
        schedule_results: 调度结果 {日期: [车辆ID列表]}
        daily_load: 每日载重数组
        trucks: 车辆列表
        work_days: 工作日数
        balance_threshold: 均衡阈值，发车数差异超过平均值的该比例时触发均衡

    Returns:
        更新后的 (schedule_results, daily_load)
    """
    # 构建车辆ID到车辆对象的映射
    truck_map = {t.truck_id: t for t in trucks}

    # 计算每日发车数
    daily_truck_counts = np.array([len(schedule_results[d]) for d in range(work_days)])
    avg_count = np.mean(daily_truck_counts)

    # 检查是否需要均衡
    max_count = np.max(daily_truck_counts)
    min_count = np.min(daily_truck_counts)

    if float(max_count - min_count) <= float(avg_count * balance_threshold):
        logger.info(f"📅 发车数分布均衡，无需调整 (最大={max_count}, 最小={min_count}, 平均={avg_count:.1f})")
        return schedule_results, daily_load

    logger.info(
        f"⚖️ 开始负载均衡 (最大发车数={max_count}, 最小={min_count}, 平均={avg_count:.1f}, 阈值={balance_threshold})"
    )

    # 计算每个车辆的"冲突敏感度"：频次越低的门店越容易产生冲突
    # 敏感度低的车辆更适合移动
    def calc_truck_conflict_sensitivity(truck: BaseTruck) -> float:
        """
        计算车辆的冲突敏感度
        敏感度高 = 包含高频次门店多 = 不易移动
        敏感度低 = 包含低频次门店多 = 容易移动
        """
        if not truck.truck_trace:
            return 0.0
        # 频次越高（约束越多），敏感度越高，越难移动；频次为1的门店贡献为0
        total_sensitivity = sum(float(node.frequency - 1) for node in truck.truck_trace)
        return total_sensitivity / len(truck.truck_trace)

    # 计算每个车辆可以移动到哪些日期（不产生冲突）
    def get_valid_move_days(truck: BaseTruck, store_history: Dict[str, list], exclude_day: int) -> List[int]:
        """获取车辆可以移动到的有效日期"""
        valid_days = []
        for target_day in range(work_days):
            if target_day == exclude_day:
                continue
            # 检查是否有冲突
            has_conflict = False
            for node in truck.truck_trace:
                history = store_history.get(node.dept_id, [])
                min_int = max(work_days // node.frequency - 1, 0)
                for _ in history:
                    # 排除当前所在日期的历史记录（因为要移动走）
                    filtered_history = [d for d in history if d != exclude_day]
                    for pd in filtered_history:
                        dist = min(abs(target_day - pd), work_days - abs(target_day - pd))
                        if dist <= min_int:
                            has_conflict = True
                            break
                    if has_conflict:
                        break
                if has_conflict:
                    break
            if not has_conflict:
                valid_days.append(target_day)
        return valid_days

    # 重建 store_history
    store_history: Dict[str, list] = {}
    for day, truck_ids in schedule_results.items():
        for tid in truck_ids:
            if tid in truck_map:
                for node in truck_map[tid].truck_trace:
                    store_history.setdefault(node.dept_id, []).append(day)

    # 迭代均衡
    max_iterations = 20
    for iteration in range(max_iterations):
        daily_truck_counts = np.array([len(schedule_results[d]) for d in range(work_days)])
        current_max = np.max(daily_truck_counts)
        current_min = np.min(daily_truck_counts)

        if current_max - current_min <= 1:
            logger.info(f"   ✅ 均衡完成, 发车数差异≤1")
            break

        # 找出高发车日和低发车日
        high_days = np.where(daily_truck_counts == current_max)[0]
        low_days = np.where(daily_truck_counts == current_min)[0]

        moved = False
        for high_day in high_days:
            if moved:
                break

            # 获取该日所有车辆，按冲突敏感度排序（敏感度低的优先移动）
            high_day_trucks = schedule_results[high_day][:]
            truck_sensitivities = []
            for tid in high_day_trucks:
                if tid in truck_map:
                    sensitivity = calc_truck_conflict_sensitivity(truck_map[tid])
                    truck_sensitivities.append((tid, sensitivity))

            # 按敏感度升序排序（低敏感度优先）
            truck_sensitivities.sort(key=lambda x: x[1])

            # 尝试移动到低发车日
            for tid, sensitivity in truck_sensitivities:
                truck = truck_map[tid]
                for low_day in low_days:
                    # 检查是否可以移动
                    valid_days = get_valid_move_days(truck, store_history, high_day)
                    if low_day in valid_days:
                        # 执行移动
                        schedule_results[high_day].remove(tid)
                        schedule_results[low_day].append(tid)
                        daily_load[high_day] -= truck.truck_current_load or 0
                        daily_load[low_day] += truck.truck_current_load or 0

                        # 更新 store_history
                        for node in truck.truck_trace:
                            if high_day in store_history.get(node.dept_id, []):
                                store_history[node.dept_id].remove(high_day)
                            store_history.setdefault(node.dept_id, []).append(low_day)

                        logger.info(
                            f"   🔄 车辆 {tid} 从周{high_day + 1} → 周{low_day + 1} "
                            f"(敏感度={sensitivity:.2f}, 载重={truck.truck_current_load:.1f})"
                        )
                        moved = True
                        break
                if moved:
                    break

        if not moved:
            logger.info(f"   ⏸️ 无法继续移动车辆，结束均衡")
            break

    return schedule_results, daily_load
