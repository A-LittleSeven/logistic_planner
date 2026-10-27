<template>
  <div class="route-plan-list-container">
    <div class="route-header-toolbar" style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap;">
      <div>
        <span style="font-size: 13px; font-weight: 700; color: #334155;">
          规划路线 (共 {{ routes.length }} 条线路)
        </span>
        <span style="font-size: 11px; color: #0284c7; margin-left: 6px;">总里程: {{ totalDistanceKm }} km</span>
      </div>

      <!-- Batch AMap Measuring Action Button -->
      <el-button
        size="small"
        type="success"
        plain
        :loading="batchMeasuring"
        :disabled="!routes.length"
        style="height: 24px; padding: 2px 8px; font-size: 11px; font-weight: 600;"
        @click="$emit('batch-calculate-amap')"
      >
        {{ batchMeasuring ? `测算中 (${measureProgress?.percent || 0}%)` : '⚡ 一键高德路网测算' }}
      </el-button>
    </div>

    <!-- Summary Stats Grid (总行驶里程、配送门店数、启用车辆数、平均装载) -->
    <div v-if="showSummary && routes.length" class="summary-stats-grid">
      <div class="stat-box">
        <span class="stat-label">总行驶里程</span>
        <span class="stat-val" style="color: #0284c7;">
          {{ totalDistanceKm }} <small>km</small>
        </span>
      </div>
      <div class="stat-box">
        <span class="stat-label">配送门店数</span>
        <span class="stat-val" style="color: #10b981;">
          {{ totalStoresCount }} <small>家</small>
        </span>
      </div>
      <div class="stat-box">
        <span class="stat-label">启用车辆数</span>
        <span class="stat-val" style="color: #6366f1;">
          {{ totalVehiclesCount }} <small>辆</small>
        </span>
      </div>
      <div class="stat-box">
        <span class="stat-label">平均车装载</span>
        <span class="stat-val" style="color: #f59e0b;">
          {{ avgTruckLoad }} <small>箱/车</small>
        </span>
      </div>
    </div>

    <!-- Batch Measuring Progress Banner -->
    <div v-if="batchMeasuring" class="batch-measure-progress-banner">
      <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px; color: #166534; font-weight: 600;">
        <span>🛣️ 正在批量测算货车路网: {{ measureProgress?.currentRouteName || '准备中...' }}</span>
        <span>{{ measureProgress?.current || 0 }} / {{ measureProgress?.total || routes.length }}</span>
      </div>
      <el-progress
        :percentage="measureProgress?.percent || 0"
        :stroke-width="6"
        color="#10b981"
        :show-text="false"
      />
    </div>

    <!-- Focus Mode Indicator Banner -->
    <div
      v-if="highlightedRouteIdx !== null && routes[highlightedRouteIdx]"
      class="focus-indicator-banner"
    >
      <span>
        🔍 已高亮聚焦【{{ getRouteTitle(routes[highlightedRouteIdx], highlightedRouteIdx) }}】
      </span>
      <button class="exit-focus-btn" @click="$emit('toggle-highlight', highlightedRouteIdx)">
        退出聚焦
      </button>
    </div>

    <div class="route-cards-list">
      <div
        v-for="(r, idx) in routes"
        :key="idx"
        class="route-card-item"
        :class="{ 'is-highlighted': highlightedRouteIdx === idx }"
        :style="{ borderLeftColor: getColor(idx) }"
        @click="$emit('toggle-highlight', idx)"
      >
        <div class="route-header-row">
          <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
            <span class="color-dot" :style="{ background: getColor(idx) }"></span>
            <span class="route-title" :style="{ color: getColor(idx) }">
              {{ getRouteTitle(r, idx) }}
            </span>
            <span class="truck-tag">{{ r.vehicle_name || r.truck_name || '默认车型' }}</span>
            <span
              class="homepot-tag"
              :style="Number(r.points?.[0]?.is_homepot ?? r.stops?.[0]?.is_homepot ?? r.is_homepot ?? 0) === 1 ? 'background: #e0f2fe; color: #0369a1;' : 'background: #fef3c7; color: #b45309;'"
            >
              {{ Number(r.points?.[0]?.is_homepot ?? r.stops?.[0]?.is_homepot ?? r.is_homepot ?? 0) === 1 ? '🏠 本埠' : '🚗 外埠' }}
            </span>

            <el-button
              size="small"
              :type="highlightedRouteIdx === idx ? 'warning' : 'default'"
              plain
              style="padding: 1px 6px; height: 20px; font-size: 10px; border-radius: 4px; margin-left: 2px;"
              @click.stop="$emit('toggle-highlight', idx)"
            >
              {{ highlightedRouteIdx === idx ? '🔍 退出聚焦' : '🔍 聚焦' }}
            </el-button>

            <el-button
              size="small"
              :type="r.amap_distance ? 'success' : 'primary'"
              plain
              :loading="loadingAmapRouteKey === idx || loadingAmapRouteKey === `all_${idx}` || loadingAmapRouteKey === `day_${idx}`"
              style="padding: 1px 6px; height: 20px; font-size: 10px; border-radius: 4px; margin-left: 2px;"
              @click.stop="$emit('calculate-amap', { route: r, routeIdx: idx })"
            >
              {{ r.amap_distance ? '🗺️ 已测路网' : '🗺️ 测算路网' }}
            </el-button>
          </div>

          <div class="route-metrics-row">
            <span><strong>{{ r.distance ?? r.distance_km ?? 0 }}</strong> km</span>
            <span style="margin: 0 3px; color: #cbd5e1;">|</span>
            <span><strong>{{ Math.round(r.load ?? r.total_weight ?? r.avg_loads ?? 0) }}</strong> 箱</span>
          </div>
        </div>

        <!-- AMap Measured Banner -->
        <div
          v-if="r.amap_distance"
          class="amap-measured-banner"
        >
          <span>
            🛣️ 高德货车路网: <strong>{{ r.amap_distance }} km</strong> · 约 <strong>{{ formatDuration(r.amap_duration) }}</strong>
            <span v-if="r.amap_tolls > 0"> (高速费 ¥{{ r.amap_tolls }})</span>
          </span>
          <el-tag size="small" type="success" effect="light" style="height: 18px; font-size: 10px;">AMap.TruckDriving</el-tag>
        </div>

        <div class="route-store-count-row">
          <span>途经门店 ({{ (r.points || r.stops || []).length }} 家):</span>
          <button class="expand-btn" @click.stop="toggleExpandRoute(idx)">
            {{ expandedRouteIndices.has(idx) ? '收起详情 ▴' : '展开到店次序 ▾' }}
          </button>
        </div>

        <!-- Expanded Store Sequence: Single-line draggable list -->
        <div v-if="expandedRouteIndices.has(idx)" class="route-stores-list" @click.stop>
          <div
            v-for="(p, sIdx) in (r.points || r.stops || [])"
            :key="p.id || p.shop_code || sIdx"
            class="route-store-row-draggable"
            :class="{
              'is-dragging': draggedRouteIdx === idx && draggedStoreIdx === sIdx,
              'is-drag-over': draggedRouteIdx === idx && dragOverStoreIdx === sIdx && draggedStoreIdx !== sIdx
            }"
            draggable="true"
            @dragstart="handleDragStart(idx, sIdx, $event)"
            @dragover.prevent="handleDragOver(idx, sIdx, $event)"
            @dragleave="handleDragLeave(idx, sIdx, $event)"
            @drop="handleDrop(idx, sIdx, $event)"
            @click="$emit('select-store', p)"
          >
            <!-- 拖拽把手图标 -->
            <span class="drag-handle" title="按住拖拽调整当前车次到店次序">⋮⋮</span>

            <!-- 到店次序序号 -->
            <span class="seq-badge" :style="{ background: getColor(idx) }">{{ sIdx + 1 }}</span>

            <!-- 只展示门店名称，占据整行剩余空间 -->
            <span class="store-name-text" :title="p.name || `门店${sIdx + 1}`">
              {{ p.name || `门店${sIdx + 1}` }}
            </span>

            <!-- 缩小尺寸的紧凑调换路线下拉框（只支持当天路线调换） -->
            <div class="store-transfer-wrap" @click.stop>
              <select
                class="transfer-select-compact"
                title="调换路线（仅限当天路线）"
                @click.stop
                @change="handleTransferSelect(idx, sIdx, $event)"
              >
                <option value="" disabled selected>⇄ 调线</option>
                <option
                  v-for="item in getAvailableTransferRoutes(r, idx)"
                  :key="item.oIdx"
                  :value="item.oIdx"
                  :disabled="item.oIdx === idx"
                >
                  {{ getRouteTitle(item.route, item.oIdx) }} ({{ item.route.vehicle_name || item.route.truck_name || '货车' }}, 已载{{ Math.round(item.route.load ?? item.route.total_weight ?? 0) }}箱)
                </option>
                <option value="new">+ 移至新路线</option>
                <option value="express" style="color: #7c3aed; font-weight: 700;">📦 移至快递直发 (不走货车)</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Express Delivery Stores Pool Section -->
    <div v-if="expressStores && expressStores.length" class="express-stores-section">
      <div class="express-header" @click="expressExpanded = !expressExpanded">
        <div style="display: flex; align-items: center; gap: 6px;">
          <span style="font-size: 14px;">📦</span>
          <span style="font-weight: 700; font-size: 12px; color: #7c3aed;">
            快递直发门店 ({{ expressStores.length }} 家)
          </span>
          <span style="font-size: 11px; color: #8b5cf6;">合计: {{ totalExpressLoads }} 箱</span>
        </div>
        <button class="expand-btn" style="color: #7c3aed;">
          {{ expressExpanded ? '收起 ▴' : '展开详情 ▾' }}
        </button>
      </div>

      <div v-if="expressExpanded" class="express-list">
        <div
          v-for="(s, sIdx) in expressStores"
          :key="sIdx"
          class="express-item-row"
          @click="$emit('select-store', s)"
        >
          <div class="express-store-info">
            <span class="express-badge">📦</span>
            <div style="overflow: hidden;">
              <div class="express-name" :title="s.name">{{ s.name || `门店${sIdx + 1}` }}</div>
              <div style="font-size: 10px; color: #94a3b8;">
                {{ s.district ? s.district + ' · ' : '' }}{{ s.avg_loads || s.weight || 10 }}箱
                <span v-if="s.day || s.delivery_days_str"> · {{ s.day || s.delivery_days_str }}</span>
              </div>
            </div>
          </div>

          <button
            class="restore-btn"
            title="将该门店从快递池恢复到常规货车配送路线"
            @click.stop="$emit('restore-express-store', s)"
          >
            🚛 恢复货车配送
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { formatDuration } from '../../utils/constants.js'

