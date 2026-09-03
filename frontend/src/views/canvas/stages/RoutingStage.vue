<template>
  <div class="stage-content-scroll">
    <div class="panel-section">
      <h3 class="section-title">🚚 多车型路线规划与调度</h3>
      <p class="section-desc">
        基于排班结果进行多车型 CVRP 运筹求解，支持高德真实货车路网高精测算与交互调线。
      </p>
    </div>

    <div class="panel-card">
      <div class="form-group">
        <label class="form-label">计划配送作业日</label>
        <el-select v-model="selectedRoutingDay" style="width: 100%;" @change="$emit('render-map')">
          <el-option label="全部时间 (全周总览)" value="全部" />
          <el-option label="周一配送路线" value="周一" />
          <el-option label="周二配送路线" value="周二" />
          <el-option label="周三配送路线" value="周三" />
          <el-option label="周四配送路线" value="周四" />
          <el-option label="周五配送路线" value="周五" />
          <el-option label="周六配送路线" value="周六" />
          <el-option label="周日配送路线" value="周日" />
        </el-select>
      </div>
    </div>

    <!-- Fleet Capacity Pool -->
    <div class="panel-card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
        <label class="form-label" style="margin: 0;">可用车型与运力池 ({{ trucks.length }} 种)</label>
        <el-button link type="primary" size="small" @click="$emit('open-fleet-config')">+ 配置车型</el-button>
      </div>
      <div class="fleet-tag-list">
        <div v-for="(t, idx) in trucks" :key="idx" class="fleet-tag">
          <span>{{ t.name }}</span>
          <span class="fleet-tag-cap">({{ t.capacity }}箱 × {{ t.count }}辆)</span>
          <span class="remove-tag" @click="trucks.splice(idx, 1)">×</span>
        </div>
        <div v-if="!trucks.length" style="font-size: 11px; color: #94a3b8;">
          暂无配置车型，将使用系统默认车型池
        </div>
      </div>
    </div>

    <!-- Stage 3 Express Management Card -->
    <div v-if="stores.length" class="panel-card" style="border-left: 4px solid #8b5cf6;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
        <span style="font-weight: 700; font-size: 13px; color: #581c87; display: flex; align-items: center; gap: 4px;">
          <span>📦</span> 配送方式与快递直发管理
        </span>
        <span style="font-size: 11px; font-weight: 700; color: #7c3aed; background: #faf5ff; padding: 1px 6px; border-radius: 4px; border: 1px solid #d8b4fe;">
          快递: {{ expressStores.length }} 家
        </span>
      </div>

      <div style="font-size: 11px; color: #64748b; line-height: 1.5; margin-bottom: 8px;">
        当前作业日: <strong>{{ selectedRoutingDay }}</strong> (常规货车 <strong>{{ (selectedRoutingDay === '全部' ? stores.length : stores.filter(s => (s.schedule_day || s.delivery_days_str || '').includes(selectedRoutingDay)).length) - expressStores.length }}</strong> 家 · 快递 <strong>{{ expressStores.length }}</strong> 家)
      </div>

      <button class="action-btn" style="width: 100%; font-size: 11px; padding: 5px 8px; background: #faf5ff; border: 1px solid #c4b5fd; color: #7c3aed; font-weight: 600; cursor: pointer;" @click="$emit('open-express-modal')">
        📋 门店配送方式列表与一键切换
      </button>
    </div>

    <div class="panel-card">
      <div style="display: flex; gap: 8px; margin-bottom: 8px;">
        <el-button
          type="primary"
          style="flex: 1;"
          :loading="routingLoading"
          @click="handleRunRouting"
        >
          {{ routingLoading ? '路径规划计算中…' : '⚡ 执行智能路线规划' }}
        </el-button>
        <el-button
          plain
          title="求解器参数设置"
          @click="$emit('open-route-config')"
          style="padding: 0 12px; font-size: 14px;"
        >
          ⚙️
        </el-button>
      </div>
      <el-button
        type="warning"
        plain
        style="width: 100%;"
        :loading="batchMeasuring"
        :disabled="!routes.length"
        @click="batchMeasureAMapRoutes"
      >
        🗺️ 批量高德真实货车路网测算
      </el-button>

      <!-- AMap Batch Measure Progress Card -->
      <div
        v-if="batchMeasuring || measureSummary"
        style="margin-top: 10px; padding: 10px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px;"
      >
        <div v-if="batchMeasuring">
          <div style="display: flex; justify-content: space-between; font-size: 11px; color: #475569; margin-bottom: 4px;">
            <span style="font-weight: 600;">路网高精测算中...</span>
            <span style="color: #0284c7; font-weight: 700;">{{ measureProgress.current }} / {{ measureProgress.total }} ({{ measureProgress.percent }}%)</span>
          </div>
          <el-progress :percentage="measureProgress.percent" :stroke-width="6" :show-text="false" status="success" />
          <div style="font-size: 10px; color: #94a3b8; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            正在测算: {{ measureProgress.currentRouteName }}
          </div>
        </div>

        <div v-else-if="measureSummary" style="font-size: 11px; line-height: 1.6; color: #1e293b;">
          <div style="font-weight: 700; color: #16a34a; display: flex; justify-content: space-between;">
            <span>✅ 高德路网测算汇总</span>
            <button style="border: none; background: transparent; color: #94a3b8; cursor: pointer;" @click="measureSummary = null">×</button>
          </div>
          <div style="grid-template-columns: 1fr 1fr; gap: 4px; margin-top: 4px; font-size: 10px; color: #64748b; display: grid;">
            <div>实测里程: <strong style="color: #0f172a;">{{ measureSummary.totalDist }} km</strong></div>
            <div>总行车耗时: <strong style="color: #0f172a;">{{ measureSummary.totalDuration }}</strong></div>
            <div>预估过路费: <strong style="color: #d97706;">¥{{ measureSummary.totalTolls }}</strong></div>
            <div>测算路线: <strong style="color: #0f172a;">{{ measureSummary.count }} 条</strong></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Routes List Overview -->
    <div v-if="routes.length || expressStores.length" class="panel-card">
      <RoutePlanList
        :routes="routes"
        :all-routes="routes"
        :express-stores="expressStores"
        :highlighted-route-idx="highlightedRouteIdx"
        :loading-amap-route-key="loadingAmapRouteKey"
        :batch-measuring="batchMeasuring"
        :measure-progress="measureProgress"
        :get-route-color="getRouteColor"
        @toggle-highlight="(rIdx) => $emit('toggle-highlight', rIdx)"
        @calculate-amap="({ route, routeIdx }) => calculateSingleAmapRoute(route, routeIdx)"
        @batch-calculate-amap="batchMeasureAMapRoutes"
        @move-store-order="({ routeIdx, storeIdx, direction }) => handleMoveStoreOrder(routeIdx, storeIdx, direction)"
        @reorder-store="({ routeIdx, fromIdx, toIdx }) => handleReorderStore(routeIdx, fromIdx, toIdx)"
        @transfer-store="({ fromRouteIdx, storeIdx, targetRouteIdx }) => handleMoveStoreBetweenRoutes(fromRouteIdx, storeIdx, targetRouteIdx)"
        @restore-express-store="(s) => handleRestoreExpressStore(s, () => $emit('render-map'))"
        @select-store="(s) => $emit('select-store', s)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useCanvasState } from '../composables/useCanvasState.js'
