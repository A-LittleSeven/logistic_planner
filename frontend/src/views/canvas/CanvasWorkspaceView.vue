<template>
  <div class="canvas-workspace-container">
    <!-- Top Canvas Scope & Version Bar -->
    <div class="canvas-scope-header">
      <div class="scope-left">
        <el-button link :icon="ArrowLeft" @click="router.push('/canvas')">返回画布列表</el-button>
        <div class="divider-vertical"></div>
        <div class="canvas-title-wrapper">
          <span class="canvas-title" :title="canvas.name">{{ canvas.name }}</span>
          <el-button link size="small" :icon="Edit" @click="openRenameModal" />
        </div>
        <div class="depot-tag">
          <el-icon><OfficeBuilding /></el-icon>
          <span>{{ canvas.depot_name || '中心仓' }}</span>
          <span class="coords">[{{ formatCoord(canvas.depot_lng) }}, {{ formatCoord(canvas.depot_lat) }}]</span>
        </div>
        <el-tag size="small" effect="plain" type="info">
          {{ stores.length }} 家规划门店 ({{ totalLoads }} 箱)
        </el-tag>
      </div>

      <div class="scope-right">
        <!-- Version Badge & Switcher -->
        <div class="version-control-box">
          <el-dropdown trigger="click" @command="handleSelectVersion">
            <span class="current-version-pill" :title="`当前版本：V${currentVersion?.version_number || 1} - ${currentVersion?.version_name || '初始版本'}`">
              <span class="dot"></span>
              <strong class="v-num-badge">V{{ currentVersion?.version_number || 1 }}</strong>
              <el-icon style="font-size: 11px; margin-left: 2px; color: #64748b;"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu class="version-dropdown-menu">
                <div class="dropdown-header">历史版本快照 (点击载入使用)</div>
                <el-dropdown-item
                  v-for="v in versionList"
                  :key="v.id"
                  :command="v.id"
                  :class="{ 'is-active-v': v.id === currentVersion?.id }"
                >
                  <div class="version-item-row">
                    <span class="v-num">V{{ v.version_number }}</span>
                    <div class="v-info-col">
                      <span class="v-title">{{ v.version_name }}</span>
                      <span v-if="v.change_summary" class="v-summary">{{ v.change_summary }}</span>
                    </div>
                    <span class="v-date">{{ formatTimeShort(v.created_at) }}</span>
                  </div>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <el-button type="success" size="small" :icon="DocumentChecked" @click="openSaveVersionModal">
          保存新版本
        </el-button>
        <el-button size="small" :icon="Timer" @click="versionDrawerVisible = true">
          版本历史
        </el-button>
        <el-button size="small" :icon="Download" @click="exportCanvasExcel">
          导出Excel
        </el-button>
      </div>
    </div>

    <!-- Main Workspace: Left Planning Panel & Right Map -->
    <div class="workspace-main">
      <!-- Left Stage Control Panel -->
      <div class="stage-sidebar">
        <!-- Stage Tabs with Status Badges -->
        <div class="stage-tabs-nav">
          <div
            class="stage-tab-btn"
            :class="{ active: activeStage === 'clustering', 'is-completed': hasClusteringComputed }"
            @click="switchStage('clustering')"
          >
            <span class="step-num">{{ hasClusteringComputed ? '✓' : '1' }}</span>
            <div class="step-text-col">
              <span class="step-text">店群规划</span>
              <span v-if="hasClusteringComputed" class="step-badge-text">{{ clusteringResult.clusters.length }} 个店群</span>
            </div>
          </div>
          <div
            class="stage-tab-btn"
            :class="{ active: activeStage === 'scheduling', 'is-completed': hasScheduleComputed }"
            @click="switchStage('scheduling')"
          >
            <span class="step-num">{{ hasScheduleComputed ? '✓' : '2' }}</span>
            <div class="step-text-col">
              <span class="step-text">周排班规划</span>
              <span v-if="hasScheduleComputed" class="step-badge-text">全周已均衡</span>
            </div>
          </div>
          <div
            class="stage-tab-btn"
            :class="{ active: activeStage === 'routing', 'is-completed': hasRoutingComputed }"
            @click="switchStage('routing')"
          >
            <span class="step-num">{{ hasRoutingComputed ? '✓' : '3' }}</span>
            <div class="step-text-col">
              <span class="step-text">路线规划</span>
              <span v-if="hasRoutingComputed" class="step-badge-text">{{ routes.length }} 条线路</span>
            </div>
          </div>
        </div>

        <!-- Stage 1: Clustering -->
        <ClusteringStage
          v-show="activeStage === 'clustering'"
          @render-map="renderMap"
          @toggle-box-select="toggleBoxSelect"
        />

        <!-- Stage 2: Scheduling -->
        <SchedulingStage
          v-show="activeStage === 'scheduling'"
          @render-map="renderMap"
          @toggle-box-select="toggleBoxSelect"
          @open-schedule-config="scheduleConfigDialogVisible = true"
        />

        <!-- Stage 3: Routing -->
        <RoutingStage
          v-show="activeStage === 'routing'"
          @render-map="renderMap"
          @open-fleet-config="fleetModalVisible = true"
          @open-route-config="routeConfigDialogVisible = true"
          @open-express-modal="expressModalVisible = true"
          @toggle-highlight="(rIdx) => toggleHighlightRoute(rIdx)"
          @select-store="handleSelectStore"
        />
      </div>

      <!-- Right Map View -->
      <div class="stage-map-wrapper">
        <MapStoreSearch :stores="stores" @select="handleSelectStore" />
        <MapPanel ref="mapPanelRef" @map-ready="onMapReady" />
      </div>
    </div>

    <!-- Modals & Drawers -->
    <SaveVersionDialog
      v-model:visible="saveVersionModalVisible"
      v-model:version-name="newVersionName"
      v-model:change-summary="newVersionChangeSummary"
      :current-version-number="currentVersion?.version_number || 1"
      :loading="savingVersion"
      @submit="submitSaveVersion"
    />

    <VersionHistoryDrawer
      v-model:visible="versionDrawerVisible"
      :version-list="versionList"
      :current-version="currentVersion"
      @rollback="rollbackToVersion"
    />

    <RenameCanvasDialog
      v-model:visible="renameModalVisible"
      v-model:name="canvasRenameText"
      @submit="submitRename"
    />

    <FleetConfigDialog
      v-model:visible="fleetModalVisible"
      v-model:trucks="trucks"
    />

    <ScheduleConfigDialog
      v-model:visible="scheduleConfigDialogVisible"
      v-model:options="scheduleOptions"
      :default-options="defaultScheduleOptions"
    />

    <RouteConfigDialog
      v-model:visible="routeConfigDialogVisible"
      v-model:options="routeOptions"
      :default-options="defaultRouteOptions"
    />

    <ExpressManagerModal
      v-model:visible="expressModalVisible"
      :stores="stores"
      :current-day="selectedRoutingDay"
      @toggle-express="({ store, day, isExpress }) => handleToggleStoreExpress(store, day, isExpress, renderMap)"
      @batch-set-express="({ targets, day, isExpress }) => handleBatchSetStoresExpress(targets, day, isExpress, renderMap)"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  ArrowDown,
  Edit,
  OfficeBuilding,
  DocumentChecked,
  Timer,
  Download,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

