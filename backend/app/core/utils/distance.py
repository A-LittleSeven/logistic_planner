import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from math import radians, cos, sin, asin, sqrt, atan2

from app.core.utils.logutils import LogUtil

logger = LogUtil.get_logger(__name__)


def calc_distance(lon1, lat1, lon2, lat2, method='haversine', **kwargs):
    """
    选择距离计算方式
    :param lon1: 经度1
    :param lat1: 纬度1
    :param lon2: 经度2
    :param lat2: 纬度2
    :param method: distance selector，可选 haversine/manhattan/euclidean/baidu_driving
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


def haversine(lon1, lat1, lon2, lat2):
    """
    计算两个经纬度之间的haversine距离 (km)
    :param lon1: 经度1
    :param lat1: 纬度1
    :param lon2: 经度2
    :param lat2: 纬度2
    :return: 距离 (km)
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371
    return c * r


def manhattan_distance(lon1, lat1, lon2, lat2):
    """
    计算两个经纬度之间的曼哈顿距离 (km)
    近似公式：纬度1°≈111km，经度1°≈111*cos(平均纬度)km
    :param lon1: 经度1
    :param lat1: 纬度1
    :param lon2: 经度2
    :param lat2: 纬度2
    :return: 距离 (km)
    """
    avg_lat = radians((lat1 + lat2) / 2)
    dlat_km = abs(lat1 - lat2) * 111.0
    dlon_km = abs(lon1 - lon2) * 111.0 * cos(avg_lat)
    return dlat_km + dlon_km


def euclidean_distance(lon1, lat1, lon2, lat2):
    """
    计算两个经纬度之间的欧式距离 (km)
    近似公式：纬度1°≈111km，经度1°≈111*cos(平均纬度)km
    :param lon1: 经度1
    :param lat1: 纬度1
    :param lon2: 经度2
    :param lat2: 纬度2
    :return: 距离 (km)
    """
    avg_lat = radians((lat1 + lat2) / 2)
    dlat_km = abs(lat1 - lat2) * 111.0
    dlon_km = abs(lon1 - lon2) * 111.0 * cos(avg_lat)
    return sqrt(dlat_km ** 2 + dlon_km ** 2)


def baidu_driving_distance(lon1, lat1, lon2, lat2, ak='', timeout=3):
    """
    调用百度地图驾车路线规划 API 计算两个点之间的驾车距离 (km)。

    注意：
    - 百度坐标顺序为「纬度,经度」(lat,lng)，本函数内部已做转换，调用方仍按 (lon, lat) 传参。
    - 本项目 data 中 gd_lat/gd_lgt 为高德 GCJ-02 坐标，故 coord_type 默认 'gcj02ll'；
      若数据为百度 BD-09 坐标请用 'bd09ll'，WGS-84 请用 'wgs84ll'。
    - 该接口为网络请求，受百度开放平台 QPS 限制；大批量调用建议自行限流或缓存。

    :param lon1: 经度1
    :param lat1: 纬度1
    :param lon2: 经度2
    :param lat2: 纬度2
    :param ak: 百度地图 AK。为空时读取环境变量 BAIDU_MAP_AK。
    :param coord_type: 坐标类型，可选 bd09ll / gcj02ll / wgs84ll。
    :param timeout: 请求超时秒数。
    :return: 驾车距离 (km)
    """
    if not ak:
        ak = os.environ.get('BAIDU_MAP_AK', '')
    if not ak:
        raise ValueError("缺少百度地图 AK，请传入 ak 参数或设置环境变量 BAIDU_MAP_AK")

    # 百度接口要求 origin/destination 为「纬度,经度」
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
        logger.error(f"百度地图驾车距离请求失败: {e}")
        raise RuntimeError(f"百度地图驾车距离请求失败: {e}") from e

    status = data.get('status')
    if status != 0:
        msg = data.get('message', '未知错误')
        logger.error(f"百度地图驾车距离接口返回错误 status={status}: {msg}")
        raise RuntimeError(f"百度地图驾车距离接口返回错误 status={status}: {msg}")

    routes = data.get('result', {}).get('routes')
    if not routes:
        logger.error(f"百度地图驾车距离未返回路线: origin={params['origin']} destination={params['destination']}")
        raise RuntimeError(f"百度地图驾车距离未返回路线: origin={params['origin']} destination={params['destination']}")

    time.sleep(0.5)
    # routes[0].distance 单位为米，转换为 km 与其它距离函数保持一致
    return routes[0].get('distance', 0) / 1000.0


if __name__ == '__main__':
    dist = baidu_driving_distance(114.82,30.21, 114.79,31.06)
    print(dist)