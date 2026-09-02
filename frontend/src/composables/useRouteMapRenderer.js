/**
 * useRouteMapRenderer.js
 * 路线规划与地图调度全要素生命周期渲染引擎 (中心仓 / 高精路网折线 / 站点次序标 / 快递📦标 / 动态弹窗)
 */

import { dotHtml, ROUTE_COLORS } from '../utils/mapMarkers.js'
import { useRouteOptimizer } from './useRouteOptimizer.js'

export function useRouteMapRenderer() {
  const { isStoreExpressOnDay, getStoreScheduleDays, getStoreExpressDays } = useRouteOptimizer()

  /**
   * 渲染路线规划地图所有要素
   */
  const renderRouteMapLayers = ({
    amap,
    mapPanel,
    depot = { name: '中心仓', lng: 0, lat: 0 },
    routes = [],
    allStores = [],
    expressStores = [],
    unassignedStores = [],
    highlightedRouteIdx = null,
    selectedPointIndices = [],
    currentDay = '全部',
    openInfoWindowAt,
    onStoreRouteTransfer,
    onStoreExpressToggle,
    onStoreHomepotToggle,
  }) => {
    if (!amap || !mapPanel) return
    const A = amap
    mapPanel.clearAll()

    const routeOverlays = []

    // 1. Draw Central Depot Marker (起点中心仓)
    if (depot && depot.lng && depot.lat) {
      const { content, offset } = dotHtml({ text: '仓', color: '#0f172a', size: 30 })
      const depotMarker = new A.Marker({
        position: [Number(depot.lng), Number(depot.lat)],
        content,
        offset: new A.Pixel(offset[0], offset[1]),
        zIndex: 200,
        title: depot.name || '配送中心 (中心仓)',
      })

      depotMarker.on('click', () => {
        const infoContent = `
          <div style="padding: 10px 14px; font-size: 12px; line-height: 1.5; color: #1e293b; min-width: 200px; background: white; border-radius: 8px;">
            <div style="font-weight: 700; font-size: 14px; color: #0f172a; margin-bottom: 4px;">
              🏬 ${depot.name || '起点中心仓'}
            </div>
            <div style="font-size: 11px; color: #64748b;">
              坐标: [${Number(depot.lng).toFixed(4)}, ${Number(depot.lat).toFixed(4)}]
            </div>
            <div style="font-size: 11px; color: #10b981; margin-top: 2px;">
              状态: 车辆出发与返程点
            </div>
          </div>
        `
        if (openInfoWindowAt) {
          openInfoWindowAt(depotMarker, infoContent)
        }
      })

      mapPanel.addOverlay(depotMarker)
    }

    // 2. Draw Unassigned Non-Express Stores (未排班 / 未分配路线门店)
    if (unassignedStores && unassignedStores.length) {
      unassignedStores.forEach((p) => {
        if (!p || p.lng === '' || p.lat === '') return
        const globalIdx = allStores.indexOf(p)
        const isBoxSelected = selectedPointIndices.includes(globalIdx)
        const isHp = Number(p.is_homepot) === 1
        const storeDays = getStoreScheduleDays(p)
        const activeDayForStore = (currentDay !== '全部') ? currentDay : (storeDays[0] || '全部')

        const { content, offset } = dotHtml({
          text: '·',
          color: isBoxSelected ? '#0d9488' : '#94a3b8',
          size: isBoxSelected ? 24 : 18,
        })

        const marker = new A.Marker({
          position: [Number(p.lng ?? p.longitude), Number(p.lat ?? p.latitude)],
          content: isBoxSelected
            ? `<div style="box-shadow: 0 0 10px #0d9488; border-radius: 50%; outline: 3px solid #0d9488;">${content}</div>`
            : `<div style="opacity: 0.85;">${content}</div>`,
          offset: new A.Pixel(offset[0], offset[1]),
          title: `${p.name} (未分配路线)`,
          zIndex: isBoxSelected ? 120 : 60,
        })

        marker.on('click', () => {
          const infoContent = `
            <div style="padding: 10px 14px; font-size: 12px; line-height: 1.5; color: #1e293b; min-width: 220px; background: white; border-radius: 8px;">
              <div style="font-weight: 700; font-size: 13px; color: #64748b; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center;">
                <span>${p.name || '门店'} (未分配)</span>
                <span style="font-size: 10px; padding: 1px 6px; border-radius: 4px; font-weight: 600; ${isHp ? 'background: #e0f2fe; color: #0369a1;' : 'background: #fef3c7; color: #b45309;'}">
                  ${isHp ? '🏠 本埠' : '🚗 外埠'}
                </span>
              </div>
              <div style="font-size: 11px; color: #64748b;">
                <span>所属作业日: <strong>${p.schedule_day || p.delivery_days_str || '未排班'}</strong> · 运量: <strong>${p.avg_loads || p.demand || 10}</strong> 箱</span>
              </div>
              <div style="margin-top: 8px; border-top: 1px dashed #e2e8f0; padding-top: 6px;">
                <button onclick="window.updateStoreExpressDay(${globalIdx}, '${activeDayForStore}', 1)" style="width: 100%; font-size: 11px; padding: 4px 6px; border: 1px solid #d8b4fe; border-radius: 4px; background: #faf5ff; color: #7c3aed; font-weight: 600; cursor: pointer;">
                  📦 快递直发
                </button>
              </div>
            </div>
          `
          if (openInfoWindowAt) openInfoWindowAt(marker, infoContent)
        })

        mapPanel.addOverlay(marker)
      })
    }

    // 3. Draw Express Stores Markers (📦 快递直发门店)
    if (expressStores && expressStores.length) {
      expressStores.forEach((p) => {
        if (!p || p.lng === '' || p.lat === '') return
        const globalIdx = allStores ? allStores.findIndex((s) => s === p || (s.shop_code && s.shop_code === p.shop_code) || s.name === p.name) : -1
        const isBoxSelected = selectedPointIndices.includes(globalIdx)
        const storeDays = getStoreScheduleDays(p)
        const expressDays = getStoreExpressDays(p)
        const activeDayForStore = (currentDay !== '全部') ? currentDay : (expressDays[0] || '全部')

        const { content, offset } = dotHtml({
          text: '📦',
          color: isBoxSelected ? '#0d9488' : '#8b5cf6',
          size: isBoxSelected ? 28 : 24,
        })

        const marker = new A.Marker({
          position: [Number(p.lng ?? p.longitude), Number(p.lat ?? p.latitude)],
          content: isBoxSelected
            ? `<div style="box-shadow: 0 0 12px #0d9488; border-radius: 50%; outline: 3px solid #0d9488;">${content}</div>`
            : content,
          offset: new A.Pixel(offset[0], offset[1]),
          zIndex: isBoxSelected ? 130 : 95,
          title: `${p.name} (📦 快递直发)`,
        })

        marker.on('click', () => {
          const infoContent = `
            <div style="padding: 10px 14px; font-size: 12px; line-height: 1.5; color: #1e293b; min-width: 230px; background: white; border-radius: 8px;">
              <div style="font-weight: 700; font-size: 13px; color: #7c3aed; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center;">
                <span>${p.name || '门店'}</span>
                <span style="font-size: 10px; background: #f3e8ff; color: #7c3aed; padding: 1px 6px; border-radius: 4px; font-weight: 600;">📦 快递直发</span>
              </div>
              <div style="font-size: 11px; color: #64748b;">
                <span>快递作业日: <strong style="color: #7c3aed;">${expressDays.join(', ') || activeDayForStore}</strong> (单日运量: <strong>${p.avg_loads || p.demand || 10}</strong> 箱)</span>
              </div>
              <div style="font-size: 11px; color: #64748b; margin-top: 2px;">
                <span>全周作业安排: ${storeDays.join(', ') || '未排班'}</span>
              </div>
              <div style="margin-top: 8px; border-top: 1px dashed #e2e8f0; padding-top: 6px;">
                <button onclick="window.updateStoreExpressDay(${globalIdx}, '${activeDayForStore}', 0)" style="width: 100%; font-size: 11px; padding: 4px 8px; border: 1px solid #86efac; border-radius: 4px; background: #f0fdf4; color: #16a34a; font-weight: 600; cursor: pointer;">
                  🚛 恢复货车配送
                </button>
              </div>
            </div>
          `
          if (openInfoWindowAt) openInfoWindowAt(marker, infoContent)
        })

        mapPanel.addOverlay(marker)
      })
    }

    // 4. Draw Planned Routes & Sequence Markers (常规货车路线与站点序号)
    if (routes && routes.length) {
      const depotPos = [Number(depot.lng), Number(depot.lat)]

      routes.forEach((r, rIdx) => {
        const isHighlighted = highlightedRouteIdx === rIdx
        const isAnyHighlighted = highlightedRouteIdx !== null
        const routeOpacity = isAnyHighlighted ? (isHighlighted ? 1.0 : 0.2) : 0.85
        const routeWeight = isHighlighted ? 6 : (isAnyHighlighted ? 3 : 5)
        const color = ROUTE_COLORS[rIdx % ROUTE_COLORS.length]
        const pts = r.points || r.stops || []
        const routeDay = r.day || currentDay || '全部'

        // Path Coords Priority: detailed_polyline (AMap high precision real road curves) -> amap_path -> pathCoords -> fallback
        let polyPath = null
        if (r.detailed_polyline && r.detailed_polyline.length >= 2) {
          polyPath = r.detailed_polyline
        } else if (r.amap_path && r.amap_path.length >= 2) {
          polyPath = r.amap_path
        } else if (r.pathCoords && r.pathCoords.length >= 2) {
          polyPath = r.pathCoords
        } else {
          polyPath = [depotPos, ...pts.map((p) => [Number(p.lng ?? p.longitude), Number(p.lat ?? p.latitude)])]
          if (r.return_to_depot === true) {
            polyPath.push(depotPos)
          }
        }

        if (polyPath && polyPath.length >= 2) {
          const polyline = new A.Polyline({
            path: polyPath,
            strokeColor: color,
            strokeWeight: routeWeight,
            strokeOpacity: routeOpacity,
            lineJoin: 'round',
            lineCap: 'round',
            showDir: true,
            zIndex: isHighlighted ? 120 : (isAnyHighlighted ? 30 : 60),
          })
          mapPanel.addOverlay(polyline)
        }

        // Draw Route Sequence Markers (1, 2, 3...)
        const routeMarkers = []
        pts.forEach((p, seqIdx) => {
          if (!p || p.lng === '' || p.lat === '') return
          const globalIdx = allStores ? allStores.findIndex((s) => s === p || (s.shop_code && s.shop_code === p.shop_code) || s.name === p.name) : -1
          const isBoxSelected = selectedPointIndices.includes(globalIdx)
          const isHp = Number(p.is_homepot) === 1

          const { content: dotNormal, offset } = dotHtml({
            text: String(seqIdx + 1),
            color: isBoxSelected ? '#0d9488' : color,
            size: isBoxSelected ? 26 : 20,
          })
          const { content: dotHighlight } = dotHtml({
            text: String(seqIdx + 1),
            color: isBoxSelected ? '#0d9488' : color,
            size: 24,
          })

          const marker = new A.Marker({
            position: [Number(p.lng ?? p.longitude), Number(p.lat ?? p.latitude)],
            content: isBoxSelected
              ? `<div style="box-shadow: 0 0 12px #0d9488; border-radius: 50%; outline: 3px solid #0d9488; outline-offset: 2px;">${dotNormal}</div>`
              : `<div style="opacity: ${routeOpacity}; transition: opacity 0.25s;">${isHighlighted ? dotHighlight : dotNormal}</div>`,
            offset: new A.Pixel(offset[0], offset[1]),
            zIndex: isBoxSelected ? 130 : (isHighlighted ? 120 : (isAnyHighlighted ? 35 : 75)),
            title: `${p.name} (${r.day ? r.day + ' ' : ''}路线 ${(r.day_route_idx ?? rIdx) + 1} 第${seqIdx + 1}站)`,
          })

          const otherRoutesOptions = routes
            .map((or, oIdx) => {
              const oTitle = or.day && or.day_route_idx !== undefined ? `${or.day} 路线 ${or.day_route_idx + 1}` : `路线 ${oIdx + 1}`
              return `<option value="${oIdx}" ${oIdx === rIdx ? 'disabled' : ''}>${oTitle} (${or.vehicle_name || or.truck_name || '货车'})</option>`
            })
            .join('')

          marker.on('click', () => {
            const infoContent = `
              <div style="padding: 10px 14px; font-size: 12px; line-height: 1.5; color: #1e293b; min-width: 230px; background: white; border-radius: 8px;">
                <div style="font-weight: 700; font-size: 14px; margin-bottom: 6px; color: #0f172a; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; display: flex; justify-content: space-between; align-items: center;">
                  <span>${p.name || '门店'}</span>
                  <span style="font-size: 10px; padding: 1px 6px; border-radius: 4px; font-weight: 600; ${isHp ? 'background: #e0f2fe; color: #0369a1;' : 'background: #fef3c7; color: #b45309;'}">
                    ${isHp ? '🏠 本埠' : '🚗 外埠'}
                  </span>
                </div>
                <div style="margin-bottom: 4px; color: #64748b;">
                  当前分配: <strong style="color: ${color};">${r.day ? r.day + ' ' : ''}路线 ${(r.day_route_idx ?? rIdx) + 1}</strong> (第 ${seqIdx + 1} 站)
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 11px; color: #64748b; margin-bottom: 6px;">
                  <span>运量: <strong>${p.avg_loads || p.demand || 10}</strong> 箱</span>
                  <span>路线里程: ${r.amap_distance || r.distance_km || r.distance || 0} km</span>
                </div>
                <div style="margin-top: 8px; border-top: 1px dashed #e2e8f0; padding-top: 6px;">
                  <label style="font-size: 11px; font-weight: 600; color: #475569;">转移路线 / 配送方式:</label>
                  <select onchange="window.updateStoreRoute(${rIdx}, ${seqIdx}, this.value)" style="margin-top: 4px; width: 100%; font-size: 11px; padding: 4px; border: 1px solid #0284c7; border-radius: 4px; background: #f0f9ff; color: #0369a1; font-weight: 600; cursor: pointer;">
                    <option value="" disabled selected>选择目标路线 / 方式...</option>
                    ${otherRoutesOptions}
                    <option value="new">+ 新建独立路线</option>
                    <option value="express" style="color: #7c3aed; font-weight: 700;">📦 快递直发</option>
                  </select>
                </div>
              </div>
            `
            if (openInfoWindowAt) openInfoWindowAt(marker, infoContent)
          })

          mapPanel.addOverlay(marker)
          routeMarkers.push({ marker, dotNormal, dotHighlight })
        })

        routeOverlays.push({ polyline: polyPath, markers: routeMarkers })
      })
    }

    return routeOverlays
  }

  return {
    renderRouteMapLayers,
  }
}