const props = defineProps({
  routes: {
    type: Array,
    default: () => [],
  },
  expressStores: {
    type: Array,
    default: () => [],
  },
  highlightedRouteIdx: {
    type: [Number, String],
    default: null,
  },
  loadingAmapRouteKey: {
    type: [Number, String],
    default: null,
  },
  batchMeasuring: {
    type: Boolean,
    default: false,
  },
  measureProgress: {
    type: Object,
    default: () => ({ current: 0, total: 0, percent: 0, currentRouteName: '' }),
  },
  getRouteColor: {
    type: Function,
    default: null,
  },
  showSummary: {
    type: Boolean,
    default: true,
  },
})

const emit = defineEmits([
  'toggle-highlight',
  'calculate-amap',
  'batch-calculate-amap',
  'move-store-order',
  'reorder-store',
  'transfer-store',
  'restore-express-store',
  'select-store',
])

const expandedRouteIndices = ref(new Set())
const expressExpanded = ref(true)

// Drag & drop state for store sequence reordering
const draggedRouteIdx = ref(null)
const draggedStoreIdx = ref(null)
const dragOverStoreIdx = ref(null)

const handleDragStart = (rIdx, sIdx, event) => {
  draggedRouteIdx.value = rIdx
  draggedStoreIdx.value = sIdx
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', String(sIdx))
}

