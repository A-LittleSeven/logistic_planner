import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from math import radians, cos, sin, asin, sqrt
from typing import Optional, Protocol, Sequence, Tuple
import numpy as np


class DistanceProvider(Protocol):
    """距离提供者协议。"""
    def distance(self, lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        ...

    def matrix_km(self, pts: Sequence[Tuple[float, float]], as_list: bool = True) -> "list[list[float]] | np.ndarray":
        """返回 n×n 距离矩阵 (km)，pts 为 (lng, lat) 元组列表。as_list=False 时返回 numpy 数组以避免大矩阵的 Python 对象内存开销。"""
        ...


class HaversineProvider:
    """使用 Haversine 公式计算球面大圆距离与距离矩阵。"""
    def distance(self, lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        return haversine(lon1, lat1, lon2, lat2)

    def matrix_km(self, pts: Sequence[Tuple[float, float]], as_list: bool = True) -> "list[list[float]] | np.ndarray":
        """构建 n×n haversine 距离矩阵 (km)，pts 为 (lng, lat) 元组列表。"""
        n = len(pts)
        if n == 0:
            return [] if as_list else np.zeros((0, 0), dtype=float)
        if n == 1:
            return [[0.0]] if as_list else np.zeros((1, 1), dtype=float)

        coords = np.radians(np.asarray(pts, dtype=float))
        lons = coords[:, 0]
        lats = coords[:, 1]

        dlon = lons[:, None] - lons[None, :]
        dlat = lats[:, None] - lats[None, :]

        a = np.sin(dlat / 2.0) ** 2 + np.cos(lats[:, None]) * np.cos(lats[None, :]) * (np.sin(dlon / 2.0) ** 2)
        np.clip(a, 0.0, 1.0, out=a)
        dist_mat = 2.0 * 6371.0 * np.arcsin(np.sqrt(a))
        np.fill_diagonal(dist_mat, 0.0)
        return dist_mat.tolist() if as_list else dist_mat


def ensure_provider(provider: Optional[DistanceProvider] = None) -> DistanceProvider:
    """确保返回有效的 DistanceProvider 实例（未传入时默认使用 HaversineProvider）。"""
    return provider if provider is not None else HaversineProvider()


def get_provider(name: str, amap_key: str = "") -> DistanceProvider:
    """根据配置名称返回对应的距离计算提供者。"""
    if name == "haversine":
        return HaversineProvider()
    # 可扩展: elif name == "amap": return AMapProvider(amap_key)
    return HaversineProvider()


def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    计算两个经纬度之间的haversine距离 (km)。
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371
    return c * r


def manhattan_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """计算两个经纬度之间的曼哈顿距离 (km)。"""
    avg_lat = radians((lat1 + lat2) / 2)
    dlat_km = abs(lat1 - lat2) * 111.0
    dlon_km = abs(lon1 - lon2) * 111.0 * cos(avg_lat)
    return dlat_km + dlon_km


def euclidean_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """计算两个经纬度之间的欧式距离 (km)。"""
    avg_lat = radians((lat1 + lat2) / 2)
    dlat_km = abs(lat1 - lat2) * 111.0
    dlon_km = abs(lon1 - lon2) * 111.0 * cos(avg_lat)
    return sqrt(dlat_km ** 2 + dlon_km ** 2)


def calc_distance(lon1: float, lat1: float, lon2: float, lat2: float, method: str = 'haversine', **kwargs) -> float:
    """
    选择距离计算方式。
    :param method: 可选 haversine / manhattan / euclidean / baidu_driving
    :return: 距离 (km)
    """
    if method == 'manhattan':
        return manhattan_distance(lon1, lat1, lon2, lat2)
    elif method == 'euclidean':
        return euclidean_distance(lon1, lat1, lon2, lat2)
    elif method == 'haversine':
        return haversine(lon1, lat1, lon2, lat2)
    elif method == 'baidu_driving':
        return baidu_driving_distance(lon1, lat1, lon2, lat2, **kwargs)
    else:
        raise ValueError(f"不支持的距离计算方法: {method}，可选值: haversine, manhattan, euclidean, baidu_driving")


def baidu_driving_distance(lon1: float, lat1: float, lon2: float, lat2: float,
                            ak: str = '', timeout: int = 3) -> float:
    """
    调用百度地图驾车路线规划 API 计算两个点之间的驾车距离 (km)。
    """
    if not ak:
        ak = os.environ.get('BAIDU_MAP_AK', '')
    if not ak:
        raise ValueError("缺少百度地图 AK，请传入 ak 参数或设置环境变量 BAIDU_MAP_AK")

    params = {
        'origin': f'{lat1},{lon1}',
        'destination': f'{lat2},{lon2}',
        'ak': ak
    }
    url = 'https://api.map.baidu.com/direction/v2/driving?' + urllib.parse.urlencode(params)

    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except urllib.error.URLError as e:
        raise RuntimeError(f"百度地图驾车距离请求失败: {e}") from e

    status = data.get('status')
    if status != 0:
        msg = data.get('message', '未知错误')
        raise RuntimeError(f"百度地图驾车距离接口返回错误 status={status}: {msg}")

    routes = data.get('result', {}).get('routes')
    if not routes:
        raise RuntimeError(f"百度地图驾车距离未返回路线: origin={params['origin']} destination={params['destination']}")

    time.sleep(0.5)
    return routes[0].get('distance', 0) / 1000.0