// Composable & Subcomponents
import { provideCanvasState } from './composables/useCanvasState.js'
import { useCanvasVersioning } from './composables/useCanvasVersioning.js'
import { useCanvasMapLayers } from './composables/useCanvasMapLayers.js'

import ClusteringStage from './stages/ClusteringStage.vue'
import SchedulingStage from './stages/SchedulingStage.vue'
import RoutingStage from './stages/RoutingStage.vue'

import SaveVersionDialog from './dialogs/SaveVersionDialog.vue'
import VersionHistoryDrawer from './dialogs/VersionHistoryDrawer.vue'
import RenameCanvasDialog from './dialogs/RenameCanvasDialog.vue'
import FleetConfigDialog from './dialogs/FleetConfigDialog.vue'
import ScheduleConfigDialog from './dialogs/ScheduleConfigDialog.vue'
import RouteConfigDialog from './dialogs/RouteConfigDialog.vue'

import MapPanel from '../../components/MapPanel.vue'
import MapStoreSearch from '../../components/MapStoreSearch.vue'
import ExpressManagerModal from '../../components/planning/ExpressManagerModal.vue'

const route = useRoute()
const router = useRouter()
const canvasId = route.params.id

// Initialize Core Canvas State via provide
const canvasState = provideCanvasState(canvasId)
const {
  canvas,
  currentVersion,
  versionList,
  activeStage,
  stores,
  clusteringResult,
  dailyResults,
  trucks,
  selectedRoutingDay,
  scheduleOptions,
  defaultScheduleOptions,
  routeOptions,
  defaultRouteOptions,
  totalLoads,
  routes,
  hasClusteringComputed,
  hasScheduleComputed,
  hasRoutingComputed,
  mapPanelRef,
  amapInstance,
  highlightedClusterId,
  handleToggleStoreExpress,
  handleBatchSetStoresExpress,
  moveStoreBetweenRoutes,
  recalculateClusterMetrics,
  invalidateDownstreamStagesFromClustering,
  invalidateDownstreamStagesFromScheduling,
} = canvasState

// Initialize Map Layer Renderer
const {
  renderMap,
  toggleBoxSelect,
  initMouseTool,
  destroyMouseTool,
  toggleHighlightRoute,
} = useCanvasMapLayers(canvasState)