const handleDragOver = (rIdx, sIdx, event) => {
  if (draggedRouteIdx.value !== rIdx) return
  event.preventDefault()
  event.dataTransfer.dropEffect = 'move'
  dragOverStoreIdx.value = sIdx
}

const handleDragLeave = (rIdx, sIdx) => {
  if (dragOverStoreIdx.value === sIdx) {
    dragOverStoreIdx.value = null
  }
}

const handleDrop = (rIdx, toIdx, event) => {
  event.preventDefault()
  if (draggedRouteIdx.value === null || draggedStoreIdx.value === null) return
  if (draggedRouteIdx.value !== rIdx) {
    draggedRouteIdx.value = null
    draggedStoreIdx.value = null
    dragOverStoreIdx.value = null
    return
  }

  const fromIdx = draggedStoreIdx.value
  draggedRouteIdx.value = null
  draggedStoreIdx.value = null
  dragOverStoreIdx.value = null

  if (fromIdx === toIdx || fromIdx < 0 || toIdx < 0) return

  emit('reorder-store', { routeIdx: rIdx, fromIdx, toIdx })
}

// 路线调换过滤：只支持当天的路线调换
const getAvailableTransferRoutes = (currentRoute, currentIdx) => {
  const allList = props.routes
  return allList
    .map((route, oIdx) => ({ route, oIdx }))
    .filter(({ route }) => {
      // 若当前路线有指定作业日，仅支持调换至相同作业日的其他路线
      if (currentRoute.day && route.day) {
        return currentRoute.day === route.day
      }
      return true
    })
}

