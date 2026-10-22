import { ref, nextTick } from 'vue'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { canvasApi } from '../../../api/client.js'
import { DAYS_LIST, getDistanceBetweenCoords } from '../../../utils/constants.js'
import { useRouteOptimizer } from '../../../composables/useRouteOptimizer.js'
import { useRouteExport } from '../../../composables/useRouteExport.js'

/**
 * 解包并规范化排班数据，避免 schedule_results 属性多层嵌套导致的结构损坏
 */
function unwrapScheduleData(data) {
  if (!data || typeof data !== 'object') return null
  let current = data
  // 递归解开潜在的嵌套包装：{ schedule_results: { schedule_results: ... } }
  while (
    current &&
    typeof current === 'object' &&
    'schedule_results' in current &&
    !('points' in current) &&
    !('daily_stats' in current)
  ) {
    current = current.schedule_results
  }
  return current && Object.keys(current).length > 0 ? current : null
}

export function useCanvasVersioning(state, options = {}) {
  const { onSnapshotLoaded } = options
  const { hydrateRoutePoints } = useRouteOptimizer()
  const { exportRoutesToExcel } = useRouteExport()

  const {
    canvas,
    currentVersion,
    versionList,
    activeStage,
    stores,
    clusteringResult,
    scheduleResult,
    dailyResults,
    trucks,
    isScheduleOutdated,
    isRoutingOutdated,
    clusteringAlgorithm,
    clusteringK,
    minZoneSize,
    maxZoneSize,
    routeOptions,
    totalLoads,
    routes,
    totalDistanceKm,
    allWeekRoutes,
    selectedScheduleDay,
    selectedRoutingDay,
  } = state

  const savingVersion = ref(false)
  const saveVersionModalVisible = ref(false)
  const newVersionName = ref('')
  const newVersionChangeSummary = ref('')
  const versionDrawerVisible = ref(false)

  const renameModalVisible = ref(false)
  const canvasRenameText = ref('')

  const getStageLabel = (stage) => {
    const map = {
      INIT: '初始建库',
      CLUSTERED: '店群已规划',
      SCHEDULED: '排班已规划',
      ROUTED: '路线已规划',
    }
    return map[stage] || stage || '进行中'
  }

  const loadSnapshotIntoState = (snapshot) => {
    if (!snapshot) return
    isScheduleOutdated.value = false
    isRoutingOutdated.value = false

    stores.value = (snapshot.stores || []).map((s) => ({
      ...s,
      lng: Number(s.lng !== undefined && s.lng !== null ? s.lng : s.longitude),
      lat: Number(s.lat !== undefined && s.lat !== null ? s.lat : s.latitude),
      avg_loads: Number(s.avg_loads || s.weight || 10),
      frequency: Number(s.frequency || 1),
      is_homepot: Number(s.is_homepot || 0),
      delivery_days_str: s.delivery_days_str || s.schedule_day || '',
    })).filter((s) => !isNaN(s.lng) && !isNaN(s.lat) && s.lng > 0 && s.lat > 0)

    if (snapshot.clustering_data && snapshot.clustering_data.clusters?.length) {
      clusteringResult.value = snapshot.clustering_data
      clusteringAlgorithm.value = snapshot.clustering_data.algorithm || 'kmeans'
      clusteringK.value = snapshot.clustering_data.k || snapshot.clustering_data.clusters.length
      minZoneSize.value = snapshot.clustering_data.minZoneSize || 5
      maxZoneSize.value = snapshot.clustering_data.maxZoneSize || 30
    } else {
      const storesWithCluster = stores.value.filter(
        (s) => s.cluster_id !== undefined && s.cluster_id !== null && s.cluster_id !== ''
      )
      if (storesWithCluster.length > 0 && storesWithCluster.length >= stores.value.length * 0.4) {
        const clusterMap = new Map()
        stores.value.forEach((s, idx) => {
          const cId = s.cluster_id !== undefined && s.cluster_id !== null ? Number(s.cluster_id) : 0
          if (!clusterMap.has(cId)) clusterMap.set(cId, [])
          clusterMap.get(cId).push(idx)
        })
        const clusters = []
        const sortedKeys = Array.from(clusterMap.keys()).sort((a, b) => Number(a) - Number(b))
        const depot = {
          lng: Number(canvas.depot_lng || 108.36654),
          lat: Number(canvas.depot_lat || 22.817),
        }
        sortedKeys.forEach((cId) => {
          const idxs = clusterMap.get(cId)
          const sumLng = idxs.reduce((sum, idx) => sum + stores.value[idx].lng, 0)
          const sumLat = idxs.reduce((sum, idx) => sum + stores.value[idx].lat, 0)
          const center = {
            lng: Number((sumLng / idxs.length).toFixed(6)),
            lat: Number((sumLat / idxs.length).toFixed(6)),
          }
          const cdist = getDistanceBetweenCoords(center, depot)
          idxs.forEach((idx) => {
            stores.value[idx].cdist_warehouse = Number(cdist.toFixed(1))
            stores.value[idx].center_lng = center.lng
            stores.value[idx].center_lat = center.lat
          })
          clusters.push({
            cluster_id: cId,
            name: `店群 ${cId + 1}`,
            center,
            size: idxs.length,
            point_indices: idxs,
            cdist_warehouse: Number(cdist.toFixed(1)),
          })
        })
        clusteringResult.value = {
          algorithm: 'Excel导入店群',
          clusters,
          total_stores: stores.value.length,
          k: clusters.length,
        }
        clusteringK.value = clusters.length
      } else {
        clusteringResult.value = null
      }
    }

    scheduleResult.value = unwrapScheduleData(snapshot.schedule_data)
    if (!scheduleResult.value) {
      stores.value.forEach((s) => {
        s.delivery_days_str = ''
        s.schedule_day = ''
      })
    }

    if (snapshot.routing_data) {
      if (snapshot.routing_data.daily_results) {
        const rawDaily = snapshot.routing_data.daily_results
        const hydratedDaily = {}
        DAYS_LIST.forEach((d) => {
          if (rawDaily[d]?.routes) {
            const dPts = stores.value.filter((p) => (p.schedule_day || p.delivery_days_str || '').includes(d))
            hydratedDaily[d] = {
              ...rawDaily[d],
              day: d,
              routes: hydrateRoutePoints(rawDaily[d].routes, dPts.length ? dPts : stores.value, { defaultReturnToDepot: routeOptions.value?.return_to_depot }),
            }
          }
        })
        dailyResults.value = hydratedDaily
        if (selectedRoutingDay) {
          if (hydratedDaily['周一']?.routes?.length) {
            selectedRoutingDay.value = '周一'
          } else {
            const firstDay = Object.keys(hydratedDaily).find((d) => hydratedDaily[d]?.routes?.length)
            if (firstDay) {
              selectedRoutingDay.value = firstDay
            }
          }
        }
      } else if (snapshot.routing_data.routes?.length) {
        dailyResults.value = {
          '全部': {
            routes: hydrateRoutePoints(snapshot.routing_data.routes, stores.value, { defaultReturnToDepot: routeOptions.value?.return_to_depot }),
          },
        }
        if (selectedRoutingDay) selectedRoutingDay.value = '全部'
      } else {
        dailyResults.value = {}
      }
      if (snapshot.routing_data.trucks?.length) {
        trucks.value = snapshot.routing_data.trucks
      }
    } else {
      dailyResults.value = {}
    }

    if (!dailyResults.value || !Object.keys(dailyResults.value).length) {
      stores.value.forEach((s) => {
        s.is_express = 0
        s.express_days = []
      })
    }

    if (onSnapshotLoaded) {
      nextTick(() => onSnapshotLoaded())
    }
  }

  const fetchCanvasData = async () => {
    try {
      const data = await canvasApi.get(canvas.canvas_id)
      canvas.id = data.id
      canvas.name = data.name
      canvas.dc_code = data.dc_code
      canvas.depot_name = data.depot_name
      canvas.depot_lng = data.depot_lng
      canvas.depot_lat = data.depot_lat
      canvas.depot_address = data.depot_address
      canvas.description = data.description
      canvas.stage = data.stage

      currentVersion.value = data.current_version
      loadSnapshotIntoState(data.current_version?.snapshot_data)

      versionList.value = await canvasApi.getVersions(canvas.canvas_id)
    } catch (err) {
      ElMessage.error(`获取画布失败: ${err.message}`)
    }
  }

  const openSaveVersionModal = () => {
    const nextNum = (currentVersion.value?.version_number || 1) + 1
    let defaultStageName = '规划演进'
    if (activeStage.value === 'clustering') defaultStageName = '完成店群分组'
    if (activeStage.value === 'scheduling') defaultStageName = '完成全周排班'
    if (activeStage.value === 'routing') defaultStageName = '生成路线与路网测算'

    newVersionName.value = `V${nextNum} - ${defaultStageName}`
    newVersionChangeSummary.value = `在当前画布中完成了${defaultStageName}，规划了 ${stores.value.length} 家门店。`
    saveVersionModalVisible.value = true
  }

  const submitSaveVersion = async () => {
    if (!newVersionName.value.trim()) {
      ElMessage.warning('请输入版本名称')
      return
    }

    savingVersion.value = true
    try {
      // 轻量化清理 daily_results: 剔除自引用的 raw_route、巨大的 points/stops 重复大对象及临时测算折线缓存
      const cleanDailyResults = {}
      if (dailyResults.value) {
        Object.entries(dailyResults.value).forEach(([day, dayData]) => {
          if (dayData && Array.isArray(dayData.routes)) {
            cleanDailyResults[day] = {
              ...dayData,
              routes: dayData.routes.map((r) => {
                const { raw_route, points, stops, detailed_polyline, amap_path, pathCoords, ...cleanR } = r
                return cleanR
              }),
            }
          }
        })
      }

      const snapshotData = {
        stores: stores.value,
        depot: {
          dc_code: canvas.dc_code,
          name: canvas.depot_name,
          lng: canvas.depot_lng,
          lat: canvas.depot_lat,
          address: canvas.depot_address,
        },
        clustering_data: {
          clusters: clusteringResult.value?.clusters || [],
          algorithm: clusteringAlgorithm.value,
          k: clusteringK.value,
          minZoneSize: minZoneSize.value,
          maxZoneSize: maxZoneSize.value,
        },
        schedule_data: unwrapScheduleData(scheduleResult.value),
        routing_data: {
          daily_results: cleanDailyResults,
          trucks: trucks.value,
        },
        algorithm_configs: {
          clustering_algorithm: clusteringAlgorithm.value,
          k: clusteringK.value,
        },
      }

      const payload = {
        version_name: newVersionName.value.trim(),
        change_summary: newVersionChangeSummary.value.trim() || undefined,
        stage: canvas.stage,
        parent_version_id: currentVersion.value?.id,
        snapshot_data: snapshotData,
      }

      const savedVersion = await canvasApi.createVersion(canvas.canvas_id, payload)
      currentVersion.value = savedVersion
      versionList.value = await canvasApi.getVersions(canvas.canvas_id)

      ElMessage.success(`🎉 成功保存版本 V${savedVersion.version_number} 并持久化到数据库！`)
      saveVersionModalVisible.value = false
    } catch (err) {
      ElMessage.error(`保存版本失败: ${err.message}`)
    } finally {
      savingVersion.value = false
    }
  }

  const handleSelectVersion = (versionId) => {
    const target = versionList.value.find((v) => v.id === versionId)
    if (target) {
      rollbackToVersion(target)
    }
  }

  const rollbackToVersion = async (targetVersion) => {
    try {
      await ElMessageBox.confirm(
        `确定要将画布工作区切换至版本「V${targetVersion.version_number} - ${targetVersion.version_name}」吗？`,
        '切换版本快照',
        { confirmButtonText: '立即载入', cancelButtonText: '取消', type: 'info' }
      )

      const prevStores = stores.value.length
      const prevLoads = totalLoads.value
      const prevClusters = clusteringResult.value?.clusters?.length || 0
      const prevRoutes = routes.value.length
      const prevDist = totalDistanceKm.value

      const res = await canvasApi.rollbackVersion(canvas.canvas_id, targetVersion.id)
      currentVersion.value = res.current_version
      canvas.stage = res.stage
      loadSnapshotIntoState(res.current_version?.snapshot_data)

      const newStores = stores.value.length
      const newLoads = totalLoads.value
      const newClusters = clusteringResult.value?.clusters?.length || 0
      const newRoutes = routes.value.length
      const newDist = totalDistanceKm.value

      const storesDiff = newStores - prevStores
      const loadsDiff = newLoads - prevLoads
      const routesDiff = newRoutes - prevRoutes
      const distDiff = (newDist - prevDist).toFixed(1)

      ElNotification({
        title: `📋 已载入版本 V${targetVersion.version_number} - ${targetVersion.version_name}`,
        message: `
          <div style="font-size: 12px; line-height: 1.6; color: #334155;">
            <div>• 规划阶段: <strong>${getStageLabel(canvas.stage)}</strong></div>
            <div>• 门店与运量: <strong>${newStores} 家</strong> (${storesDiff >= 0 ? '+' + storesDiff : storesDiff}) · <strong>${newLoads} 箱</strong> (${loadsDiff >= 0 ? '+' + loadsDiff : loadsDiff})</div>
            <div>• 店群数量: <strong>${newClusters} 个店群</strong></div>
            <div>• 规划路线: <strong>${newRoutes} 条</strong> (${routesDiff >= 0 ? '+' + routesDiff : routesDiff}) · <strong>${newDist} km</strong> (${distDiff >= 0 ? '+' + distDiff : distDiff} km)</div>
            ${targetVersion.change_summary ? `<div style="margin-top: 4px; padding-top: 4px; border-top: 1px dashed #cbd5e1; color: #64748b; font-style: italic;">"${targetVersion.change_summary}"</div>` : ''}
          </div>
        `,
        dangerouslyUseHTMLString: true,
        type: 'success',
        duration: 6000,
      })

      versionDrawerVisible.value = false
    } catch (e) {
      if (e !== 'cancel') ElMessage.error(`版本切换失败: ${e.message}`)
    }
  }

  const openRenameModal = () => {
    canvasRenameText.value = canvas.name
    renameModalVisible.value = true
  }

  const submitRename = async () => {
    if (!canvasRenameText.value.trim()) return
    try {
      await canvasApi.update(canvas.canvas_id, { name: canvasRenameText.value.trim() })
      canvas.name = canvasRenameText.value.trim()
      ElMessage.success('画布重命名成功')
      renameModalVisible.value = false
    } catch (err) {
      ElMessage.error(`重命名失败: ${err.message}`)
    }
  }

  const exportCanvasExcel = () => {
    exportRoutesToExcel({
      planName: canvas.name || '画布规划方案',
      versionNumber: currentVersion.value?.version_number || 1,
      stores: stores.value,
      routes: routes.value,
      allWeekRoutes: allWeekRoutes.value,
    })
  }

  return {
    savingVersion,
    saveVersionModalVisible,
    newVersionName,
    newVersionChangeSummary,
    versionDrawerVisible,
    renameModalVisible,
    canvasRenameText,
    getStageLabel,
    loadSnapshotIntoState,
    fetchCanvasData,
    openSaveVersionModal,
    submitSaveVersion,
    handleSelectVersion,
    rollbackToVersion,
    openRenameModal,
    submitRename,
    exportCanvasExcel,
  }
}