// Initialize Versioning
const {
  savingVersion,
  saveVersionModalVisible,
  newVersionName,
  newVersionChangeSummary,
  versionDrawerVisible,
  renameModalVisible,
  canvasRenameText,
  fetchCanvasData,
  openSaveVersionModal,
  submitSaveVersion,
  handleSelectVersion,
  rollbackToVersion,
  openRenameModal,
  submitRename,
  exportCanvasExcel,
} = useCanvasVersioning(canvasState, {
  onSnapshotLoaded: () => renderMap(true),
})

// Dialog Visibility
const fleetModalVisible = ref(false)
const scheduleConfigDialogVisible = ref(false)
const routeConfigDialogVisible = ref(false)
const expressModalVisible = ref(false)

// Formatting Helpers
const formatCoord = (num) => (num ? Number(num).toFixed(4) : '--')
const formatTimeShort = (timeStr) => {
  if (!timeStr) return ''
  const d = new Date(timeStr)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const switchStage = (stage) => {
  activeStage.value = stage
  highlightedClusterId.value = null
  renderMap(true)
}

const onMapReady = async ({ map, AMap }) => {
  amapInstance.value = AMap
  renderMap()
}

const handleSelectStore = (item) => {
  if (!item || !item.lng || !item.lat) return
  const mapObj = mapPanelRef.value?.getMap()
  if (mapObj) mapObj.setZoomAndCenter(15, [Number(item.lng), Number(item.lat)])
}

// Global window actions for map InfoWindow button

window.moveCanvasStore = function (pointIdx, targetClusterVal) {
  let targetClusterId
  if (targetClusterVal === 'new') {
    targetClusterId = (clusteringResult.value?.clusters?.length || 0)
    if (!clusteringResult.value) clusteringResult.value = { clusters: [] }
    clusteringResult.value.clusters.push({
      cluster_id: targetClusterId,
      size: 0,
      point_indices: [],
    })
  } else {
    targetClusterId = Number(targetClusterVal)
  }

  if (stores.value[pointIdx]) {
    stores.value[pointIdx].cluster_id = targetClusterId
    // 关闭当前打开的高德信息窗，防止旧弹窗内容滞留
    const mapObj = mapPanelRef.value?.getMap()
    if (mapObj && typeof mapObj.clearInfoWindow === 'function') {
      mapObj.clearInfoWindow()
    }
    recalculateClusterMetrics()
    invalidateDownstreamStagesFromClustering('单店调区')
    ElMessage.success(`已将门店移动至店群 ${targetClusterId + 1}，下游周排班与路线数据已同步重置`)
    renderMap()
  }
}

window.updateCanvasStoreSchedule = function (pointIdx, dayVal) {
  if (stores.value[pointIdx]) {
    stores.value[pointIdx].schedule_day = dayVal
    stores.value[pointIdx].delivery_days_str = dayVal
    const mapObj = mapPanelRef.value?.getMap()
    if (mapObj && typeof mapObj.clearInfoWindow === 'function') {
      mapObj.clearInfoWindow()
    }
    invalidateDownstreamStagesFromScheduling('单店排班修改')
    ElMessage.success(`已将门店排班修改为 ${dayVal}，下游路线数据已同步刷新`)
    renderMap()
  }
}

window.updateCanvasStoreAttr = function (idx, key, val) {
  if (stores.value[idx]) {
    if (['frequency', 'avg_loads', 'is_homepot', 'service_time'].includes(key)) {
      const num = Number(val)
      stores.value[idx][key] = isNaN(num) ? val : num
    } else {
      stores.value[idx][key] = val
    }
    const mapObj = mapPanelRef.value?.getMap()
    if (mapObj && typeof mapObj.clearInfoWindow === 'function') {
      mapObj.clearInfoWindow()
    }
    if (key === 'frequency') {
      // 配送频次改变会导致原排班方案模式不再匹配，需级联重置排班
      invalidateDownstreamStagesFromClustering('门店频次属性修改')
      ElMessage.success(`门店 [${stores.value[idx].name || idx + 1}] 配送频次已变更，下游排班与路线已同步重置`)
    } else {
      invalidateDownstreamStagesFromScheduling('门店基础属性修改')
      ElMessage.success(`门店 [${stores.value[idx].name || idx + 1}] 属性已更新，下游路线规划已刷新`)
    }
    renderMap()
  }
}

window.updateStoreExpressDay = function (globalIdx, day, isExp) {
  const store = stores.value[globalIdx]
  if (store) {
    handleToggleStoreExpress(store, day, Number(isExp), renderMap)
  }
}

window.updateStoreExpress = function (pointIdx, val) {
  if (stores.value[pointIdx]) {
    const store = stores.value[pointIdx]
    const isExp = Number(val)
    const targetDay = selectedRoutingDay.value || '全部'
    handleToggleStoreExpress(store, targetDay, isExp, renderMap)
  }
}

window.updateStoreRoute = function (sourceRouteIdx, storeSeq, targetVal) {
  moveStoreBetweenRoutes(sourceRouteIdx, storeSeq, targetVal, renderMap)
}

onMounted(async () => {
  await fetchCanvasData()
  if (mapPanelRef.value) {
    try {
      amapInstance.value = await (mapPanelRef.value.whenReady ? mapPanelRef.value.whenReady() : mapPanelRef.value.getAmap())
      await renderMap()
      initMouseTool()
    } catch (e) {
      console.warn('Map initialization in canvas workspace:', e)
    }
  }
})

onUnmounted(() => {
  delete window.updateStoreExpressDay
  delete window.moveCanvasStore
  delete window.updateCanvasStoreSchedule
  delete window.updateCanvasStoreAttr
  delete window.updateStoreExpress
  delete window.updateStoreRoute
  destroyMouseTool()
})
</script>

<style scoped>
.canvas-workspace-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 60px);
  background: #f8fafc;
  overflow: hidden;
}