const toggleExpandRoute = (idx) => {
  if (expandedRouteIndices.value.has(idx)) {
    expandedRouteIndices.value.delete(idx)
  } else {
    expandedRouteIndices.value.add(idx)
  }
}

const DEFAULT_ROUTE_COLORS = [
  '#0284c7', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4',
  '#84cc16', '#d97706', '#6366f1', '#14b8a6', '#f43f5e', '#a855f7',
]

const getColor = (idx) => {
  if (props.getRouteColor) {
    return props.getRouteColor(idx)
  }
  return DEFAULT_ROUTE_COLORS[Number(idx) % DEFAULT_ROUTE_COLORS.length]
}

const getRouteTitle = (r, idx) => {
  if (r.day && r.day_route_idx !== undefined) {
    return `${r.day} 路线 ${r.day_route_idx + 1}`
  }
  return r.route_title || `路线 ${idx + 1}`
}

const totalDistanceKm = computed(() => {
  const sum = props.routes.reduce((acc, r) => {
    return acc + (Number(r.distance ?? r.distance_km) || 0)
  }, 0)
  return sum.toFixed(1)
})

const totalStoresCount = computed(() => {
  return props.routes.reduce((acc, r) => {
    return acc + (r.points || r.stops || []).length
  }, 0)
})

const totalVehiclesCount = computed(() => {
  return props.routes.length
})

const avgTruckLoad = computed(() => {
  if (!props.routes.length) return 0
  const totalLoad = props.routes.reduce((acc, r) => {
    return acc + (Number(r.load ?? r.total_weight ?? r.avg_loads) || 0)
  }, 0)
  return Math.round(totalLoad / props.routes.length)
})

const totalExpressLoads = computed(() => {
  if (!props.expressStores) return 0
  const sum = props.expressStores.reduce((acc, s) => {
    return acc + (Number(s.avg_loads || s.weight || s.demand || 10) || 0)
  }, 0)
  return Math.round(sum)
})

const handleTransferSelect = (routeIdx, storeIdx, event) => {
  const targetRouteIdx = event.target.value
  emit('transfer-store', { fromRouteIdx: routeIdx, storeIdx, targetRouteIdx })
  event.target.value = ''
}
</script>

<style scoped>
.route-plan-list-container {
  display: flex;
  flex-direction: column;
}

.batch-measure-progress-banner {
  margin-bottom: 10px;
  padding: 8px 10px;
  background: #f0fdf4;
  border: 1px solid #86efac;
  border-radius: 6px;
}

.focus-indicator-banner {
  margin-bottom: 10px;
  padding: 6px 10px;
  background: #e0f2fe;
  border: 1px solid #7dd3fc;
  border-radius: 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: #0369a1;
}

