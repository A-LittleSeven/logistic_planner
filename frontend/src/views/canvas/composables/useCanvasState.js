import { ref, shallowRef, reactive, computed, provide, inject } from 'vue'
import { DAYS_LIST, getDistanceBetweenCoords } from '../../../utils/constants.js'
import { useRouteOptimizer } from '../../../composables/useRouteOptimizer.js'
import { ElMessage } from 'element-plus'

const CanvasStateSymbol = Symbol('CanvasState')

export function provideCanvasState(canvasId) {
  const {
    isStoreExpressOnDay,
    setStoreExpressOnDay,
    removeExpressFromRoutes,
    clearRouteMeasureCache,
    optimizeRouteWith2Opt,
    recalculateRouteMetrics: optRecalculateRouteMetrics,
  } = useRouteOptimizer()

  // 1. Canvas Entity & Version Info
  const canvas = reactive({
    id: null,
    canvas_id: canvasId,
    name: '',
    dc_code: '',
    depot_name: '',
    depot_lng: 108.36654,
    depot_lat: 22.81700,
    depot_address: '',
    description: '',
    stage: 'INIT',
  })

  const currentVersion = ref(null)
  const versionList = shallowRef([])
  const activeStage = ref('clustering')

  // 2. Core Business Data
  const stores = ref([])
  const clusteringResult = ref(null)
  const scheduleResult = ref(null)
  const dailyResults = ref({})
  const trucks = ref([
    { name: '4.2米厢式货车', capacity: 230, count: 20, cost_per_km: 3.5 },
  ])

  // Filters & State Flags
  const selectedScheduleDay = ref('周一')
  const selectedRoutingDay = ref('周一')
  const isScheduleOutdated = ref(false)
  const isRoutingOutdated = ref(false)
  const routingMeasureSummary = ref(null)

  // 3. Algorithm Parameters
  const clusteringAlgorithm = ref('kmeans')
  const clusteringK = ref(6)
  const minZoneSize = ref(5)
  const maxZoneSize = ref(30)

  const loadPersistedOptions = (storageKey, defaults) => {
    try {
      const raw = localStorage.getItem(storageKey)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (parsed && typeof parsed === 'object') {
          return { ...defaults, ...parsed }
        }
      }
    } catch (e) {
      console.warn(`[useCanvasState] 读取缓存配置 ${storageKey} 失败:`, e)
    }
    return { ...defaults }
  }

  const defaultScheduleOptions = {
    max_truck_capacity_rate: 0.96,
    search_n_neighbor: 1,
    detour_thres: 500,
    dist_thres: 0.9,
    one_way_dist_max: 40,
    work_days: 6,
  }
  const scheduleOptions = ref(loadPersistedOptions('canvas_schedule_options', defaultScheduleOptions))

  const defaultRouteOptions = {
    max_capacity_rate: 1.10,
    time_limit_seconds: 60,
    return_to_depot: false,
  }
  const routeOptions = ref(loadPersistedOptions('canvas_route_options', defaultRouteOptions))

  // 4. Map & Box Selection Tool
  const mapPanelRef = shallowRef(null)
  const amapInstance = shallowRef(null)
  const isSelecting = ref(false)
  const selectedPointIndices = ref([])
  const expandedRouteIndices = ref(new Set())
  const highlightedRouteIdx = ref(null)
  const highlightedClusterId = ref(null)

  // 5. Computeds
  const totalLoads = computed(() => {
    return Math.round(
      stores.value.reduce((acc, s) => {
        let freq = Number(s.frequency)
        if (!freq || isNaN(freq)) {
          const dStr = s.delivery_days_str || s.schedule_day || ''
          freq = dStr ? dStr.split(',').filter(Boolean).length : 1
        }
        const freqVal = Math.max(1, freq || 1)
        const loadVal = Number(s.avg_loads || s.weight || s.demand || 10)
        return acc + loadVal * freqVal
      }, 0)
    )
  })

  const activeScheduleStores = computed(() => {
    if (!hasScheduleComputed.value) return []
    if (selectedScheduleDay.value === '全部') return stores.value
    return stores.value.filter((s) => {
      const dStr = s.schedule_day || s.delivery_days_str || ''
      return dStr.includes(selectedScheduleDay.value)
    })
  })

  const activeDayLoad = computed(() => {
    return Math.round(activeScheduleStores.value.reduce((acc, s) => acc + Number(s.avg_loads || 10), 0))
  })

  const activeDayPoints = computed(() => {
    if (!hasScheduleComputed.value) return []
    if (selectedRoutingDay.value === '全部') {
      return stores.value
    }
    return stores.value.filter((s) => {
      const dStr = s.schedule_day || s.delivery_days_str || ''
      return dStr.includes(selectedRoutingDay.value)
    })
  })

  const allWeekRoutes = computed(() => {
    const list = []
    DAYS_LIST.forEach((day) => {
      const dayRes = dailyResults.value[day]
      if (dayRes?.routes?.length) {
        dayRes.routes.forEach((r, rIdx) => {
          list.push({
            ...r,
            day,
            day_route_idx: rIdx,
            route_title: `${day} 路线 ${rIdx + 1}`,
          })
        })
      }
    })
    return list
  })

  const currentDisplayRoutes = computed(() => {
    if (selectedRoutingDay.value === '全部') {
      return allWeekRoutes.value
    }
    const dayRoutes = dailyResults.value[selectedRoutingDay.value]?.routes
    if (dayRoutes && dayRoutes.length) {
      return dayRoutes
    }
    // Fallback: If legacy canvas only has dailyResults['全部'], fallback gracefully
    if (dailyResults.value['全部']?.routes?.length && !Object.keys(dailyResults.value).some((k) => k !== '全部')) {
      return dailyResults.value['全部'].routes
    }
    return dayRoutes || []
  })

  const routes = computed(() => currentDisplayRoutes.value)

  const totalDistanceKm = computed(() => {
    const sum = currentDisplayRoutes.value.reduce((acc, r) => acc + (Number(r.distance ?? r.distance_km) || 0), 0)
    return sum.toFixed(1)
  })

  const hasClusteringComputed = computed(() => Boolean(clusteringResult.value?.clusters?.length))

  const hasScheduleComputed = computed(() => {
    if (isScheduleOutdated.value) return false
    return Boolean(
      scheduleResult.value ||
      stores.value.some((s) => Boolean(s.schedule_day || s.delivery_days_str))
    )
  })

  const hasRoutingComputed = computed(() => {
    if (isRoutingOutdated.value || !hasScheduleComputed.value) return false
    return routes.value.length > 0
  })

  const expressStores = computed(() => {
    if (!hasScheduleComputed.value || isRoutingOutdated.value) return []
    if (selectedRoutingDay.value === '全部') {
      return stores.value.filter((s) => isStoreExpressOnDay(s, '全部', stores.value))
    }
    return stores.value.filter((s) => {
      const matchSchedule = (s.schedule_day || s.delivery_days_str || '').includes(selectedRoutingDay.value)
      return isStoreExpressOnDay(s, selectedRoutingDay.value, stores.value) && (matchSchedule || !s.delivery_days_str)
    })
  })

  // 6. Methods & Event Triggers
  const recalculateClusterMetrics = () => {
    const clusters = clusteringResult.value?.clusters
    if (!clusters?.length) return
    const depot = {
      lng: Number(canvas.depot_lng || 108.36654),
      lat: Number(canvas.depot_lat || 22.817),
    }
    const round = (n) => Math.round(n * 1e5) / 1e5
    clusters.forEach((c) => {
      const idxs = stores.value
        .map((s, idx) => (Number(s.cluster_id) === Number(c.cluster_id) ? idx : -1))
        .filter((idx) => idx !== -1)
      c.size = idxs.length
      c.point_indices = idxs
      if (idxs.length > 0) {
        const sumLng = idxs.reduce((sum, idx) => sum + Number(stores.value[idx].lng), 0)
        const sumLat = idxs.reduce((sum, idx) => sum + Number(stores.value[idx].lat), 0)
        c.center = { lng: round(sumLng / idxs.length), lat: round(sumLat / idxs.length) }
        c.cdist_warehouse = getDistanceBetweenCoords(c.center, depot)
        idxs.forEach((idx) => {
          stores.value[idx].cdist_warehouse = round(c.cdist_warehouse)
          stores.value[idx].center_lng = c.center.lng
          stores.value[idx].center_lat = c.center.lat
        })
      } else {
        c.center = null
        c.cdist_warehouse = 0
      }
    })
    clusteringResult.value = {
      ...clusteringResult.value,
      clusters: [...clusters],
    }
  }

  const invalidateDownstreamStagesFromClustering = (reason = '店群规划已更新') => {
    isScheduleOutdated.value = true
    isRoutingOutdated.value = true
    scheduleResult.value = null
    selectedScheduleDay.value = '周一'
    highlightedClusterId.value = null

    // 深度清洗门店实体层上的下游脏数据 (彻底清除幽灵排班/快递/路线)
    if (Array.isArray(stores.value)) {
      stores.value.forEach((s) => {
        s.schedule_day = ''
        s.delivery_days_str = ''
        s.is_express = 0
        s.express_days = []
        delete s.route_idx
        delete s.route_color
      })
    }

    dailyResults.value = {}
    selectedRoutingDay.value = '周一'
    highlightedRouteIdx.value = null
    expandedRouteIndices.value.clear()

    // 清空路网底层测算内存缓存
    if (typeof clearRouteMeasureCache === 'function') {
      clearRouteMeasureCache()
    }

    canvas.stage = 'CLUSTERED'
  }

  const invalidateDownstreamStagesFromScheduling = (reason = '周排班规划已更新') => {
    isScheduleOutdated.value = false
    isRoutingOutdated.value = true
    dailyResults.value = {}
    selectedRoutingDay.value = '周一'
    highlightedRouteIdx.value = null
    expandedRouteIndices.value.clear()

    // 清除下游路线与快递专属标记
    if (Array.isArray(stores.value)) {
      stores.value.forEach((s) => {
        s.is_express = 0
        s.express_days = []
        delete s.route_idx
        delete s.route_color
      })
    }

    // 清空路网底层测算内存缓存
    if (typeof clearRouteMeasureCache === 'function') {
      clearRouteMeasureCache()
    }

    canvas.stage = 'SCHEDULED'
  }

  const recalculateRouteMetrics = () => {
    const allDays = [...new Set([...DAYS_LIST, '全部', ...Object.keys(dailyResults.value)])]
    optRecalculateRouteMetrics(
      dailyResults.value,
      allDays,
      canvas.depot_lng,
      canvas.depot_lat,
      Boolean(routeOptions.value?.return_to_depot)
    )
  }

  const handleToggleStoreExpress = (row, day, isExp, renderMapFn = null) => {
    const targetDay = day || (selectedRoutingDay.value !== '全部' ? selectedRoutingDay.value : '全部')
    setStoreExpressOnDay(row, targetDay, isExp, stores.value)

    if (Number(isExp) === 1) {
      const daysToClean = targetDay === '全部' ? DAYS_LIST : [targetDay]
      const isReturn = routeOptions.value?.return_to_depot ?? false
      const depotPos = { lng: Number(canvas.depot_lng), lat: Number(canvas.depot_lat) }
      removeExpressFromRoutes(dailyResults.value, daysToClean, { depotPos, isReturn, allStores: stores.value })
      recalculateRouteMetrics()
    }
    dailyResults.value = { ...dailyResults.value }
    if (renderMapFn) renderMapFn()
    ElMessage.success(`门店「${row.name}」在【${targetDay}】已更新为: ${Number(isExp) === 1 ? '📦 快递直发' : '🚛 货车配送'}`)
  }

  const handleBatchSetStoresExpress = (targets, day, isExp, renderMapFn = null) => {
    if (!targets.length) return
    const targetDay = day || selectedRoutingDay.value || '全部'
    targets.forEach((p) => {
      setStoreExpressOnDay(p, targetDay, isExp, stores.value)
    })
    if (Number(isExp) === 1) {
      const daysToClean = targetDay === '全部' ? DAYS_LIST : [targetDay]
      const isReturn = routeOptions.value?.return_to_depot ?? false
      const depotPos = { lng: Number(canvas.depot_lng), lat: Number(canvas.depot_lat) }
      removeExpressFromRoutes(dailyResults.value, daysToClean, { depotPos, isReturn, allStores: stores.value })
      recalculateRouteMetrics()
    }
    dailyResults.value = { ...dailyResults.value }
    if (renderMapFn) renderMapFn()
    ElMessage.success(`已将 ${targets.length} 家门店在【${targetDay}】批量更新为: ${Number(isExp) === 1 ? '📦 快递直发' : '🚛 货车配送'}`)
  }

  const handleRestoreExpressStore = (store, renderMapFn = null) => {
    const targetDay = selectedRoutingDay.value || '全部'
    setStoreExpressOnDay(store, targetDay, 0, stores.value)
    dailyResults.value = { ...dailyResults.value }
    if (renderMapFn) renderMapFn()
    ElMessage.success(`已恢复门店「${store.name}」在【${targetDay}】为货车配送`)
  }

  const moveStoreBetweenRoutes = (sourceRouteIdx, storeSeq, targetRouteVal, renderMapFn = null) => {
    const displayList = currentDisplayRoutes.value
    const sourceRoute = displayList[sourceRouteIdx]
    if (!sourceRoute) return

    const realSourceRoute = sourceRoute.raw_route || sourceRoute
    const sourceDay = sourceRoute.day || (selectedRoutingDay.value !== '全部' ? selectedRoutingDay.value : Object.keys(dailyResults.value)[0] || '周一')

    if (!realSourceRoute || !realSourceRoute.points) return
    const movedStore = realSourceRoute.points[storeSeq]
    if (!movedStore) return

    const isReturn = Boolean(routeOptions.value?.return_to_depot)
    const depotPos = { lng: Number(canvas.depot_lng), lat: Number(canvas.depot_lat) }

    // 1. 从源路线剥离该站点
    realSourceRoute.points.splice(storeSeq, 1)
    realSourceRoute.stops = realSourceRoute.points
    clearRouteMeasureCache(realSourceRoute)
    if (realSourceRoute.points.length > 2) {
      realSourceRoute.points = optimizeRouteWith2Opt(realSourceRoute.points, isReturn, { depot: depotPos })
      realSourceRoute.stops = realSourceRoute.points
    }

    // 2. 分支处理目标操作
    if (targetRouteVal === 'express') {
      const targetDay = sourceDay || selectedRoutingDay.value || '全部'
      setStoreExpressOnDay(movedStore, targetDay, 1, stores.value)

      const daysToClean = targetDay === '全部' ? DAYS_LIST : [targetDay]
      removeExpressFromRoutes(dailyResults.value, daysToClean, { depotPos, isReturn, allStores: stores.value })

      recalculateRouteMetrics()
      dailyResults.value = { ...dailyResults.value }
      if (renderMapFn) renderMapFn()
      ElMessage.success(`已将门店「${movedStore.name}」在【${targetDay}】设为快递直发，已从货车路线中剔除`)
      return
    } else if (targetRouteVal === 'new') {
      const targetDay = sourceDay || (selectedRoutingDay.value !== '全部' ? selectedRoutingDay.value : '周一')
      if (!dailyResults.value[targetDay]) {
        dailyResults.value[targetDay] = { routes: [], day: targetDay }
      }
      const targetDayRoutes = dailyResults.value[targetDay].routes || []
      const defaultTruck = trucks.value[0]?.name || '4.2米厢式货车'
      const newRouteIdx = targetDayRoutes.length
      const newRoute = {
        day: targetDay,
        day_route_idx: newRouteIdx,
        route_title: `${targetDay} 路线 ${newRouteIdx + 1}`,
        truck_name: defaultTruck,
        vehicle_name: defaultTruck,
        points: [movedStore],
        stops: [movedStore],
        load: Number(movedStore.avg_loads || movedStore.demand || 10),
        total_weight: Number(movedStore.avg_loads || movedStore.demand || 10),
        distance: 0,
        distance_km: 0,
        is_homepot: Number(movedStore.is_homepot ?? 0),
        return_to_depot: isReturn,
      }
      targetDayRoutes.push(newRoute)
      dailyResults.value[targetDay].routes = targetDayRoutes

      const allDays = [...new Set([...DAYS_LIST, '全部', ...Object.keys(dailyResults.value)])]
      allDays.forEach((d) => {
        if (dailyResults.value[d]?.routes) {
          dailyResults.value[d].routes = dailyResults.value[d].routes.filter((r) => r.points && r.points.length > 0)
        }
      })
      recalculateRouteMetrics()
      dailyResults.value = { ...dailyResults.value }
      if (renderMapFn) renderMapFn()
      ElMessage.success(`已在【${targetDay}】为门店「${movedStore.name}」创建新独立路线`)
    } else {
      const targetIdx = Number(targetRouteVal)
      const targetDisplayRoute = displayList[targetIdx]
      if (targetDisplayRoute) {
        const realTargetRoute = targetDisplayRoute.raw_route || targetDisplayRoute
        if (!realTargetRoute.points) realTargetRoute.points = []
        realTargetRoute.points.push(movedStore)
        realTargetRoute.stops = realTargetRoute.points
        clearRouteMeasureCache(realTargetRoute)
        if (realTargetRoute.points.length > 2) {
          realTargetRoute.points = optimizeRouteWith2Opt(realTargetRoute.points, isReturn, { depot: depotPos })
          realTargetRoute.stops = realTargetRoute.points
        }

        const allDays = [...new Set([...DAYS_LIST, '全部', ...Object.keys(dailyResults.value)])]
        allDays.forEach((d) => {
          if (dailyResults.value[d]?.routes) {
            dailyResults.value[d].routes = dailyResults.value[d].routes.filter((r) => r.points && r.points.length > 0)
          }
        })
        recalculateRouteMetrics()
        dailyResults.value = { ...dailyResults.value }
        if (renderMapFn) renderMapFn()
        ElMessage.success(`已将门店「${movedStore.name}」转移至目标路线并重新测算顺路里程！`)
      }
    }
  }

  const state = {
    canvas,
    currentVersion,
    versionList,
    activeStage,
    stores,
    clusteringResult,
    scheduleResult,
    dailyResults,
    trucks,
    selectedScheduleDay,
    selectedRoutingDay,
    isScheduleOutdated,
    isRoutingOutdated,
    clusteringAlgorithm,
    clusteringK,
    minZoneSize,
    maxZoneSize,
    defaultScheduleOptions,
    scheduleOptions,
    defaultRouteOptions,
    routeOptions,
    mapPanelRef,
    amapInstance,
    isSelecting,
    selectedPointIndices,
    expandedRouteIndices,
    highlightedRouteIdx,
    highlightedClusterId,
    // Computeds
    totalLoads,
    activeScheduleStores,
    activeDayLoad,
    activeDayPoints,
    allWeekRoutes,
    currentDisplayRoutes,
    routes,
    totalDistanceKm,
    routingMeasureSummary,
    hasClusteringComputed,
    hasScheduleComputed,
    hasRoutingComputed,
    expressStores,
    // Methods
    recalculateClusterMetrics,
    invalidateDownstreamStagesFromClustering,
    invalidateDownstreamStagesFromScheduling,
    recalculateRouteMetrics,
    handleToggleStoreExpress,
    handleBatchSetStoresExpress,
    handleRestoreExpressStore,
    moveStoreBetweenRoutes,
  }

  provide(CanvasStateSymbol, state)
  return state
}

export function useCanvasState() {
  const state = inject(CanvasStateSymbol)
  if (!state) {
    throw new Error('useCanvasState must be used within a component wrapped by provideCanvasState')
  }
  return state
}
