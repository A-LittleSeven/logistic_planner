import { ref } from 'vue'
import { loadAMap } from '../../../composables/useAMap.js'
import { useRouteMapRenderer } from '../../../composables/useRouteMapRenderer.js'
import { useRouteOptimizer } from '../../../composables/useRouteOptimizer.js'
import { dotHtml, CLUSTER_COLORS, DAY_COLORS, escapeHtml } from '../../../utils/mapMarkers.js'


export function useCanvasMapLayers(state) {
  const {
    canvas,
    activeStage,
    stores,
    clusteringResult,
    selectedScheduleDay,
    selectedRoutingDay,
    hasScheduleComputed,
    activeDayPoints,
    currentDisplayRoutes,
    highlightedRouteIdx,
    selectedPointIndices,
    isSelecting,
    mapPanelRef,
    amapInstance,
  } = state

  const { renderRouteMapLayers } = useRouteMapRenderer()
  const { isStoreExpressOnDay } = useRouteOptimizer()

  const routeOverlays = []
  let sharedInfoWindow = null
  let mouseToolInstance = null

  const getClusterColor = (cId) => CLUSTER_COLORS[(cId || 0) % CLUSTER_COLORS.length]

  const getClusterLoad = (cId) => {
    const list = stores.value.filter((s) => s.cluster_id === cId)
    return Math.round(list.reduce((acc, s) => acc + Number(s.avg_loads || 10), 0))
  }

  const getValidScheduleOptionsForFreq = (freq) => {
    const f = Math.round(Number(freq || 1))
    if (f === 2) {
      return [
        { label: '周一 / 周四 (2次/周: 间隔3天)', value: '周一,周四' },
        { label: '周二 / 周五 (2次/周: 间隔3天)', value: '周二,周五' },
        { label: '周三 / 周六 (2次/周: 间隔3天)', value: '周三,周六' },
      ]
    } else if (f === 3) {
      return [
        { label: '周一 / 周三 / 周五 (3次/周: 1/3/5)', value: '周一,周三,周五' },
        { label: '周二 / 周四 / 周六 (3次/周: 2/4/6)', value: '周二,周四,周六' },
      ]
    } else if (f === 4) {
      return [
        { label: '周一 / 周二 / 周四 / 周五 (4次/周)', value: '周一,周二,周四,周五' },
      ]
    } else if (f === 6) {
      return [
        { label: '周一 至 周六 (6次/周)', value: '周一,周二,周三,周四,周五,周六' },
      ]
    } else if (f >= 7) {
      return [
        { label: '每天配送 (7次/周: 周一至周日)', value: '周一,周二,周三,周四,周五,周六,周日' },
      ]
    } else {
      return [
        { label: '周一 (1次/周)', value: '周一' },
        { label: '周二 (1次/周)', value: '周二' },
        { label: '周三 (1次/周)', value: '周三' },
        { label: '周四 (1次/周)', value: '周四' },
        { label: '周五 (1次/周)', value: '周五' },
        { label: '周六 (1次/周)', value: '周六' },
        { label: '周日 (1次/周)', value: '周日' },
      ]
    }
  }

  const openInfoWindowAt = (marker, html) => {
    const mapObj = mapPanelRef.value?.getMap()
    const A = amapInstance.value
    if (!mapObj || !A) return
    if (!sharedInfoWindow) {
      sharedInfoWindow = new A.InfoWindow({ offset: new A.Pixel(0, -18), closeWhenClickMap: true })
    }
    sharedInfoWindow.setContent(html)
    sharedInfoWindow.open(mapObj, marker.getPosition())
  }

  const applyRouteHighlight = (changedIdxs) => {
    const isAny = highlightedRouteIdx.value !== null
    routeOverlays.forEach((ro, rIdx) => {
      const isHl = highlightedRouteIdx.value === rIdx
      ro.polyline.setOptions({
        strokeOpacity: isAny ? (isHl ? 1.0 : 0.2) : 0.85,
        strokeWeight: isHl ? 6 : (isAny ? 3 : 5),
        zIndex: isHl ? 120 : (isAny ? 40 : 80),
      })
      ro.markers.forEach((m) => {
        if (changedIdxs.includes(rIdx)) m.marker.setContent(isHl ? m.dotHighlight : m.dotNormal)
        if (m.marker.setOpacity) m.marker.setOpacity(isAny ? (isHl ? 1.0 : 0.3) : 1.0)
        if (m.marker.setzIndex) m.marker.setzIndex(isHl ? 130 : 100)
      })
    })
  }

  const toggleHighlightRoute = (rIdx, fitBounds = true) => {
    const prev = highlightedRouteIdx.value
    highlightedRouteIdx.value = prev === rIdx ? null : rIdx
    if (routeOverlays.length) {
      applyRouteHighlight([prev, rIdx].filter((i) => i !== null))
    } else {
      renderMap()
    }

    if (fitBounds && highlightedRouteIdx.value !== null && routeOverlays[rIdx]) {
      const ro = routeOverlays[rIdx]
      const mapObj = mapPanelRef.value?.getMap ? mapPanelRef.value.getMap() : amapInstance.value
      if (mapObj && ro.polyline) {
        mapObj.setFitView([ro.polyline, ...(ro.markers?.map((m) => m.marker) || [])])
      }
    } else if (fitBounds && highlightedRouteIdx.value === null) {
      mapPanelRef.value?.fitView()
    }
  }

  const renderClusteringMap = (A) => {
    stores.value.forEach((p, i) => {
      if (!p.lng || !p.lat) return
      const cid = p.cluster_id
      const color = (cid !== undefined && cid !== null)
        ? CLUSTER_COLORS[cid % CLUSTER_COLORS.length]
        : '#94a3b8'

      const { content, offset } = dotHtml({
        text: String(i + 1),
        color,
        size: 22,
      })

      const marker = new A.Marker({
        position: [Number(p.lng), Number(p.lat)],
        content,
        offset: new A.Pixel(offset[0], offset[1]),
        title: p.name || `门店${i + 1}`,
        zIndex: 100,
      })

      let clusterSelectHtml = ''
      if (clusteringResult.value?.clusters?.length) {
        clusterSelectHtml = `
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
            <span style="font-size: 11px; font-weight: 600; color: #475569;">所属店群:</span>
            <select onchange="window.moveCanvasStore(${i}, this.value)" style="font-size: 11px; padding: 2px 4px; border-radius: 4px; border: 1px solid #0284c7; background: #f0f9ff; font-weight: 600; color: #0369a1;">
              ${clusteringResult.value.clusters.map(c => `<option value="${c.cluster_id}" ${c.cluster_id === cid ? 'selected' : ''}>店群 ${c.cluster_id + 1} (${c.size}家)</option>`).join('')}
              <option value="new">+ 新建并加入新店群</option>
            </select>
          </div>
        `
      }

      const safeName = escapeHtml(p.name || '未命名门店')
      const infoContent = `
        <div style="padding: 12px; font-size: 12px; line-height: 1.5; color: #1e293b; min-width: 230px; max-width: 290px; background: #fff; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
          <div style="font-weight: 700; font-size: 14px; margin-bottom: 8px; color: #0f172a; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; display: flex; justify-content: space-between;">
            <span>${safeName}</span>
            <span style="font-size: 11px; color: #94a3b8;">#${i + 1}</span>
          </div>
          ${clusterSelectHtml}
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 5px;">
            <span style="font-size: 11px; color: #64748b;">日均箱数(avg_loads):</span>
            <input type="number" value="${p.avg_loads || p.weight || 10}" onchange="window.updateCanvasStoreAttr(${i}, 'avg_loads', this.value)" style="font-size: 11px; width: 70px; padding: 2px 4px; border: 1px solid #cbd5e1; border-radius: 4px; text-align: right;" />
          </div>
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 5px;">
            <span style="font-size: 11px; color: #64748b;">周配送频次(frequency):</span>
            <select onchange="window.updateCanvasStoreAttr(${i}, 'frequency', this.value)" style="font-size: 11px; padding: 2px 4px; border: 1px solid #cbd5e1; border-radius: 4px;">
              ${[1, 2, 3, 4, 5, 6, 7].map(f => `<option value="${f}" ${p.frequency == f ? 'selected' : ''}>每周 ${f} 次</option>`).join('')}
            </select>
          </div>
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 5px;">
            <span style="font-size: 11px; color: #64748b;">属性(is_homepot):</span>
            <select onchange="window.updateCanvasStoreAttr(${i}, 'is_homepot', this.value)" style="font-size: 11px; padding: 2px 4px; border: 1px solid #cbd5e1; border-radius: 4px;">
              <option value="1" ${p.is_homepot == 1 ? 'selected' : ''}>本埠门店</option>
              <option value="0" ${p.is_homepot == 0 ? 'selected' : ''}>外埠门店</option>
            </select>
          </div>
        </div>
      `

      const infoWindow = new A.InfoWindow({
        content: infoContent,
        offset: new A.Pixel(0, -18),
        closeWhenClickMap: true,
      })

      marker.on('click', () => {
        const mapObj = mapPanelRef.value?.getMap()
        if (mapObj) infoWindow.open(mapObj, marker.getPosition())
      })

      mapPanelRef.value.addOverlay(marker)
    })

    if (clusteringResult.value?.clusters?.length) {
      clusteringResult.value.clusters.forEach((c) => {
        if (!c.center?.lng || !c.center?.lat) return
        const color = CLUSTER_COLORS[c.cluster_id % CLUSTER_COLORS.length]
        const { content, offset } = dotHtml({
          text: `C${c.cluster_id + 1}`,
          color,
          size: 32,
        })

        const centerMarker = new A.Marker({
          position: [Number(c.center.lng), Number(c.center.lat)],
          content,
          offset: new A.Pixel(offset[0], offset[1]),
          zIndex: 200,
          title: `店群 ${c.cluster_id + 1} 中心`,
        })

        const centerContent = `
          <div style="padding: 10px 14px; font-size: 13px; line-height: 1.6; color: #1e293b; min-width: 170px; background: white; border-radius: 8px;">
            <strong style="font-size: 14px; color: ${color};">店群 ${c.cluster_id + 1} 概览</strong><br>
            <hr style="margin: 6px 0; border: none; border-top: 1px solid #e2e8f0;">
            <strong>门店总数:</strong> ${c.size} 家<br>
            <strong>日均总装载:</strong> ${getClusterLoad(c.cluster_id)} 箱<br>
            <strong>距仓库:</strong> ${c.cdist_warehouse ? c.cdist_warehouse.toFixed(2) : '-'} km
          </div>
        `

        const centerInfoWindow = new A.InfoWindow({
          content: centerContent,
          offset: new A.Pixel(0, -22),
          closeWhenClickMap: true,
        })

        centerMarker.on('click', () => {
          const mapObj = mapPanelRef.value?.getMap()
          if (mapObj) centerInfoWindow.open(mapObj, centerMarker.getPosition())
        })

        mapPanelRef.value.addOverlay(centerMarker)
      })
    }
  }

  const renderSchedulingMap = (A) => {
    if (!hasScheduleComputed.value) {
      renderClusteringMap(A)
      return
    }

    stores.value.forEach((p, i) => {
      if (!p.lng || !p.lat) return
      const dayStr = p.delivery_days_str || p.schedule_day || ''
      
      let opacity = 1.0
      if (selectedScheduleDay.value !== '全部') {
        const match = dayStr && dayStr.includes(selectedScheduleDay.value)
        if (!match) {
          opacity = 0.15
        }
      }

      const firstDay = dayStr.split(',')[0].trim()
      const color = DAY_COLORS[firstDay] || '#94a3b8'
      const isSelected = selectedPointIndices.value && selectedPointIndices.value.includes(i)

      const { content, offset } = dotHtml({
        text: String(i + 1),
        color,
        size: isSelected ? 26 : 22,
      })

      const storeFreq = Math.round(Number(p.frequency || (dayStr ? dayStr.split(',').filter(Boolean).length : 1)))
      p.frequency = storeFreq

      let badgeHtml = ''
      if (storeFreq > 1) {
        badgeHtml = `<span style="
          position: absolute;
          top: -6px;
          right: -6px;
          background: #ef4444;
          color: white;
          font-size: 9px;
          font-weight: 800;
          border-radius: 50%;
          width: 14px;
          height: 14px;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 0 4px rgba(0,0,0,0.3);
          border: 1px solid white;
          z-index: 10;
          pointer-events: none;
        ">${storeFreq}</span>`
      }

      let finalContent = `<div style="position: relative;">${content}${badgeHtml}</div>`
      if (opacity < 1.0) {
        finalContent = `<div style="opacity: ${opacity}; transition: opacity 0.25s; position: relative;">${content}${badgeHtml}</div>`
      } else if (isSelected) {
        finalContent = `<div style="box-shadow: 0 0 12px #0d9488; border-radius: 50%; outline: 3px solid #0d9488; outline-offset: 2px; position: relative;">${content}${badgeHtml}</div>`
      }

      const marker = new A.Marker({
        position: [Number(p.lng), Number(p.lat)],
        content: finalContent,
        offset: new A.Pixel(offset[0], offset[1]),
        title: p.name || `门店${i + 1}`,
        zIndex: isSelected ? 120 : 100,
      })

      const validOpts = getValidScheduleOptionsForFreq(storeFreq)
      let optionsHtml = validOpts.map(opt => `<option value="${opt.value}" ${dayStr === opt.value ? 'selected' : ''}>${opt.label}</option>`).join('')
      if (dayStr && !validOpts.some(opt => opt.value === dayStr)) {
        optionsHtml = `<option value="${dayStr}" selected disabled>⚠️ 当前非标准作业日: ${dayStr}</option>` + optionsHtml
      }

      const isHp = Number(p.is_homepot !== undefined && p.is_homepot !== null ? p.is_homepot : 0)
      const safeName = escapeHtml(p.name || '未命名门店')
      const infoContent = `
        <div style="padding: 12px; font-size: 12px; line-height: 1.5; color: #1e293b; min-width: 260px; background: #fff; border-radius: 8px;">
          <div style="font-weight: 700; font-size: 14px; margin-bottom: 8px; color: #0f172a; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; display: flex; justify-content: space-between;">
            <span>${safeName}</span>
            <span style="font-size: 11px; color: #94a3b8;">#${i + 1}</span>
          </div>
          <div style="margin-bottom: 5px; color: #64748b;">
            所属店群: <strong style="color: #0284c7;">店群 ${(p.cluster_id !== undefined && p.cluster_id !== null ? p.cluster_id : 0) + 1}</strong>
          </div>
          <div style="margin-bottom: 5px; color: #64748b;">
            日均货量: <strong>${p.avg_loads || 10.0}</strong> 箱 | 配送频次: <strong style="color: #0284c7;">每周 ${storeFreq} 次</strong>
          </div>
          <div style="margin-bottom: 5px; color: #64748b; display: flex; align-items: center; justify-content: space-between;">
            <span>门店属性:</span>
            <select onchange="window.updateCanvasStoreAttr(${i}, 'is_homepot', this.value)" style="font-size: 11px; padding: 2px 6px; border: 1px solid #cbd5e1; border-radius: 4px; background: #f8fafc; font-weight: 600;">
              <option value="1" ${isHp === 1 ? 'selected' : ''}>🏠 本埠门店</option>
              <option value="0" ${isHp === 0 ? 'selected' : ''}>🚗 外埠门店</option>
            </select>
          </div>
          <div style="margin-top: 8px;">
            <div style="font-size: 11px; font-weight: 600; color: #475569; margin-bottom: 4px;">
              调整配送作业日 (限定 ${storeFreq}次/周 规则):
            </div>
            <select onchange="window.updateCanvasStoreSchedule(${i}, this.value)" style="width: 100%; font-size: 11px; padding: 5px; border: 1px solid #0284c7; border-radius: 4px; background: #f0f9ff; color: #0369a1; font-weight: 600;">
              ${optionsHtml}
            </select>
          </div>
        </div>
      `

      const infoWindow = new A.InfoWindow({
        content: infoContent,
        offset: new A.Pixel(0, -18),
        closeWhenClickMap: true,
      })

      marker.on('click', () => {
        const mapObj = mapPanelRef.value?.getMap()
        if (mapObj) infoWindow.open(mapObj, marker.getPosition())
      })

      mapPanelRef.value.addOverlay(marker)
    })
  }

  const renderRoutingMap = (A) => {
    const displayRoutes = currentDisplayRoutes.value
    const targetStores = activeDayPoints.value
    const routedKeys = new Set(displayRoutes.flatMap((r) => r.points || []).map((p) => p.shop_code || p.name))
    const unassigned = targetStores.filter((p) => !routedKeys.has(p.shop_code || p.name) && !isStoreExpressOnDay(p, selectedRoutingDay.value, stores.value))
    const currentExpress = stores.value.filter((s) => isStoreExpressOnDay(s, selectedRoutingDay.value, stores.value))

    renderRouteMapLayers({
      amap: A,
      mapPanel: mapPanelRef.value,
      depot: { name: canvas.depot_name || '中心仓', lng: Number(canvas.depot_lng), lat: Number(canvas.depot_lat) },
      routes: displayRoutes,
      allStores: stores.value,
      expressStores: currentExpress,
      unassignedStores: unassigned,
      highlightedRouteIdx: highlightedRouteIdx.value,
      selectedPointIndices: selectedPointIndices.value || [],
      currentDay: selectedRoutingDay.value,
      openInfoWindowAt,
    })
  }

  const renderMap = async (shouldFit = false) => {
    if (!mapPanelRef.value) return
    if (!amapInstance.value) {
      if (mapPanelRef.value.whenReady) {
        amapInstance.value = await mapPanelRef.value.whenReady()
      } else if (mapPanelRef.value.getAmap) {
        amapInstance.value = await mapPanelRef.value.getAmap()
      } else {
        amapInstance.value = await loadAMap()
      }
    }
    const A = amapInstance.value
    if (!A) return

    mapPanelRef.value.clearAll()
    if (sharedInfoWindow) sharedInfoWindow.close()

    const depotLng = Number(canvas.depot_lng)
    const depotLat = Number(canvas.depot_lat)
    if (!isNaN(depotLng) && !isNaN(depotLat) && depotLng > 0 && depotLat > 0) {
      const { content, offset } = dotHtml({ text: '仓', color: '#475569', size: 28 })
      const depotMarker = new A.Marker({
        position: [depotLng, depotLat],
        content,
        offset: new A.Pixel(offset[0], offset[1]),
        zIndex: 200,
        title: canvas.depot_name || '中心仓',
      })
      mapPanelRef.value.addOverlay(depotMarker)
    }

    if (activeStage.value === 'clustering') {
      renderClusteringMap(A)
    } else if (activeStage.value === 'scheduling') {
      renderSchedulingMap(A)
    } else if (activeStage.value === 'routing') {
      renderRoutingMap(A)
    }

    if (shouldFit === true && stores.value.length > 0) {
      setTimeout(() => {
        mapPanelRef.value?.fitView()
      }, 150)
    }
  }

  const initMouseTool = () => {
    const A = window.AMap
    const mapObj = mapPanelRef.value?.getMap ? mapPanelRef.value.getMap() : amapInstance.value
    if (!A || !mapObj) return

    A.plugin(['AMap.MouseTool'], () => {
      if (!mouseToolInstance) {
        mouseToolInstance = new A.MouseTool(mapObj)
        mouseToolInstance.on('draw', (e) => {
          const bounds = e.obj.getBounds()
          const selected = []
          stores.value.forEach((p, idx) => {
            if (p.lng === '' || p.lat === '') return
            const pos = new A.LngLat(Number(p.lng), Number(p.lat))
            if (bounds.contains(pos)) {
              selected.push(idx)
            }
          })
          selectedPointIndices.value = selected
          mouseToolInstance.close(true)
          isSelecting.value = false
          renderMap()
        })
      }
    })
  }

  const toggleBoxSelect = () => {
    const A = window.AMap
    const mapObj = mapPanelRef.value?.getMap ? mapPanelRef.value.getMap() : amapInstance.value
    if (!mapObj || !A) return

    if (!mouseToolInstance) {
      initMouseTool()
    }

    if (isSelecting.value) {
      mouseToolInstance?.close(true)
      isSelecting.value = false
    } else {
      selectedPointIndices.value = []
      isSelecting.value = true
      mouseToolInstance?.rectangle({
        fillColor: '#0d9488',
        strokeColor: '#0d9488',
        fillOpacity: 0.18,
        strokeOpacity: 0.85,
        strokeWeight: 2,
      })
    }
    renderMap()
  }

  const destroyMouseTool = () => {
    if (mouseToolInstance) {
      mouseToolInstance.close(true)
      mouseToolInstance = null
    }
  }

  return {
    renderMap,
    toggleBoxSelect,
    initMouseTool,
    destroyMouseTool,
    toggleHighlightRoute,
  }
}