import { routingApi } from '../../../api/client.js'
import { useRouteMeasure } from '../../../composables/useRouteMeasure.js'
import { useRouteOptimizer } from '../../../composables/useRouteOptimizer.js'
import RoutePlanList from '../../../components/planning/RoutePlanList.vue'
import { ROUTE_COLORS } from '../../../utils/mapMarkers.js'
import { DAYS_LIST } from '../../../utils/constants.js'
import { ElMessage } from 'element-plus'

const emit = defineEmits([
  'render-map',
  'open-fleet-config',
  'open-route-config',
  'open-express-modal',
  'toggle-highlight',
  'select-store',
])

const {
  canvas,
  stores,
  dailyResults,
  trucks,
  selectedRoutingDay,
  isRoutingOutdated,
  routeOptions,
  currentDisplayRoutes,
  routes,
  expressStores,
  highlightedRouteIdx,
  recalculateRouteMetrics,
  handleRestoreExpressStore,
  moveStoreBetweenRoutes,
} = useCanvasState()

const {
  isStoreExpressOnDay,
  setStoreExpressOnDay,
  optimizeRouteWith2Opt,
  clearRouteMeasureCache,
} = useRouteOptimizer()

const routingLoading = ref(false)

const getRouteColor = (idx) => ROUTE_COLORS[(idx || 0) % ROUTE_COLORS.length]

const {
  loadingAmapRouteKey,
  batchMeasuring,
  measureProgress,
  measureSummary,
  measureSingleRoute,
  batchMeasureRoutes,
} = useRouteMeasure()