/* Top Scope Header */
.canvas-scope-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 18px;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  z-index: 10;
  min-height: 52px;
  gap: 14px;
}

.scope-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.divider-vertical {
  width: 1px;
  height: 18px;
  background: #cbd5e1;
  flex-shrink: 0;
}

.canvas-title-wrapper {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  min-width: 0;
  flex-shrink: 1;
  border: 1px solid transparent;
}

.canvas-title-wrapper:hover {
  background: #f1f5f9;
  border-color: #e2e8f0;
}

.canvas-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: clamp(260px, 32vw, 550px);
  letter-spacing: -0.2px;
  line-height: 1.3;
}

.depot-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #0284c7;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  padding: 3px 8px;
  border-radius: 6px;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}

.depot-tag .coords {
  font-size: 10px;
  color: #0369a1;
  font-weight: normal;
}

.scope-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.scope-right .el-button {
  margin-left: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.version-control-box {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  flex-shrink: 0;
}

.current-version-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  height: 28px;
  line-height: 1;
  gap: 5px;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  padding: 0 10px;
  border-radius: 14px;
  font-size: 12px;
  color: #1e293b;
  transition: all 0.2s;
  white-space: nowrap;
}

.current-version-pill:hover {
  background: #f1f5f9;
  border-color: #0284c7;
}

.current-version-pill .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #16a34a;
  flex-shrink: 0;
}

.current-version-pill .v-num-badge {
  font-weight: 700;
  color: #0369a1;
  font-size: 12px;
}

/* Main Workspace */
.workspace-main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.stage-sidebar {
  width: 380px;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 6px rgba(0, 0, 0, 0.02);
  z-index: 5;
}

.stage-tabs-nav {
  display: flex;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.stage-tab-btn {
  flex: 1;
  padding: 12px 6px;
  text-align: center;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.stage-tab-btn:hover {
  color: #0284c7;
  background: #f1f5f9;
}

.stage-tab-btn.active {
  color: #0284c7;
  background: #ffffff;
  border-bottom-color: #0284c7;
}

.stage-tab-btn .step-num {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #e2e8f0;
  color: #475569;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
}

.stage-tab-btn.active .step-num {
  background: #0284c7;
  color: #ffffff;
}

.step-text-col {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
}

.step-badge-text {
  font-size: 9px;
  color: #10b981;
  font-weight: 700;
  line-height: 1;
  margin-top: 2px;
}

.stage-tab-btn.is-completed .step-num {
  background: #10b981 !important;
  color: #ffffff !important;
  font-weight: 800;
}

.stage-map-wrapper {
  flex: 1;
  position: relative;
  height: 100%;
}

/* Dropdown Menu Enhancements */
.dropdown-header {
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
  padding: 6px 12px;
  border-bottom: 1px solid #f1f5f9;
  background: #f8fafc;
}

.version-item-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 4px 0;
  max-width: 360px;
}

.version-item-row .v-num {
  font-weight: 700;
  color: #0284c7;
  font-size: 11px;
  background: #f0f9ff;
  padding: 1px 5px;
  border-radius: 4px;
  flex-shrink: 0;
}

.version-item-row .v-info-col {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.version-item-row .v-title {
  font-weight: 600;
  color: #1e293b;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.version-item-row .v-summary {
  font-size: 11px;
  color: #64748b;
  line-height: 1.3;
  white-space: normal;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.version-item-row .v-date {
  font-size: 10px;
  color: #94a3b8;
  flex-shrink: 0;
}

.is-active-v {
  background: #f0f9ff;
  color: #0284c7;
  font-weight: 600;
}
</style>