.exit-focus-btn {
  border: none;
  background: transparent;
  color: #0284c7;
  font-weight: 700;
  cursor: pointer;
  font-size: 11px;
  text-decoration: underline;
}

.route-cards-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 420px;
  overflow-y: auto;
  padding-right: 2px;
}

.route-card-item {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-left-width: 4px;
  border-radius: 6px;
  padding: 8px 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.route-card-item:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.route-card-item.is-highlighted {
  background: #f0f9ff;
  border-color: #0284c7;
  box-shadow: 0 0 0 1px #0284c7;
}

.route-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.color-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.route-title {
  font-weight: 700;
  font-size: 12px;
}

.truck-tag {
  font-size: 10px;
  color: #475569;
  background: #f1f5f9;
  padding: 1px 5px;
  border-radius: 3px;
}

.homepot-tag {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: 600;
}

.route-metrics-row {
  font-size: 11px;
  color: #64748b;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.amap-measured-banner {
  margin: 6px 0 2px;
  padding: 3px 6px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 4px;
  font-size: 10px;
  color: #166534;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.route-store-count-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: #64748b;
  margin-top: 6px;
}

.expand-btn {
  border: none;
  background: transparent;
  color: #0284c7;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 3px;
}

.expand-btn:hover {
  background: #f0f9ff;
}

/* Summary Stats Grid */
.summary-stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin-bottom: 10px;
}

.stat-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 6px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: 11px;
  color: #64748b;
}

.stat-val {
  font-size: 15px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-val small {
  font-size: 11px;
  font-weight: normal;
  color: #64748b;
  margin-left: 2px;
}

.route-stores-list {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.route-store-row-draggable {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  transition: background 0.15s, border-color 0.15s, transform 0.15s;
  cursor: pointer;
  user-select: none;
  min-height: 28px;
  box-sizing: border-box;
}

.route-store-row-draggable:hover {
  background: #ffffff;
  border-color: #cbd5e1;
}

.route-store-row-draggable.is-dragging {
  opacity: 0.35;
  background: #f1f5f9;
  border: 1px dashed #0284c7;
}

.route-store-row-draggable.is-drag-over {
  border-top: 2px solid #0284c7;
  background: #f0f9ff;
  transform: translateY(1px);
}

.drag-handle {
  color: #94a3b8;
  cursor: grab;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  padding: 2px 2px;
  letter-spacing: -1px;
  flex-shrink: 0;
  transition: color 0.15s;
}

.drag-handle:hover {
  color: #334155;
}

.drag-handle:active {
  cursor: grabbing;
}

.seq-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  color: #ffffff;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}

.store-name-text {
  color: #1e293b;
  font-weight: 500;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.store-transfer-wrap {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.transfer-select-compact {
  font-size: 10px;
  height: 20px;
  line-height: 18px;
  padding: 0 4px;
  border: 1px solid #cbd5e1;
  border-radius: 3px;
  background: #ffffff;
  color: #0284c7;
  font-weight: 600;
  cursor: pointer;
  max-width: 68px;
  outline: none;
  transition: all 0.15s;
}

.transfer-select-compact:hover {
  border-color: #0284c7;
  background: #f0f9ff;
}

/* Express Section */
.express-stores-section {
  background: #faf5ff;
  border: 1px solid #e9d5ff;
  border-left: 4px solid #8b5cf6;
  border-radius: 6px;
  padding: 8px 10px;
  margin-top: 10px;
}

.express-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
}

.express-list {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed #e9d5ff;
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 180px;
  overflow-y: auto;
}

.express-item-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 6px;
  background: #ffffff;
  border: 1px solid #f3e8ff;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s;
}

.express-item-row:hover {
  background: #f5f3ff;
}

.express-store-info {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
  max-width: 200px;
}

.express-badge {
  font-size: 12px;
  flex-shrink: 0;
}

.express-name {
  font-size: 11px;
  font-weight: 600;
  color: #581c87;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.restore-btn {
  border: 1px solid #c4b5fd;
  background: #ffffff;
  color: #7c3aed;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 3px;
  cursor: pointer;
  white-space: nowrap;
}

.restore-btn:hover {
  background: #7c3aed;
  color: #ffffff;
}
</style>
