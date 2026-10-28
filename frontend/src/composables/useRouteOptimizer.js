import { getDistanceBetweenCoords } from '../utils/constants.js'

export function useRouteOptimizer() {
  /**
   * 计算地球表面两点间球面距离 (km)，统一复用 constants.js 算法
   */
  const calcDistanceKm = (lng1, lat1, lng2, lat2) => {
    return getDistanceBetweenCoords({ lng: lng1, lat: lat1 }, { lng: lng2, lat: lat2 })
  }

  /**
   * 获取门店的所有排班作业日数组
   */
  const getStoreScheduleDays = (store) => {
    if (!store) return []
    const dayStr = store.schedule_day || store.delivery_days_str || ''
    if (!dayStr) return []
    return dayStr
      .split(/[,，、 ]+/)
      .map((d) => d.trim())
      .filter(Boolean)
  }

  /**
   * 标准化获取门店走快递的作业日列表 (express_days)
   */
  const getStoreExpressDays = (store) => {
    if (!store) return []
    if (Array.isArray(store.express_days)) {
      return [...store.express_days]
    }
    if (typeof store.express_days === 'string' && store.express_days.trim()) {
      return store.express_days
        .split(/[,，、 ]+/)
        .map((d) => d.trim())
        .filter(Boolean)
    }
    if (Number(store.is_express) === 1) {
      const scheduleDays = getStoreScheduleDays(store)
      return scheduleDays.length ? scheduleDays : ['全部']
    }
    return []
  }

  /**
   * 判断门店在指定作业日是否为快递直发
   */
  const isStoreExpressOnDay = (store, day, allStores = null) => {
    if (!store) return false
    let target = store
    if (allStores && Array.isArray(allStores) && (!store.express_days || !store.express_days.length) && !store.is_express) {
      const match = allStores.find((s) => (s.shop_code && s.shop_code === store.shop_code) || s.name === store.name)
      if (match) target = match
    }
    const expDays = getStoreExpressDays(target)
    if (!expDays.length) return false
    if (day === '全部') return expDays.length > 0
    return expDays.includes(day) || expDays.includes('全部')
  }

  /**
   * 设置门店在指定作业日下的快递直发状态
   */
  const setStoreExpressOnDay = (store, day, isExpress, allStores = null) => {
    if (!store) return
    const isExp = Number(isExpress) === 1
    const scheduleDays = getStoreScheduleDays(store)
    let currentExpDays = getStoreExpressDays(store)

    if (day === '全部') {
      if (isExp) {
        currentExpDays = scheduleDays.length ? [...scheduleDays] : ['全部']
      } else {
        currentExpDays = []
      }
    } else {
      if (isExp) {
        if (!currentExpDays.includes(day)) {
          currentExpDays.push(day)
        }
      } else {
        currentExpDays = currentExpDays.filter((d) => d !== day && d !== '全部')
      }
    }

    store.express_days = currentExpDays
    store.is_express = currentExpDays.length > 0 ? 1 : 0

    if (allStores && Array.isArray(allStores)) {
      const match = allStores.find((s) => (s.shop_code && s.shop_code === store.shop_code) || s.name === store.name)
      if (match && match !== store) {
        match.express_days = [...currentExpDays]
        match.is_express = store.is_express
      }
    }
  }

  /**
   * 2-Opt 路径交叉消除与顺路优化算法 (完美适配对象点列与索引编号点列)
   * @param {Array} pointsOrOrder 站点列表 (对象数组或索引数组)
   * @param {Boolean} isReturn 是否闭环返回起点
   * @param {Object|Function} optionsOrCoordFn 配置对象 { depot, getCoordFn } 或坐标解析函数
   */
  const optimizeRouteWith2Opt = (pointsOrOrder = [], isReturn = true, optionsOrCoordFn = {}) => {
    if (!pointsOrOrder || pointsOrOrder.length <= 1) return pointsOrOrder ? [...pointsOrOrder] : []

    let getCoordFn = null
    let depot = null

    if (typeof optionsOrCoordFn === 'function') {
      getCoordFn = optionsOrCoordFn
    } else if (typeof optionsOrCoordFn === 'object' && optionsOrCoordFn !== null) {
      getCoordFn = optionsOrCoordFn.getCoordFn || null
      depot = optionsOrCoordFn.depot || null
    }

    const isIndexArray = typeof pointsOrOrder[0] === 'number' || pointsOrOrder.some((x) => x === -1)

    // CASE 1: 索引数组模式 (e.g. [-1, 0, 2, -1] 或 [0, 2])
    if (isIndexArray) {
      let route = [...pointsOrOrder]
      if (route.length <= 2) return route

      const resolveCoord = (idx) => {
        if (getCoordFn) return getCoordFn(idx)
        return { lng: 0, lat: 0 }
      }

      const calcDist = (idx1, idx2) => {
        const c1 = resolveCoord(idx1)
        const c2 = resolveCoord(idx2)
        if ((!c1.lng && !c1.lat) || (!c2.lng && !c2.lat)) return 0
        return calcDistanceKm(c1.lng, c1.lat, c2.lng, c2.lat)
      }

      const isClosedLoop = isReturn || route[route.length - 1] === -1
      const endLimit = isClosedLoop ? route.length - 2 : route.length - 1
      let improved = true
      let iters = 0

      while (improved && iters < 60) {
        improved = false
        iters++
        for (let i = 1; i < endLimit; i++) {
          const jLimit = isClosedLoop ? route.length - 1 : route.length
          for (let j = i + 1; j < jLimit; j++) {
            const a = route[i - 1]
            const b = route[i]
            const c = route[j]
            const d = j + 1 < route.length ? route[j + 1] : null

            let curDist = calcDist(a, b)
            let newDist = calcDist(a, c)
            if (d !== null) {
              curDist += calcDist(c, d)
              newDist += calcDist(b, d)
            }

            if (newDist + 1e-6 < curDist) {
              const sub = route.slice(i, j + 1).reverse()
              route.splice(i, sub.length, ...sub)
              improved = true
              break
            }
          }
          if (improved) break
        }
      }
      return route
    }

    // CASE 2: 对象点列模式 (e.g. [ {lng, lat}, {lng, lat}, ... ])
    const pts = [...pointsOrOrder]
    if (pts.length <= 1) return pts

    const resolveObjCoord = (p) => ({
      lng: Number(p.lng ?? p.longitude ?? 0),
      lat: Number(p.lat ?? p.latitude ?? 0),
    })

    const calcObjDist = (p1, p2) => {
      const c1 = resolveObjCoord(p1)
      const c2 = resolveObjCoord(p2)
      return calcDistanceKm(c1.lng, c1.lat, c2.lng, c2.lat)
    }

    // 若传入了中心仓坐标，将中心仓作为起终点锚定优化
    let route = []
    let hasDepot = false
    if (depot && depot.lng && depot.lat) {
      hasDepot = true
      route = [depot, ...pts]
      if (isReturn) {
        route.push(depot)
      }
    } else {
      route = [...pts]
    }

    const isClosedLoop = isReturn && hasDepot
    const startIdx = hasDepot ? 1 : 1
    const endLimit = isClosedLoop ? route.length - 2 : route.length - 1
    let improved = true
    let iters = 0

    while (improved && iters < 60) {
      improved = false
      iters++
      for (let i = startIdx; i < endLimit; i++) {
        const jLimit = isClosedLoop ? route.length - 1 : route.length
        for (let j = i + 1; j < jLimit; j++) {
          const a = route[i - 1]
          const b = route[i]
          const c = route[j]
          const d = j + 1 < route.length ? route[j + 1] : null

          let curDist = calcObjDist(a, b)
          let newDist = calcObjDist(a, c)
          if (d !== null) {
            curDist += calcObjDist(c, d)
            newDist += calcObjDist(b, d)
          }

          if (newDist + 1e-6 < curDist) {
            const sub = route.slice(i, j + 1).reverse()
            route.splice(i, sub.length, ...sub)
            improved = true
            break
          }
        }
        if (improved) break
      }
    }

    if (hasDepot) {
      return isReturn ? route.slice(1, -1) : route.slice(1)
    }
    return route
  }

  /**
   * 清除路线上的高德测算缓存与失真索引
   */
  const clearRouteMeasureCache = (route) => {
    if (!route) return
    const keys = ['detailed_polyline', 'amap_path', 'amap_distance', 'amap_duration', 'amap_tolls', 'pathCoords', 'poly_key', 'order']
    keys.forEach((k) => delete route[k])
  }

  /**
   * 从每日路线中批量移除已设为快递直发的门店，并执行 2-Opt 顺路优化与缓存清理
   * @param {Object} dailyResultsObj dailyResults 响应式对象的 .value
   * @param {Array<string>} daysToClean 需要清理的作业日数组
   * @param {Object} options { depotPos: {lng, lat}, isReturn: boolean, extraRoutes: Array, allStores: Array }
   */
  const removeExpressFromRoutes = (dailyResultsObj, daysToClean, options = {}) => {
    const { depotPos = null, isReturn = false, extraRoutes = null, allStores = [] } = options
    if (!dailyResultsObj && !extraRoutes) return

    const storeIsExpress = (st, dayName) => {
      if (isStoreExpressOnDay(st, dayName)) return true
      if (allStores && Array.isArray(allStores) && allStores.length) {
        const match = allStores.find((s) => (s.shop_code && s.shop_code === st.shop_code) || s.name === st.name)
        if (match && isStoreExpressOnDay(match, dayName)) return true
      }
      return false
    }

    const cleanList = (routesList, dayName) => {
      if (!Array.isArray(routesList)) return
      routesList.forEach((r) => {
        if (r.points) {
          const prevLen = r.points.length
          r.points = r.points.filter((st) => !storeIsExpress(st, dayName))
          r.stops = r.points
          if (r.points.length !== prevLen) {
            clearRouteMeasureCache(r)
            if (r.points.length > 2) {
              r.points = optimizeRouteWith2Opt(r.points, isReturn, depotPos ? { depot: depotPos } : {})
              r.stops = r.points
            }
          }
        }
      })
    }

    if (dailyResultsObj) {
      const allDays = [...new Set([...(daysToClean || []), '全部', ...Object.keys(dailyResultsObj)])]
      allDays.forEach((d) => {
        if (dailyResultsObj[d]?.routes) {
          cleanList(dailyResultsObj[d].routes, d)
          dailyResultsObj[d].routes = dailyResultsObj[d].routes.filter((r) => (r.points || []).length > 0)
        }
      })
    }

    if (extraRoutes && Array.isArray(extraRoutes)) {
      const targetDay = daysToClean && daysToClean.length === 1 ? daysToClean[0] : '全部'
      cleanList(extraRoutes, targetDay)
    }
  }

  /**
   * 解析路线的本外埠属性 (1 本埠 / 0 外埠)，若无则尝试通过首个站点的属性判断
   */
  const resolveHomepot = (route, fallbackStores = []) => {
    if (route.is_homepot !== undefined && route.is_homepot !== null) return Number(route.is_homepot)
    return fallbackStores.length > 0 ? Number(fallbackStores[0].is_homepot ?? 0) : 0
  }

  /**
   * 重建并补全路线的关键节点数据与基本属性，适配对象、停靠点及索引等多种持久化存储格式
   * @param {Array} routesList 需要重构的原始路线数组
   * @param {Array} targetStores (可选) 用于通过索引映射提取对象的基准门店池
   * @param {Object} options (可选) 配置项，如 { defaultReturnToDepot: boolean }
   */
  const hydrateRoutePoints = (routesList, targetStores = [], options = {}) => {
    if (!routesList || !Array.isArray(routesList)) return []
    const defaultReturn = options.defaultReturnToDepot ?? false
    const allStorePool = options.allStores || targetStores || []

    // 构建门店快速查找索引字典 (shop_code 和 name 双重索引)，保证 O(1) 匹配
    const storeMap = new Map()
    if (Array.isArray(allStorePool)) {
      allStorePool.forEach((s) => {
        if (!s) return
        if (s.shop_code) storeMap.set(String(s.shop_code), s)
        if (s.name) storeMap.set(String(s.name), s)
      })
    }

    const findStore = (p) => {
      if (!p) return null
      if (typeof p === 'string') {
        return storeMap.get(p) || null
      }
      if (typeof p === 'object') {
        if (p.shop_code && storeMap.has(String(p.shop_code))) {
          return storeMap.get(String(p.shop_code))
        }
        if (p.name && storeMap.has(String(p.name))) {
          return storeMap.get(String(p.name))
        }
      }
      return p
    }

    return routesList.map((r, rIdx) => {
      let pts = []
      // 1. 优先读取路线持久化的最新途经站点列表 (r.stops 或 r.points)
      const stopList =
        (Array.isArray(r.stops) && r.stops.length > 0 && r.stops) ||
        (Array.isArray(r.points) && r.points.length > 0 && r.points) ||
        null

      if (stopList) {
        pts = stopList.map(findStore).filter(Boolean)
      } else if (Array.isArray(r.order) && r.order.length > 0) {
        // 2. 仅在历史版本完全无 stops 标识时，走旧 order 兜底
        const storeIndices = r.order.filter((idx) => idx !== -1)
        pts = storeIndices.map((idx) => targetStores[idx]).filter(Boolean)
      }

      const isHp = resolveHomepot(r, pts)
      const isReturn = r.return_to_depot !== undefined ? Boolean(r.return_to_depot) : Boolean(defaultReturn)

      return {
        ...r,
        points: pts,
        stops: pts,
        is_homepot: isHp,
        return_to_depot: isReturn,
        truck_name: r.truck_name || r.vehicle_name || `货车 ${rIdx + 1}`,
        vehicle_name: r.vehicle_name || r.truck_name || `货车 ${rIdx + 1}`,
        distance: Number(r.distance ?? r.distance_km ?? 0),
        distance_km: Number(r.distance ?? r.distance_km ?? 0),
        load: Number(r.load ?? r.avg_loads ?? 0),
      }
    })
  }

  /**
   * 重新汇总所有路线的总里程与装载量
   */
  const recalculateRouteMetrics = (dailyResults, daysList, depotLng, depotLat, returnToDepot = true) => {
    if (!dailyResults) return
    const dLng = Number(depotLng)
    const dLat = Number(depotLat)

    daysList.forEach((day) => {
      const dayRes = dailyResults[day]
      if (dayRes?.routes?.length) {
        let dayTotalDist = 0
        dayRes.routes.forEach((r) => {
          const pts = r.points || r.stops || []
          const totalLoad = pts.reduce((sum, p) => {
            const w = p.avg_loads ?? p.weight ?? p.demand ?? p.loads ?? 10
            return sum + (Number(w) || 0)
          }, 0)

          r.load = Math.round(totalLoad)
          r.total_weight = Math.round(totalLoad)
          r.avg_loads = Math.round(totalLoad)

          if (!r.amap_distance) {
            let distKm = 0
            if (pts.length > 0) {
              let prevPos = [dLng, dLat]
              pts.forEach((p) => {
                const currPos = [Number(p.lng ?? p.longitude ?? 0), Number(p.lat ?? p.latitude ?? 0)]
                if (currPos[0] && currPos[1]) {
                  distKm += calcDistanceKm(prevPos[0], prevPos[1], currPos[0], currPos[1])
                  prevPos = currPos
                }
              })
              if (returnToDepot && prevPos[0] && prevPos[1]) {
                distKm += calcDistanceKm(prevPos[0], prevPos[1], dLng, dLat)
              }
            }
            r.distance = Number((distKm * 1.3).toFixed(1))
            r.distance_km = r.distance
          }
          dayTotalDist += (Number(r.amap_distance || r.distance) || 0)
        })
        dayRes.total_distance = Number(dayTotalDist.toFixed(1))
      }
    })
  }

  return {
    calcDistanceKm,
    getStoreScheduleDays,
    getStoreExpressDays,
    isStoreExpressOnDay,
    setStoreExpressOnDay,
    optimizeRouteWith2Opt,
    clearRouteMeasureCache,
    removeExpressFromRoutes,
    resolveHomepot,
    hydrateRoutePoints,
    recalculateRouteMetrics,
  }
}
