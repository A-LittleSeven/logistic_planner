import pandas as pd
from typing import Dict, List, Any

from app.models.store import StoreNode
from app.models.truck import BaseTruck
from app.core.utils.logutils import LogUtil

logger = LogUtil.get_logger(__name__)


def build_store_node(row: Dict[str, Any], idx: int) -> StoreNode:
    """
    基于显式列名构建门店对象，避免依赖 CSV 列顺序。
    """
    return StoreNode(
        cluster_center_id=int(row['cluster_id']),
        cluster_center_lon=float(row['center_lng']),
        cluster_center_lat=float(row['center_lat']),
        cdist_warehouse=float(row['c_dist']),
        dept_id=str(row['dept_id']),
        shop_code=str(row['shop_code']),
        warzone=str(row.get('warzone', '0')),
        district=str(row.get('district', '')),
        name=str(row.get('shop_name', idx)),
        is_homepot=int(row.get('is_homepot', 1)),
        store_lon=float(row['lng']),
        store_lat=float(row['lat']),
        sdist_warehouse=float(row['s_dist']),
        frequency=int(row['frequency']),
        store_freq_remains=int(row['frequency']),
        avg_loads=float(row['avg_loads'])
    )


def export_schedule_to_csv(schedule_results: Dict[int, List[int]], trucks: List[BaseTruck],
                           high_freq_stores: List[Any] = None, work_days: int = 7,
                           output_path: str = 'schedule_result.csv'):
    """
    将排班结果导出为 CSV 文件。
    格式: 门店编号, 配送周期, 频次, 平均箱数, 周一, 周二, 周三, 周四, 周五, 周六, 周日
    """
    truck_map: Dict[int, BaseTruck] = {int(t.truck_id): t for t in trucks if t.truck_id is not None}
    store_info = {}

    for t in trucks:
        for store in t.truck_trace:
            if store.dept_id not in store_info:
                store_info[store.dept_id] = {
                    '门店编号': store.shop_code,  # 也可以用 store.dept_id, 这里假设使用shop_code表示 A001 等
                    '频次': store.frequency,
                    '平均箱数': store.avg_loads,
                    'days': set()
                }

    for day, t_ids in schedule_results.items():
        for tid in map(int, t_ids):
            truck = truck_map.get(tid)
            if truck is None:
                continue
            for store in truck.truck_trace:
                store_info[store.dept_id]['days'].add(day)

    # 计算每天的总负载，用于高频店多余天数的分配依据
    daily_loads = {d: 0.0 for d in range(work_days)}
    for day, t_ids in schedule_results.items():
        for tid in map(int, t_ids):
            truck = truck_map.get(tid)
            if truck is not None:
                daily_loads[day] += (truck.truck_current_load or 0.0)

    if high_freq_stores:
        for store in high_freq_stores:
            freq = store.frequency
            if freq <= 0:
                continue

            best_days = []
            min_load_sum = float('inf')

            # 尝试所有的 start_day，选择总载重最低的日期组合
            for candidate_start in range(work_days):
                num_step2 = min(freq, work_days // 2)
                candidate_days = []
                for j in range(num_step2):
                    candidate_days.append((candidate_start + 2 * j) % work_days)

                remains_needed = freq - num_step2
                if remains_needed > 0:
                    unselected_days = [d for d in range(work_days) if d not in candidate_days]
                    unselected_days.sort(key=lambda d: daily_loads.get(d, 0.0))
                    candidate_days.extend(unselected_days[:remains_needed])

                load_sum = sum(daily_loads.get(d, 0.0) for d in candidate_days)
                if load_sum < min_load_sum:
                    min_load_sum = load_sum
                    best_days = candidate_days

            days = best_days

            # 实时更新每日负载，以便后面的高频门店能基于最新负载做出最优选择
            for d in days:
                daily_loads[d] += (store.avg_loads or 0.0)

            if store.dept_id not in store_info:
                store_info[store.dept_id] = {
                    '门店编号': store.shop_code,
                    '频次': store.frequency,
                    '平均箱数': store.avg_loads,
                    'days': set()
                }
            store_info[store.dept_id]['days'].update(days)

    day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    rows = []
    for dept_id, info in store_info.items():
        row = {
            '门店编号': info['门店编号'],
            '频次': info['频次'],
            '平均箱数': info['平均箱数']
        }

        scheduled_days = sorted(list(info['days']))
        cycle_str = "/".join([day_names[d] for d in scheduled_days if d < len(day_names)])
        row['配送周期'] = cycle_str

        for i in range(7):
            row[day_names[i]] = 1 if i in info['days'] else 0

        rows.append(row)

    df_out = pd.DataFrame(rows)
    cols = ['门店编号', '配送周期', '频次', '平均箱数'] + day_names
    df_out = df_out[cols]

    df_out.to_csv(output_path, index=False, encoding='utf-8-sig')
    logger.info(f"✅ 调度结果已导出到: {output_path}")
    return df_out


def export_route_to_csv(n_day, daily_routes, output_path='routes.csv'):
    with open(output_path, 'a+', encoding='utf-8') as f:
        for r_idx, route in enumerate(daily_routes):
            stop_codes = route.get('path_store_ids', [])
            stops = route.get('stops', [])
            route_str = f"路线{r_idx} 仓库 -> " + " -> ".join([i.name for i in stops]) + " -> 仓库"
            f.write(f'周{n_day}' + ', ' + f'路线{r_idx}' + ', ' + route_str + '\n')
