import { ref } from 'vue'
import { planTruckDrivingRoute } from './useAMap.js'
import { ElMessage } from 'element-plus'
import { formatDuration } from '../utils/constants.js'

/**
 * 货车路网规划与实测核心 Composable
 */
export function useRouteMeasure() {
  const loadingAmapRouteKey = ref(null)
  const batchMeasuring = ref(false)
  const measureProgress = ref({ current: 0, total: 0, percent: 0, currentRouteName: '' })
  const measureSummary = ref(null)

  /**
   * 根据车型名称/载重解析货车物理参数
   */
  const getTruckParams = (truckName = '', customOpts = {}) => {
    let truckOpts = { size: 2, width: 2.1, height: 2.8, load: 4.5, weight: 2.0, ...customOpts }
    const name = String(truckName || '')
    if (name.includes('6.8') || name.includes('中型') || name.includes('7.6')) {
      truckOpts = { size: 3, width: 2.4, height: 3.5, load: 10.0, weight: 5.0, ...customOpts }
    } else if (name.includes('9.6') || name.includes('重型') || name.includes('高栏') || name.includes('半挂')) {
      truckOpts = { size: 4, width: 2.5, height: 4.0, load: 18.0, weight: 10.0, ...customOpts }
    } else if (name.includes('微型') || name.includes('面包') || name.includes('依维柯')) {
      truckOpts = { size: 1, width: 1.8, height: 2.0, load: 1.5, weight: 1.0, ...customOpts }
    }
    return truckOpts
  }

  /**
   * 单条路线高德货车路网真实测算
   */
  const measureSingleRoute = async (targetRoute, routeKey = 0, options = {}) => {
    const {
      depotLng = 108.318344,
      depotLat = 22.846367,
      returnToDepot = false,
      onSuccess = null,
    } = options

    const pts = targetRoute.points || targetRoute.stops || []
    if (!pts.length) {
      ElMessage.warning('该路线暂无有效配送门店')
      return null
    }

    loadingAmapRouteKey.value = routeKey
    try {
      const origin = [Number(depotLng), Number(depotLat)]
      const waypoints = pts.map((p) => [Number(p.lng || p.longitude), Number(p.lat || p.latitude)])
      const isReturn = returnToDepot ?? false

      const searchOrigin = origin
      const searchDest = isReturn ? origin : waypoints[waypoints.length - 1]
      const searchWaypoints = isReturn ? waypoints : waypoints.slice(0, -1)

      const truckOpts = getTruckParams(targetRoute.truck_name || targetRoute.vehicle_name)
      const res = await planTruckDrivingRoute(searchOrigin, searchDest, searchWaypoints, truckOpts)

      const realKm = Number((res.distance / 1000).toFixed(1))
      const realDurationSec = res.time || 0
      const tolls = res.tolls || 0
      const detailedPath = res.path || []

      // 写入路线对象（兼容不同视图字段命名）
      targetRoute.amap_distance = realKm
      targetRoute.distance = realKm
      targetRoute.distance_km = realKm
      targetRoute.amap_duration = realDurationSec
      targetRoute.amap_tolls = tolls
      targetRoute.toll = tolls
      targetRoute.amap_path = detailedPath
      targetRoute.detailed_polyline = detailedPath

      if (targetRoute.raw_route) {
        targetRoute.raw_route.amap_distance = realKm
        targetRoute.raw_route.distance = realKm
        targetRoute.raw_route.amap_duration = realDurationSec
        targetRoute.raw_route.amap_tolls = tolls
        targetRoute.raw_route.amap_path = detailedPath
        targetRoute.raw_route.detailed_polyline = detailedPath
      }

      if (typeof onSuccess === 'function') {
        onSuccess(targetRoute, res)
      }

      return {
        distanceKm: realKm,
        durationSeconds: realDurationSec,
        tolls,
        path: detailedPath,
      }
    } catch (err) {
      console.error('[useRouteMeasure] AMap Truck Driving Error:', err)
      ElMessage.error(`高德路网测算失败: ${err.message || err}`)
      throw err
    } finally {
      loadingAmapRouteKey.value = null
    }
  }

  /**
   * 批量一键高德货车路网真实测算
   */
  const batchMeasureRoutes = async (routesList, options = {}) => {
    if (!routesList || !routesList.length) {
      ElMessage.warning('当前暂无可测算路线，请先执行路线规划')
      return
    }

    const {
      depotLng = 108.318344,
      depotLat = 22.846367,
      returnToDepot = false,
      onProgress = null,
      onSingleSuccess = null,
      onAllCompleted = null,
    } = options

    batchMeasuring.value = true
    measureSummary.value = null
    const total = routesList.length
    measureProgress.value = { current: 0, total, percent: 0, currentRouteName: '' }

    let successCount = 0
    let totalDist = 0
    let totalDurationSec = 0
    let totalTolls = 0

    try {
      for (let i = 0; i < routesList.length; i++) {
        const r = routesList[i]
        const rName = r.day ? `${r.day} 路线 ${r.day_route_idx + 1}` : `路线 ${i + 1}`
        measureProgress.value.current = i + 1
        measureProgress.value.currentRouteName = rName
        measureProgress.value.percent = Math.round(((i + 1) / total) * 100)

        if (typeof onProgress === 'function') {
          onProgress(measureProgress.value)
        }

        try {
          const res = await measureSingleRoute(r, i, {
            depotLng,
            depotLat,
            returnToDepot,
            onSuccess: onSingleSuccess,
          })
          if (res) {
            successCount++
            totalDist += res.distanceKm
            totalDurationSec += res.durationSeconds
            totalTolls += res.tolls
          }
        } catch (e) {
          console.warn(`[useRouteMeasure] 路线 ${i + 1} 测算失败，继续下一条:`, e)
        }

        // 避免高德 API 频控超限 (QPS 保护)
        if (i < routesList.length - 1) {
          await new Promise((resolve) => setTimeout(resolve, 350))
        }
      }

      measureSummary.value = {
        successCount,
        total,
        totalDist: Number(totalDist.toFixed(1)),
        totalDurationFormatted: formatDuration(totalDurationSec),
        totalTolls,
      }

      ElMessage.success(
        `🎉 批量路网测算完成！成功测算 ${successCount}/${total} 条线路，实测总里程 ${totalDist.toFixed(1)} km，过路费 ¥${totalTolls}`
      )

      if (typeof onAllCompleted === 'function') {
        onAllCompleted(measureSummary.value)
      }

      return measureSummary.value
    } finally {
      batchMeasuring.value = false
    }
  }

  return {
    loadingAmapRouteKey,
    batchMeasuring,
    measureProgress,
    measureSummary,
    getTruckParams,
    measureSingleRoute,
    batchMeasureRoutes,
  }
}
