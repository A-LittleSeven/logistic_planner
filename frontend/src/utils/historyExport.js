import * as XLSX from 'xlsx'

/**
 * 安全解析 JSON 字符串
 */
function safeParseJson(data) {
  if (!data) return null
  if (typeof data === 'object') return data
  try {
    return JSON.parse(data)
  } catch (e) {
    return null
  }
}

/**
 * 格式化日期为文件名安全字符串
 */
function formatDateForFilename(dateStr) {
  const d = dateStr ? new Date(dateStr) : new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}`
}

/**
 * 导出历史任务数据为标准 Excel 文件
 * @param {Object} task 历史任务记录对象
 */
export function exportHistoryTaskToExcel(task) {
  if (!task) throw new Error('任务记录为空')

  const taskType = task.task_type
  const result = safeParseJson(task.result) || {}
  const params = safeParseJson(task.parameters) || {}

  const wb = XLSX.utils.book_new()
  const title = params.title || result.title || task.task_id
  const dateStr = formatDateForFilename(task.created_at)

  if (taskType === 'CLUSTERING') {
    exportClusteringTask(wb, result, params)
    const filename = `店群分组方案_${title}_${dateStr}.xlsx`
    XLSX.writeFile(wb, filename)
    return filename
  } else if (taskType === 'CLUSTER_SCHEDULE') {
    exportScheduleTask(wb, result, params)
    const filename = `店群排班方案_${title}_${dateStr}.xlsx`
    XLSX.writeFile(wb, filename)
    return filename
  } else if (taskType === 'ROUTING' || taskType === 'GLOBAL_ROUTING') {
    exportRoutingTask(wb, result, params)
    const filename = `路线规划方案_${title}_${dateStr}.xlsx`
    XLSX.writeFile(wb, filename)
    return filename
  } else {
    // 通用回退导出
    exportGenericTask(wb, result, params)
    const filename = `历史任务数据_${task.task_id}_${dateStr}.xlsx`
    XLSX.writeFile(wb, filename)
    return filename
  }
}

/**
 * 导出店群分组 (CLUSTERING)
 */
function exportClusteringTask(wb, result, params) {
  let rawPoints = result.points || params.points || []
  const assignments = result.assignments || []
  const clusters = result.clusters || []

  // 如果 points 嵌套在 clusters 里
  if ((!rawPoints || rawPoints.length === 0) && Array.isArray(clusters) && clusters.length > 0) {
    rawPoints = []
    clusters.forEach((c) => {
      if (Array.isArray(c.points)) {
        c.points.forEach((p) => {
          rawPoints.push({
            ...p,
            cluster_id: p.cluster_id !== undefined ? p.cluster_id : c.cluster_id
          })
        })
      }
    })
  }

  const storeRows = rawPoints.map((p, idx) => {
    let clusterId = p.cluster_id
    if (clusterId === undefined && assignments.length > idx) {
      clusterId = assignments[idx]
    }
    const isHome = p.is_homepot === 1 || p.is_homepot === true || p.is_homepot === '本埠' || p.is_homepot === '1'

    return {
      '门店编号': p.shop_code || p.dept_id || `S${String(idx + 1).padStart(3, '0')}`,
      '门店名称': p.name || p.shop_name || `门店_${idx + 1}`,
      '所属仓库': p.dc_code || p.warehouse_name || params.dc_code || '-',
      '所属店群': clusterId !== undefined ? `店群 ${clusterId}` : '未分配',
      '所属行政区': p.district || '-',
      '日均箱数': Number(p.avg_loads || p.weight || 0),
      '周配送频次': Number(p.frequency || p.freq || 1),
      '本外埠': isHome ? '本埠' : '外埠',
      '经度': p.lng !== undefined ? Number(p.lng) : '',
      '纬度': p.lat !== undefined ? Number(p.lat) : '',
      '卸货耗时_小时': p.service_time !== undefined ? Number(p.service_time) : 0.5,
      '指定车型': p.available_truck || '',
      '详细地址': p.address || ''
    }
  })

  const wsStores = XLSX.utils.json_to_sheet(storeRows)
  XLSX.utils.book_append_sheet(wb, wsStores, '门店分组明细')

  // 2. 店群统计汇总
  const clusterMap = new Map()
  storeRows.forEach((r) => {
    const cName = r['所属店群']
    if (!clusterMap.has(cName)) {
      clusterMap.set(cName, { count: 0, totalDemand: 0, homeCount: 0, outpostCount: 0 })
    }
    const stat = clusterMap.get(cName)
    stat.count++
    stat.totalDemand += Number(r['日均箱数'] || 0)
    if (r['本外埠'] === '本埠') stat.homeCount++
    else stat.outpostCount++
  })

  const summaryRows = []
  if (Array.isArray(clusters) && clusters.length > 0) {
    clusters.forEach((c) => {
      const cId = c.cluster_id !== undefined ? `店群 ${c.cluster_id}` : `店群 ${c.id || '-'}`
      const stat = clusterMap.get(cId) || { count: c.points_count || (c.points ? c.points.length : 0), totalDemand: c.total_demand || 0, homeCount: 0, outpostCount: 0 }
      summaryRows.push({
        '店群编号': cId,
        '门店数量': stat.count,
        '日均总需求(箱)': stat.totalDemand,
        '本埠门店数': stat.homeCount,
        '外埠门店数': stat.outpostCount,
        '中心经度': c.center && c.center[0] ? Number(c.center[0].toFixed(6)) : (c.center_lng || '-'),
        '中心纬度': c.center && c.center[1] ? Number(c.center[1].toFixed(6)) : (c.center_lat || '-'),
        '平均辐射距离(km)': c.avg_distance_km ? Number(c.avg_distance_km.toFixed(2)) : (c.avg_dist || '-')
      })
    })
  } else {
    for (const [cId, stat] of clusterMap.entries()) {
      summaryRows.push({
        '店群编号': cId,
        '门店数量': stat.count,
        '日均总需求(箱)': stat.totalDemand,
        '本埠门店数': stat.homeCount,
        '外埠门店数': stat.outpostCount
      })
    }
  }

  if (summaryRows.length > 0) {
    const wsSummary = XLSX.utils.json_to_sheet(summaryRows)
    XLSX.utils.book_append_sheet(wb, wsSummary, '店群指标汇总')
  }
}

/**
 * 导出店群排班 (CLUSTER_SCHEDULE)
 */
function exportScheduleTask(wb, result, params) {
  const points = result.points || params.points || []

  const storeRows = points.map((p, idx) => {
    const isHome = p.is_homepot === 1 || p.is_homepot === true || p.is_homepot === '本埠' || p.is_homepot === '1'
    let daysStr = p.delivery_days_str || ''
    if (!daysStr && Array.isArray(p.delivery_days)) {
      daysStr = p.delivery_days.join(',')
    }

    return {
      '门店编号': p.shop_code || p.dept_id || `S${String(idx + 1).padStart(3, '0')}`,
      '门店名称': p.name || p.shop_name || `门店_${idx + 1}`,
      '所属仓库': p.dc_code || p.warehouse_name || params.dc_code || '-',
      '所属店群': p.cluster_id !== undefined ? `店群 ${p.cluster_id}` : '-',
      '所属行政区': p.district || '-',
      '计划配送作业日': daysStr || '周一',
      '周配送频次': Number(p.frequency || p.freq || (daysStr ? daysStr.split(',').length : 1)),
      '日均箱数': Number(p.avg_loads || p.weight || 0),
      '本外埠': isHome ? '本埠' : '外埠',
      '经度': p.lng !== undefined ? Number(p.lng) : '',
      '纬度': p.lat !== undefined ? Number(p.lat) : '',
      '卸货耗时_小时': p.service_time !== undefined ? Number(p.service_time) : 0.5,
      '指定车型': p.available_truck || '',
      '详细地址': p.address || ''
    }
  })

  const wsStores = XLSX.utils.json_to_sheet(storeRows)
  XLSX.utils.book_append_sheet(wb, wsStores, '门店排班明细')

  // 周一至周日运力分布汇总
  const dayStats = {
    '周一': { storeCount: 0, totalLoads: 0, homeCount: 0, outpostCount: 0 },
    '周二': { storeCount: 0, totalLoads: 0, homeCount: 0, outpostCount: 0 },
    '周三': { storeCount: 0, totalLoads: 0, homeCount: 0, outpostCount: 0 },
    '周四': { storeCount: 0, totalLoads: 0, homeCount: 0, outpostCount: 0 },
    '周五': { storeCount: 0, totalLoads: 0, homeCount: 0, outpostCount: 0 },
    '周六': { storeCount: 0, totalLoads: 0, homeCount: 0, outpostCount: 0 },
    '周日': { storeCount: 0, totalLoads: 0, homeCount: 0, outpostCount: 0 }
  }

  storeRows.forEach((r) => {
    const days = (r['计划配送作业日'] || '').split(/[,，、\s]+/).filter(Boolean)
    const loads = Number(r['日均箱数'] || 0)
    const isHome = r['本外埠'] === '本埠'

    days.forEach((d) => {
      if (dayStats[d]) {
        dayStats[d].storeCount++
        dayStats[d].totalLoads += loads
        if (isHome) dayStats[d].homeCount++
        else dayStats[d].outpostCount++
      }
    })
  })

  const daySummaryRows = Object.entries(dayStats).map(([day, stat]) => ({
    '计划作业日': day,
    '配送门店数': stat.storeCount,
    '计划配送总箱数': stat.totalLoads,
    '本埠门店数': stat.homeCount,
    '外埠门店数': stat.outpostCount
  }))

  const wsDaySummary = XLSX.utils.json_to_sheet(daySummaryRows)
  XLSX.utils.book_append_sheet(wb, wsDaySummary, '每日运力汇总')
}

/**
 * 智能解析路线中的门店列表（兼容对象数组、索引列表、带仓库/不带仓库等各种格式）
 */
function resolveStopsForRoute(r, dayPoints, allPoints) {
  // 1. 如果 r.stops 已经是包含具体门店属性的对象列表
  if (Array.isArray(r.stops) && r.stops.length > 0 && typeof r.stops[0] === 'object') {
    return r.stops.filter((s) => !s.is_depot)
  }

  // 2. 如果 r.points 已经是包含具体门店属性的对象列表
  if (Array.isArray(r.points) && r.points.length > 0 && typeof r.points[0] === 'object') {
    return r.points.filter((s) => !s.is_depot)
  }

  // 3. 如果 r.order 是索引数组 (如 [0, 3, 5, 2, 0] 或 [1, 4, 2])
  if (Array.isArray(r.order) && r.order.length > 0) {
    const primaryPool = dayPoints && dayPoints.length > 0 ? dayPoints : allPoints
    const candidateStops = []

    // 优先按照 primaryPool[idx] 匹配
    r.order.forEach((idx) => {
      if (idx === -1 || idx === null || idx === undefined) return
      const pt = primaryPool[idx]
      if (pt && !pt.is_depot) {
        candidateStops.push(pt)
      }
    })

    if (candidateStops.length > 0) {
      return candidateStops
    }

    // 次选：若 primaryPool 包含 depot，且 order 排除 depot 后的索引
    const nonDepotPool = primaryPool.filter((p) => !p.is_depot)
    r.order.forEach((idx) => {
      if (idx >= 0 && idx < nonDepotPool.length) {
        candidateStops.push(nonDepotPool[idx])
      }
    })

    if (candidateStops.length > 0) {
      return candidateStops
    }
  }

  // 4. 回退检查 r.stops 为索引数组的情况
  if (Array.isArray(r.stops) && r.stops.length > 0 && typeof r.stops[0] === 'number') {
    const primaryPool = dayPoints && dayPoints.length > 0 ? dayPoints : allPoints
    return r.stops.map((idx) => primaryPool[idx]).filter((p) => p && !p.is_depot)
  }

  return []
}

/**
 * 匹配或推断车型容量
 */
function resolveTruckCapacity(truckName, trucks, r) {
  if (r.capacity && Number(r.capacity) > 0) return Number(r.capacity)
  if (r.truck && r.truck.capacity && Number(r.truck.capacity) > 0) return Number(r.truck.capacity)

  if (Array.isArray(trucks) && trucks.length > 0 && truckName) {
    const found = trucks.find(
      (t) => t.name === truckName || truckName.includes(t.name) || t.name.includes(truckName)
    )
    if (found && found.capacity) return Number(found.capacity)
  }

  const nameStr = String(truckName || '')
  if (nameStr.includes('4.2')) return 230
  if (nameStr.includes('6.8')) return 450
  if (nameStr.includes('9.6')) return 800

  return 0
}

/**
 * 导出路线规划 (ROUTING / GLOBAL_ROUTING)
 */
function exportRoutingTask(wb, result, params) {
  const routes = result.routes || []
  const dailyPlans = result.daily_results || result.daily_plans || {}
  const allPoints = result.points || params.points || []
  const trucks = result.trucks || params.trucks || []

  const routeSummaryRows = []
  const stopDetailRows = []

  const DAYS_ORDER = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

  const processSingleRoute = (r, routeIndex, dayName) => {
    const truckName = (r.truck && r.truck.name) || r.truck_name || '默认车型'
    const capacity = resolveTruckCapacity(truckName, trucks, r)
    
    // 提取途经门店
    const dayPts = dayName && dayName !== '全部' && dayName !== '单日规划'
      ? allPoints.filter((p) => p.delivery_days_str && p.delivery_days_str.includes(dayName))
      : allPoints
    const stops = resolveStopsForRoute(r, dayPts, allPoints)

    // 计算装载与里程
    let load = r.total_load !== undefined ? r.total_load : (r.load !== undefined ? r.load : 0)
    if (load === 0 && stops.length > 0) {
      load = stops.reduce((sum, s) => sum + Number(s.avg_loads || s.weight || s.demand || 0), 0)
    }

    const dist = r.total_distance !== undefined ? r.total_distance : (r.distance !== undefined ? r.distance : 0)

    // 高德测算数据
    let amapDist = '-'
    if (r.amap_distance !== undefined && r.amap_distance !== null && r.amap_distance !== '') {
      const numDist = Number(r.amap_distance)
      amapDist = numDist > 1000 ? (numDist / 1000).toFixed(1) : numDist.toFixed(1)
    }

    let amapTime = '-'
    if (r.amap_duration !== undefined && r.amap_duration !== null && r.amap_duration !== '') {
      const mins = Math.round(Number(r.amap_duration))
      if (mins < 60) amapTime = `${mins} 分钟`
      else amapTime = `${Math.floor(mins / 60)}小时${mins % 60 > 0 ? (mins % 60) + '分' : ''}`
    } else if (r.amap_time !== undefined && r.amap_time !== null && r.amap_time !== '') {
      const mins = Math.round(Number(r.amap_time) / 60)
      if (mins < 60) amapTime = `${mins} 分钟`
      else amapTime = `${Math.floor(mins / 60)}小时${mins % 60 > 0 ? (mins % 60) + '分' : ''}`
    }

    const amapTolls = (r.amap_tolls !== undefined && r.amap_tolls !== null && r.amap_tolls !== '')
      ? `${r.amap_tolls} 元`
      : '-'

    const routeLabel = dayName && dayName !== '单日规划' ? `${dayName} 路线 ${routeIndex + 1}` : `路线 ${routeIndex + 1}`

    routeSummaryRows.push({
      '路线编号': routeLabel,
      '计划作业日': dayName || '单日规划',
      '指派车型': truckName,
      '额定容量(箱)': capacity > 0 ? capacity : '-',
      '实际装载(箱)': Number(load.toFixed ? load.toFixed(0) : load),
      '装载率': capacity > 0 ? `${((load / capacity) * 100).toFixed(1)}%` : '-',
      '配送门店数': stops.length,
      '规划里程(km)': Number(Number(dist).toFixed(1)),
      '高德路网里程(km)': amapDist,
      '高德预估耗时': amapTime,
      '高速过路费': amapTolls
    })

    // 到店次序明细
    stops.forEach((s, seqIdx) => {
      const isHome = s.is_homepot === 1 || s.is_homepot === true || s.is_homepot === '本埠' || s.is_homepot === '1'
      stopDetailRows.push({
        '路线编号': routeLabel,
        '计划作业日': dayName || '单日规划',
        '到店顺序': seqIdx + 1,
        '门店编号': s.shop_code || s.dept_id || `S${String(seqIdx + 1).padStart(3, '0')}`,
        '门店名称': s.name || s.shop_name || `门店_${seqIdx + 1}`,
        '所属仓库': s.dc_code || s.warehouse_name || params.depot_name || '-',
        '所属店群': s.cluster_id !== undefined ? `店群 ${s.cluster_id}` : '-',
        '所属行政区': s.district || '-',
        '到店需求(箱)': Number(s.avg_loads || s.weight || s.demand || 0),
        '本外埠': isHome ? '本埠' : '外埠',
        '卸货耗时_小时': s.service_time !== undefined ? Number(s.service_time) : 0.5,
        '经度': s.lng !== undefined ? Number(s.lng) : '',
        '纬度': s.lat !== undefined ? Number(s.lat) : '',
        '详细地址': s.address || ''
      })
    })
  }

  // 1. 如果存在按周多日排班结果
  const hasDailyPlans = Object.keys(dailyPlans).length > 0
  if (hasDailyPlans) {
    DAYS_ORDER.forEach((day) => {
      const plan = dailyPlans[day]
      if (plan && Array.isArray(plan.routes) && plan.routes.length > 0) {
        plan.routes.forEach((r, rIdx) => {
          processSingleRoute(r, rIdx, day)
        })
      }
    })
    // 补充非标准星期名称的排班
    for (const [day, plan] of Object.entries(dailyPlans)) {
      if (!DAYS_ORDER.includes(day) && plan && Array.isArray(plan.routes)) {
        plan.routes.forEach((r, rIdx) => {
          processSingleRoute(r, rIdx, day)
        })
      }
    }
  } else if (Array.isArray(routes) && routes.length > 0) {
    const singleDay = params.day || result.day || '单日规划'
    routes.forEach((r, rIdx) => {
      processSingleRoute(r, rIdx, singleDay)
    })
  }

  if (routeSummaryRows.length > 0) {
    const wsRoutes = XLSX.utils.json_to_sheet(routeSummaryRows)
    XLSX.utils.book_append_sheet(wb, wsRoutes, '路线指标汇总')
  }

  if (stopDetailRows.length > 0) {
    const wsStops = XLSX.utils.json_to_sheet(stopDetailRows)
    XLSX.utils.book_append_sheet(wb, wsStops, '各路线到店次序明细')
  }
}

/**
 * 通用回退导出
 */
function exportGenericTask(wb, result, params) {
  const genericRows = [
    { '配置项目': '任务参数 JSON', '内容': JSON.stringify(params) },
    { '配置项目': '计算结果 JSON', '内容': JSON.stringify(result) }
  ]
  const ws = XLSX.utils.json_to_sheet(genericRows)
  XLSX.utils.book_append_sheet(wb, ws, '任务原始数据')
}
