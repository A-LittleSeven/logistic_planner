/**
 * useRouteExport.js
 * 统一多工作表路线规划与精细化单日快递方案 Excel 导出引擎
 */

import * as XLSX from 'xlsx'
import { ElMessage } from 'element-plus'
import { useRouteOptimizer } from './useRouteOptimizer.js'
import { formatDuration } from '../utils/constants.js'

export function useRouteExport() {
  const { getStoreScheduleDays, getStoreExpressDays, isStoreExpressOnDay } = useRouteOptimizer()

  /**
   * 导出规划方案至 Excel (支持全周/单日多路线与精细单日快递直发门店)
   */
  const exportRoutesToExcel = ({
    planName = '物流规划方案',
    versionNumber = 1,
    stores = [],
    routes = [],
    allWeekRoutes = [],
    customFilename = '',
  } = {}) => {
    if (!stores || !stores.length) {
      ElMessage.warning('当前暂无可导出的门店或路线数据')
      return false
    }

    try {
      const wb = XLSX.utils.book_new()

      // 1. Stores & Schedule Sheet (规划门店与排班)
      const storeRows = stores.map((s, idx) => {
        const scheduleDays = getStoreScheduleDays(s)
        const expressDays = getStoreExpressDays(s)
        const truckDays = scheduleDays.filter((d) => !expressDays.includes(d))

        let deliveryMode = '常规货车'
        if (expressDays.length > 0) {
          if (truckDays.length === 0) {
            deliveryMode = '全周快递直发'
          } else {
            deliveryMode = '混合(部分日快递)'
          }
        }

        return {
          序号: idx + 1,
          门店编码: s.shop_code || '',
          门店名称: s.name || '',
          所属店群: s.cluster_id !== undefined ? `店群 ${Number(s.cluster_id) + 1}` : '未划分',
          周作业日: s.schedule_day || s.delivery_days_str || '未排班',
          配送模式: deliveryMode,
          货车配送日: truckDays.join(', ') || (expressDays.length ? '无' : s.delivery_days_str || '未排班'),
          快递直发日: expressDays.join(', ') || '无',
          日均箱数: Number(s.avg_loads ?? s.weight ?? s.demand ?? 10),
          配送频次: Number(s.frequency || 1),
          本外埠: Number(s.is_homepot) === 1 ? '本埠' : '外埠',
          行政区划: s.district || '',
          经度: s.lng ?? s.longitude ?? '',
          纬度: s.lat ?? s.latitude ?? '',
          详细地址: s.address || '',
        }
      })

      const wsStores = XLSX.utils.json_to_sheet(storeRows)
      wsStores['!cols'] = [
        { wch: 8 },
        { wch: 14 },
        { wch: 20 },
        { wch: 12 },
        { wch: 16 },
        { wch: 16 },
        { wch: 18 },
        { wch: 18 },
        { wch: 10 },
        { wch: 10 },
        { wch: 10 },
        { wch: 14 },
        { wch: 12 },
        { wch: 12 },
        { wch: 28 },
      ]
      XLSX.utils.book_append_sheet(wb, wsStores, '规划门店与排班')

      // 2. Routes & Express Details Sheet (路线规划与快递明细)
      const exportRoutesList = allWeekRoutes.length ? allWeekRoutes : routes
      const hasExpressStores = stores.some((s) => getStoreExpressDays(s).length > 0)

      if (exportRoutesList.length || hasExpressStores) {
        const routeRows = []

        // Regular Truck Routes
        exportRoutesList.forEach((r, rIdx) => {
          const routeDay = r.day || '全周'
          const routeNumber = r.day
            ? `${r.day} 路线 ${(r.day_route_idx !== undefined ? r.day_route_idx + 1 : rIdx + 1)}`
            : `路线-${rIdx + 1}`
          const distanceVal = r.amap_distance ? r.amap_distance : (r.distance_km || r.distance || 0)
          const durationVal = r.amap_duration ? formatDuration(r.amap_duration) : '--'
          const tollVal = r.amap_tolls ?? r.toll ?? 0
          const storeList = r.points || r.stops || []

          storeList.forEach((p, seq) => {
            routeRows.push({
              周作业日: routeDay,
              路线编号: routeNumber,
              配送方式: '常规货车',
              车型: r.vehicle_name || r.truck_name || '默认车型',
              到店顺序: seq + 1,
              门店编码: p.shop_code || '',
              门店名称: p.name || '',
              单店运量_箱: Number(p.avg_loads ?? p.weight ?? p.demand ?? 10),
              本外埠: Number(p.is_homepot) === 1 ? '本埠' : '外埠',
              路线总箱数: r.load ?? r.total_weight ?? r.avg_loads ?? 0,
              测算里程_km: distanceVal,
              预估耗时: durationVal,
              高速路费_元: tollVal,
              行政区划: p.district || '',
              经度: p.lng ?? p.longitude ?? '',
              纬度: p.lat ?? p.latitude ?? '',
              详细地址: p.address || '',
            })
          })
        })

        // Day-Specific Express Direct Delivery Stores
        stores.forEach((p) => {
          const expDays = getStoreExpressDays(p)
          expDays.forEach((expDay) => {
            routeRows.push({
              周作业日: expDay,
              路线编号: '📦 快递直发',
              配送方式: '快递直发',
              车型: '第三方快递/物流',
              到店顺序: '--',
              门店编码: p.shop_code || '',
              门店名称: p.name || '',
              单店运量_箱: Number(p.avg_loads ?? p.weight ?? p.demand ?? 10),
              本外埠: Number(p.is_homepot) === 1 ? '本埠' : '外埠',
              路线总箱数: '--',
              测算里程_km: '--',
              预估耗时: '--',
              高速路费_元: 0,
              行政区划: p.district || '',
              经度: p.lng ?? p.longitude ?? '',
              纬度: p.lat ?? p.latitude ?? '',
              详细地址: p.address || '',
            })
          })
        })

        const wsRoutes = XLSX.utils.json_to_sheet(routeRows)
        wsRoutes['!cols'] = [
          { wch: 10 },
          { wch: 16 },
          { wch: 12 },
          { wch: 14 },
          { wch: 10 },
          { wch: 14 },
          { wch: 22 },
          { wch: 12 },
          { wch: 10 },
          { wch: 12 },
          { wch: 14 },
          { wch: 14 },
          { wch: 12 },
          { wch: 14 },
          { wch: 12 },
          { wch: 12 },
          { wch: 28 },
        ]
        XLSX.utils.book_append_sheet(wb, wsRoutes, '路线规划与快递明细')
      }

      const fileName = customFilename || `${planName}_V${versionNumber}_规划方案_${new Date().toISOString().slice(0, 10)}.xlsx`
      XLSX.writeFile(wb, fileName)
      ElMessage.success('已成功导出包含车辆路线与单日精细化快递直发方案的 Excel 文件！')
      return true
    } catch (err) {
      ElMessage.error(`导出失败: ${err.message}`)
      return false
    }
  }

  return {
    exportRoutesToExcel,
  }
}