const handleRunRouting = async () => {
  if (stores.value.length < 1) {
    ElMessage.warning('没有可规划的门店')
    return
  }
  routingLoading.value = true
  try {
    if (selectedRoutingDay.value === '全部') {
      let plannedDaysCount = 0
      let totalPlannedRoutes = 0

      for (const day of DAYS_LIST) {
        const dayStores = stores.value.filter((s) => {
          const dStr = s.schedule_day || s.delivery_days_str || ''
          return dStr.includes(day) && !isStoreExpressOnDay(s, day)
        })
        if (!dayStores.length) continue

        const reqPoints = [
          {
            name: canvas.depot_name || '中心仓',
            lng: Number(canvas.depot_lng),
            lat: Number(canvas.depot_lat),
            is_depot: true,
            avg_loads: 0,
            demand: 0,
          },
          ...dayStores.map((s) => {
            const boxes = Number(s.avg_loads || s.demand || s.weight || 10)
            return {
              ...s,
              name: s.name || '',
              shop_code: s.shop_code || '',
              dept_id: s.dept_id || '',
              lng: Number(s.lng),
              lat: Number(s.lat),
              is_depot: false,
              avg_loads: boxes,
              demand: boxes,
              weight: boxes,
              is_homepot: s.is_homepot !== undefined && s.is_homepot !== null ? Number(s.is_homepot) : 1,
            }
          }),
        ]

        const payload = {
          points: reqPoints,
          trucks: trucks.value,
          algorithm: 'ortools',
          options: routeOptions.value,
        }

        const res = await routingApi.solve(payload)
        const mappedRoutes = (res.routes || []).map((r, rIdx) => {
          const storeIndices = (r.order || []).filter((idx) => idx !== -1)
          const routeStores = storeIndices.map((idx) => dayStores[idx]).filter(Boolean)
          const totalLoad =
            r.load !== undefined
              ? Number(r.load)
              : routeStores.reduce((sum, st) => sum + Number(st.avg_loads || st.demand || 10), 0)
          const distKm = r.distance !== undefined ? Number(r.distance) : Number(r.distance_km || 0)

          return {
            ...r,
            day,
            day_route_idx: rIdx,
            vehicle_name: r.truck_name || `货车 ${rIdx + 1}`,
            truck_name: r.truck_name || `货车 ${rIdx + 1}`,
            return_to_depot: Boolean(routeOptions.value?.return_to_depot),
            load: Math.round(totalLoad),
            total_weight: Math.round(totalLoad),
            avg_loads: Math.round(totalLoad),
            distance: Number(distKm.toFixed(1)),
            distance_km: Number(distKm.toFixed(1)),
            points: routeStores,
            stops: routeStores,
          }
        })

        dailyResults.value[day] = {
          ...res,
          routes: mappedRoutes,
          day,
        }
        totalPlannedRoutes += mappedRoutes.length
        plannedDaysCount++
      }

      isRoutingOutdated.value = false
      canvas.stage = 'ROUTED'
      ElMessage.success(`🎉 全周多日路线规划完成！共规划 ${plannedDaysCount} 个作业日，生成 ${totalPlannedRoutes} 条配送线路。`)
      emit('render-map', true)
    } else {
      const day = selectedRoutingDay.value
      const dayStores = stores.value.filter((s) => {
        const dStr = s.schedule_day || s.delivery_days_str || ''
        return dStr.includes(day) && !isStoreExpressOnDay(s, day)
      })

      if (!dayStores.length) {
        ElMessage.warning(`「${day}」无常规货车配送门店（或全部为快递直发）`)
        return
      }

      const reqPoints = [
        {
          name: canvas.depot_name || '中心仓',
          lng: Number(canvas.depot_lng),
          lat: Number(canvas.depot_lat),
          is_depot: true,
          avg_loads: 0,
          demand: 0,
        },
        ...dayStores.map((s) => {
          const boxes = Number(s.avg_loads || s.demand || s.weight || 10)
          return {
            ...s,
            name: s.name || '',
            shop_code: s.shop_code || '',
            dept_id: s.dept_id || '',
            lng: Number(s.lng),
            lat: Number(s.lat),
            is_depot: false,
            avg_loads: boxes,
            demand: boxes,
            weight: boxes,
            is_homepot: s.is_homepot !== undefined && s.is_homepot !== null ? Number(s.is_homepot) : 1,
          }
        }),
      ]

      const payload = {
        points: reqPoints,
        trucks: trucks.value,
        algorithm: 'ortools',
        options: routeOptions.value,
      }

      const res = await routingApi.solve(payload)
      const mappedRoutes = (res.routes || []).map((r, rIdx) => {
        const storeIndices = (r.order || []).filter((idx) => idx !== -1)
        const routeStores = storeIndices.map((idx) => dayStores[idx]).filter(Boolean)
        const totalLoad =
          r.load !== undefined
            ? Number(r.load)
            : routeStores.reduce((sum, st) => sum + Number(st.avg_loads || st.demand || 10), 0)
        const distKm = r.distance !== undefined ? Number(r.distance) : Number(r.distance_km || 0)

        return {
          ...r,
          day,
          day_route_idx: rIdx,
          vehicle_name: r.truck_name || `货车 ${rIdx + 1}`,
          truck_name: r.truck_name || `货车 ${rIdx + 1}`,
          return_to_depot: Boolean(routeOptions.value?.return_to_depot),
          load: Math.round(totalLoad),
          total_weight: Math.round(totalLoad),
          avg_loads: Math.round(totalLoad),
          distance: Number(distKm.toFixed(1)),
          distance_km: Number(distKm.toFixed(1)),
          points: routeStores,
          stops: routeStores,
        }
      })

      dailyResults.value[day] = {
        ...res,
        routes: mappedRoutes,
        day,
      }

      isRoutingOutdated.value = false
      canvas.stage = 'ROUTED'
      ElMessage.success(`🎉「${day}」路线规划完成，生成 ${mappedRoutes.length} 条配送线路！其他作业日方案已完整保留。`)
      emit('render-map', true)
    }
  } catch (err) {
    ElMessage.error(`路径求解失败: ${err.message}`)
  } finally {
    routingLoading.value = false
  }
}

