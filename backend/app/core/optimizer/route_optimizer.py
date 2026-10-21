from typing import List

from app.models.store import StoreNode
from app.models.vehicle import BaseTruck
from app.utils.distance import haversine
from app.utils.logger import LogUtil

logger = LogUtil.get_logger(__name__)


class RouteOptimizer(object):

    @staticmethod
    def is_eco_route(current_store: StoreNode, next_store: StoreNode, threshold: float = 0.9, one_way_dist_max=90):
        """
        判断当前加入门店是否经济（是否需要绕远路专门去送）
        :return:
        """
        cur_dist_to_ware = current_store.sdist_warehouse
        next_dist_to_ware = next_store.sdist_warehouse
        cur_to_next_dist = haversine(current_store.store_lon, current_store.store_lat,
                                     next_store.store_lon, next_store.store_lat)
        if (cur_to_next_dist + next_dist_to_ware) * threshold > (cur_dist_to_ware + next_dist_to_ware):
            logger.debug(
                f" ❌️ {current_store.dept_id} -> {next_store.dept_id} 门店距离过远，为不经济路线")
            return False
        else:
            if cur_to_next_dist > one_way_dist_max:
                logger.debug(
                    f" ❗️{current_store.dept_id} -> {next_store.dept_id} 门店间卡车配送距离超过{one_way_dist_max}km，需关注卡车装载")
            return True

    @staticmethod
    def local_route_optimize(truck_list: List[BaseTruck]):
        """
        对车辆进行局部优化 优化最优路线
        :param truck_list:
        :return:
        """

        def calc_route_distance(route):
            """
            计算车辆总距离
            :return:
            """
            distance = 0
            distance += route[0].sdist_warehouse
            for i in range(len(route) - 1):
                distance += haversine(
                    route[i].store_lon, route[i].store_lat,
                    route[i + 1].store_lon, route[i + 1].store_lat
                )
            distance += route[-1].sdist_warehouse
            return distance

        for truck in truck_list:
            original_route = truck.truck_trace
            if len(original_route) < 2:
                continue

            best_route = original_route[:]
            best_dist = calc_route_distance(original_route)

            max_iterations = 50
            iteration_count = 0

            improved = True
            while improved and iteration_count < max_iterations:
                improved = False
                iteration_count += 1

                for i in range(1, len(best_route) - 1):
                    for j in range(i + 1, len(best_route)):
                        new_route = best_route[:i] + best_route[i:j + 1][::-1] + best_route[j + 1:]
                        new_dist = calc_route_distance(new_route)

                        if new_dist < best_dist:
                            best_route = new_route[:]
                            best_dist = new_dist
                            improved = True
                            break
                    if improved:
                        break

            truck.truck_trace = best_route
        return truck_list