const calculateSingleAmapRoute = async (targetRoute, idx) => {
  await measureSingleRoute(targetRoute, idx, {
    depotLng: canvas.depot_lng,
    depotLat: canvas.depot_lat,
    returnToDepot: routeOptions.value.return_to_depot,
    onSuccess: () => {
      emit('render-map')
    },
  })
}

const batchMeasureAMapRoutes = async () => {
  await batchMeasureRoutes(routes.value, {
    depotLng: canvas.depot_lng,
    depotLat: canvas.depot_lat,
    returnToDepot: routeOptions.value.return_to_depot,
    onSingleSuccess: () => {
      emit('render-map')
    },
    onAllCompleted: () => {
      emit('render-map')
    },
  })
}

const handleMoveStoreOrder = (rIdx, storeSeq, direction) => {
  const displayList = currentDisplayRoutes.value
  const r = displayList[rIdx]
  if (!r) return
  const sourceDay = r.day || (selectedRoutingDay.value !== '全部' ? selectedRoutingDay.value : '周一')
  const dayRes = dailyResults.value[sourceDay]
  const dayRoutes = dayRes?.routes || routes.value
  if (!dayRoutes) return
  const dayRoute = dayRoutes[r.day_route_idx ?? rIdx]
  if (!dayRoute || !dayRoute.points) return

  const newIndex = storeSeq + direction
  if (newIndex < 0 || newIndex >= dayRoute.points.length) return

  const temp = dayRoute.points[storeSeq]
  dayRoute.points[storeSeq] = dayRoute.points[newIndex]
  dayRoute.points[newIndex] = temp
  dayRoute.stops = dayRoute.points
  clearRouteMeasureCache(dayRoute)

  recalculateRouteMetrics()
  emit('render-map')
}

const handleReorderStore = (rIdx, fromIdx, toIdx) => {
  const displayList = currentDisplayRoutes.value
  const r = displayList[rIdx]
  if (!r) return
  const sourceDay = r.day || (selectedRoutingDay.value !== '全部' ? selectedRoutingDay.value : '周一')
  const dayRes = dailyResults.value[sourceDay]
  const dayRoutes = dayRes?.routes || routes.value
  if (!dayRoutes) return
  const dayRoute = dayRoutes[r.day_route_idx ?? rIdx]
  if (!dayRoute || !dayRoute.points) return

  const list = dayRoute.points
  if (fromIdx < 0 || fromIdx >= list.length || toIdx < 0 || toIdx >= list.length || fromIdx === toIdx) return

  const [movedItem] = list.splice(fromIdx, 1)
  list.splice(toIdx, 0, movedItem)
  dayRoute.stops = list
  clearRouteMeasureCache(dayRoute)

  recalculateRouteMetrics()
  emit('render-map')
}

const handleMoveStoreBetweenRoutes = (sourceRouteIdx, storeSeq, targetRouteVal) => {
  moveStoreBetweenRoutes(sourceRouteIdx, storeSeq, targetRouteVal, () => emit('render-map'))
}
</script>

<style scoped>
.stage-content-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.panel-section {
  margin-bottom: 2px;
}

.section-title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 4px 0;
}

.section-desc {
  font-size: 11px;
  color: #64748b;
  margin: 0;
  line-height: 1.4;
}

.panel-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 11px;
  font-weight: 600;
  color: #475569;
}

.fleet-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.fleet-tag {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.fleet-tag-cap {
  color: #64748b;
  font-size: 10px;
}

.remove-tag {
  color: #94a3b8;
  cursor: pointer;
  font-weight: 700;
}

.remove-tag:hover {
  color: #ef4444;
}
</style>
