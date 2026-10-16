<template>
  <div class="clustering-view-wrapper">
    <ViewLayout>
      <template #side>
        <div class="sidebar-header">
          <h2 class="lp-section-title">门店分组与店群规划</h2>
          <p class="desc">
            基于地理坐标、行政区划与运量属性进行算法分群。您可在地图上直接点击门店进行属性编辑与换区调度，并保存或载入规划方案。
          </p>
          <div v-if="dataSourceLabel" class="data-source-badge">
            📦 数据来源：{{ dataSourceLabel }}
          </div>
        </div>

        <!-- 1. Empty State Guidance Card -->
        <div v-if="!points.length" class="lp-card empty-guide-card">
          <div class="empty-guide-text" style="margin-bottom: 0;">
            💡 当前画布暂无门店数据，请从下方工具箱点击<strong>「📂 载入历史」</strong>或<strong>「📥 导入Excel」</strong>开始规划。
          </div>
        </div>

        <!-- 2. Data Scope Overview Card -->
        <div v-if="points.length" class="lp-card" style="margin-bottom: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 13px; font-weight: 600; color: #334155;">规划门店范围</span>
            <span style="font-size: 14px; font-weight: 700; color: #0284c7;">{{ points.length }} 家</span>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px; font-size: 12px; color: #64748b;">
            <span>日均总装载需求: <strong style="color: #16a34a;">{{ totalAvgLoads }}</strong> 箱</span>
            <span v-if="depotName" style="color: #64748b;">中心仓: {{ depotName }}</span>
          </div>
        </div>

        <!-- 3. Planning Strategy & Algorithm Settings -->
        <div class="lp-card" style="margin-bottom: 12px;">
          <!-- Central Warehouse (Depot) Point Selection -->
          <div class="form-group" style="margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <label class="form-label" style="margin-bottom: 0;">🏬 起点配送中心 (中心仓)</label>
              <span v-if="depotLng && depotLat" style="font-size: 11px; color: #10b981; font-family: monospace;">
                [{{ Number(depotLng).toFixed(4) }}, {{ Number(depotLat).toFixed(4) }}]
              </span>
            </div>
            <select v-model="selectedDepotKey" class="lp-input select-alg" @change="onDepotSelectChange">
              <option v-for="d in depotList" :key="d.dc_code || d.name" :value="d.dc_code || d.name">
                🏬 {{ d.name }} ({{ d.dc_code }})
              </option>
              <option value="custom">✏️ 自定义中心仓坐标...</option>
            </select>
            <div v-if="selectedDepotKey === 'custom'" style="display: flex; gap: 6px; margin-top: 6px;">
              <input v-model="depotName" class="lp-input" placeholder="仓库名称" style="flex: 1.2;" @change="onDepotCustomChange" />
              <input v-model.number="depotLng" class="lp-input" placeholder="经度" style="flex: 1;" @change="onDepotCustomChange" />
              <input v-model.number="depotLat" class="lp-input" placeholder="纬度" style="flex: 1;" @change="onDepotCustomChange" />
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">分组规划策略</label>
            <select v-model="algorithm" class="lp-input select-alg" @change="onAlgChange">
              <option value="kmeans">智能约束分组求解 (容量与距离约束)</option>
              <option value="district">行政区划归属分组 (纯行政区归属)</option>
              <option value="district_extension">行政区扩展拆分分组 (行政区合并与拆分)</option>
            </select>
          </div>

          <div v-if="algorithm === 'kmeans'" class="form-group" style="margin-top: 10px;">
            <label class="form-label">目标店群数 K</label>
            <input
              v-model.number="k"
              type="number"
              min="1"
              max="50"
              class="lp-input inline-input"
              @change="saveToLocalStorage"
            />
          </div>

          <div v-if="algorithm === 'district_extension'" class="form-row" style="margin-top: 10px; display: flex; gap: 8px;">
            <div class="form-group" style="flex: 1;">
              <label class="form-label">最小规模 (min)</label>
              <input
                v-model.number="minZoneSize"
                type="number"
                min="1"
                class="lp-input"
                @change="saveToLocalStorage"
              />
            </div>
            <div class="form-group" style="flex: 1;">
              <label class="form-label">最大规模 (max)</label>
              <input
                v-model.number="maxZoneSize"
                type="number"
                min="1"
                class="lp-input"
                @change="saveToLocalStorage"
              />
            </div>
          </div>
        </div>

        <!-- 4. Core Actions Toolbar -->
        <div class="actions-container lp-card">
          <div class="main-solve-row">
            <button
              class="lp-btn lp-btn--primary main-solve-btn"
              :disabled="loading || points.length < 2"
              @click="solve"
            >
              {{ loading ? '聚类求解计算中…' : '⚡ 执行智能店群聚类' }}
            </button>
          </div>

          <div class="actions-toolbar-grid">
            <button class="lp-btn lp-btn--ghost" :disabled="!points.length" @click="openSaveModal">
              💾 保存方案
            </button>
            <button class="lp-btn lp-btn--ghost" @click="openHistoryModal">
              📂 载入历史
            </button>
            <button class="lp-btn lp-btn--ghost" @click="triggerExcelImport">
              📥 导入Excel
            </button>
            <button
              class="lp-btn lp-btn--ghost"
              :class="{ 'is-box-selecting': isSelecting }"
              :disabled="!points.length"
              @click="toggleBoxSelect"
            >
              {{ isSelecting ? '取消框选' : '📐 框选调区' }}
            </button>
          </div>

          <input
            ref="excelFileInput"
            type="file"
            accept=".xlsx,.xls,.csv"
            style="display: none;"
            @change="handleExcelImport"
          />

          <div class="actions-footer-row">
            <button class="footer-sub-btn footer-clear-btn" :disabled="!points.length" @click="clearAll">
              🗑️ 清空画布
            </button>
          </div>
        </div>

        <!-- 5. Box Select Batch Operation Card -->
        <div v-if="selectedPointIndices.length" class="lp-card batch-action-card">
          <div class="batch-card-header">
            <span class="batch-card-title">
              <span class="batch-icon">📐</span>
              已框选 <strong>{{ selectedPointIndices.length }}</strong> 家门店
            </span>
            <button class="batch-close-btn" @click="selectedPointIndices = []">×</button>
          </div>
          
          <div class="batch-card-body">
            <!-- 1. Batch move cluster -->
            <div v-if="result" style="display: flex; flex-direction: column; gap: 4px;">
              <label style="font-size: 11px; font-weight: 600; color: #555;">批量换区到目标店群：</label>
              <div style="display: flex; gap: 6px;">
                <select v-model="batchTargetCluster" style="font-size: 12px; padding: 6px; flex: 1; border-radius: 4px; border: 1px solid #cbd5e1; background: white;">
                  <option value="" disabled>选择目标店群</option>
                  <option v-for="c in result.clusters" :key="c.cluster_id" :value="c.cluster_id">店群 {{ c.cluster_id + 1 }}</option>
                  <option value="new">+ 新建并加入新店群</option>
                </select>
                <button class="lp-btn" style="font-size: 11px; padding: 6px 12px;" :disabled="batchTargetCluster === ''" @click="applyBatchMove">应用</button>
              </div>
            </div>
            
            <div style="display: flex; gap: 8px; margin-top: 4px;">
              <button class="lp-btn lp-btn--danger" style="flex: 1; font-size: 11px; padding: 4px 0;" @click="batchDelete">批量删除所选</button>
              <button class="lp-btn lp-btn--ghost" style="flex: 1; font-size: 11px; padding: 4px 0;" @click="selectedPointIndices = []">取消选择</button>
            </div>
          </div>
        </div>

        <!-- Cluster Results Summary Cards -->
        <ResultCard title="店群划分结果" :visible="!!result">
          <template v-if="result">
            <ClusterResultList
              :clusters="result.clusters"
              :stores="points"
              :highlighted-cluster-id="highlightedClusterId"
              :get-cluster-color="clusterColor"
              @toggle-highlight="toggleHighlightCluster"
            />
          </template>
        </ResultCard>

        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
      </template>

      <template #map>
        <MapStoreSearch :stores="points" @select="handleSelectStore" />
        <MapPanel ref="mapPanel" :center="mapCenter" :zoom="11" />
      </template>
    </ViewLayout>

    <!-- Save Plan Modal Dialog -->
    <el-dialog v-model="saveDialogVisible" title="保存店群规划方案" width="480px" destroy-on-close :append-to-body="true">
      <el-form label-width="90px">
        <el-form-item label="方案名称">
          <el-input v-model="planTitle" placeholder="例如: 南宁核心区周三店群调整方案" />
        </el-form-item>
        <el-form-item label="规划摘要">
          <div style="font-size: 13px; color: #64748b; line-height: 1.6;">
            包含 <strong>{{ points.length }}</strong> 家门店，划分 <strong>{{ result?.clusters?.length || k }}</strong> 个店群，中心仓：{{ depotName }}
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="saveDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSavePlan">确认保存</el-button>
      </template>
    </el-dialog>

    <!-- Load History Plan Modal Dialog -->
    <el-dialog v-model="historyDialogVisible" title="载入历史店群规划方案" width="760px" destroy-on-close :append-to-body="true">
      <div style="display: flex; justify-content: flex-end; margin-bottom: 12px;">
        <el-radio-group v-model="historySaveType" size="small" @change="fetchHistory">
          <el-radio-button label="">全部记录</el-radio-button>
          <el-radio-button label="MANUAL">💾 手动保存</el-radio-button>
          <el-radio-button label="AUTO">⚡ 自动运行</el-radio-button>
        </el-radio-group>
      </div>

      <el-table :data="historyList" v-loading="loadingHistory" border stripe max-height="380px">
        <el-table-column prop="task_id" label="方案编号 / 标题" min-width="220">
          <template #default="{ row }">
            <div style="font-weight: 600; color: #0f172a;">{{ getPlanTitle(row) }}</div>
            <div style="font-size: 11px; color: #94a3b8; font-family: monospace;">{{ row.task_id }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="save_type" label="记录来源" width="115" align="center">
          <template #default="{ row }">
            <el-tag :type="row.save_type === 'MANUAL' ? 'success' : 'info'" size="small" effect="light" style="font-weight: 600;">
              {{ row.save_type === 'MANUAL' ? '💾 手动保存' : '⚡ 自动运行' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="记录时间" width="160">
          <template #default="{ row }">
            {{ row.created_at ? new Date(row.created_at).toLocaleString() : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="loadHistoryPlan(row)">载入此方案</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import ViewLayout from '../components/ViewLayout.vue'
import ResultCard from '../components/ResultCard.vue'
import MapPanel from '../components/MapPanel.vue'
import MapStoreSearch from '../components/MapStoreSearch.vue'
import ClusterResultList from '../components/planning/ClusterResultList.vue'
import { clusteringApi, routingApi } from '../api/client.js'
import { getDistanceBetweenCoords } from '../utils/constants.js'
import { dotHtml, CLUSTER_COLORS, escapeHtml } from '../utils/mapMarkers.js'
import { parseFileUniversal } from '../utils/excelImport.js'
import { ElMessage } from 'element-plus'

const route = useRoute()

const mapCenter = [108.33, 22.80]
const mapPanel = ref(null)
const amap = ref(null)

const points = ref([])
const dataSourceLabel = ref('')
const k = ref(9)
const algorithm = ref('kmeans')
const minZoneSize = ref(30)
const maxZoneSize = ref(40)

// Dedicated depot coordinates
const depotName = ref('南宁中心仓')
const depotLng = ref(108.318344)
const depotLat = ref(22.846367)
const depotList = ref([])
const selectedDepotKey = ref('')

const highlightedClusterId = ref(null)
const result = ref(null)
const loading = ref(false)
const errorMsg = ref('')

const isSelecting = ref(false)
let mouseTool = null
const selectedPointIndices = ref([])
const batchTargetCluster = ref('')
const batchAttrKey = ref('')
const batchAttrVal = ref('')

// Save & History Modal States
const saveDialogVisible = ref(false)
const planTitle = ref('')
const saving = ref(false)

const historyDialogVisible = ref(false)
const historySaveType = ref('')
const historyList = ref([])
const loadingHistory = ref(false)

// Excel Import Handler
const excelFileInput = ref(null)

const triggerExcelImport = () => {
  if (excelFileInput.value) {
    excelFileInput.value.value = ''
    excelFileInput.value.click()
  }
}

const handleExcelImport = async (e) => {
  const file = e.target.files?.[0]
  if (!file) return

  try {
    const { points: parsedPoints, warnings } = await parseFileUniversal(file)
    if (!parsedPoints || !parsedPoints.length) {
      ElMessage.error('未能成功解析有效门店数据，请检查文件格式与经纬度字段')
      return
    }

    if (warnings && warnings.length) {
      ElMessage.warning(`解析提示: ${warnings[0]}`)
    }

    // Map into clustering format
    points.value = parsedPoints.map((p, idx) => ({
      name: p.name || `门店${idx + 1}`,
      shop_code: p.shop_code || '',
      dept_id: p.dept_id || '',
      district: p.district || '',
      warzone: p.warzone || '',
      lng: Number(p.lng),
      lat: Number(p.lat),
      avg_loads: Number(p.avg_loads || p.weight || 10),
      frequency: Number(p.frequency || 1),
      is_homepot: p.is_homepot !== undefined ? Number(p.is_homepot) : 0,
      service_time: p.service_time || 0.65,
      available_truck: p.available_truck || '',
      address: p.address || '',
      cluster_id: p.cluster_id,
      center_lng: p.center_lng,
      center_lat: p.center_lat,
      cdist_warehouse: p.cdist_warehouse,
      sdist_warehouse: p.sdist_warehouse
    }))

    dataSourceLabel.value = `Excel 导入「${file.name}」`

    // Check if the imported Excel already contains cluster_id/店群 assignments
    const pointsWithCluster = points.value.filter(p => p.cluster_id !== undefined && p.cluster_id !== null && p.cluster_id !== '')
    if (pointsWithCluster.length > 0 && pointsWithCluster.length >= points.value.length * 0.4) {
      // Group by cluster_id directly and display result
      const clusterMap = new Map()
      points.value.forEach((p, idx) => {
        const cId = p.cluster_id !== undefined && p.cluster_id !== null && p.cluster_id !== '' ? Number(p.cluster_id) : 0
        if (!clusterMap.has(cId)) clusterMap.set(cId, [])
        clusterMap.get(cId).push(idx)
      })

      const clusters = []
      const assignments = new Array(points.value.length).fill(0)
      let newCId = 0

      // Sort clusters
      const sortedKeys = Array.from(clusterMap.keys()).sort((a, b) => Number(a) - Number(b))
      sortedKeys.forEach(origCId => {
        const idxs = clusterMap.get(origCId)
        idxs.forEach(idx => {
          assignments[idx] = newCId
          points.value[idx].cluster_id = newCId
        })
        const sumLng = idxs.reduce((sum, idx) => sum + points.value[idx].lng, 0)
        const sumLat = idxs.reduce((sum, idx) => sum + points.value[idx].lat, 0)
        const center = {
          lng: round(sumLng / idxs.length),
          lat: round(sumLat / idxs.length)
        }
        const cdist = (depotLng.value && depotLat.value) ? getDistanceBetweenCoords(center, { lng: depotLng.value, lat: depotLat.value }) : 0
        idxs.forEach(idx => {
          points.value[idx].cdist_warehouse = round(cdist)
          points.value[idx].center_lng = round(center.lng)
          points.value[idx].center_lat = round(center.lat)
        })

        clusters.push({
          cluster_id: newCId,
          center,
          size: idxs.length,
          point_indices: idxs,
          cdist_warehouse: round(cdist)
        })
        newCId++
      })

      result.value = {
        algorithm: 'Excel导入店群',
        clusters,
        assignments,
        k: clusters.length
      }
      k.value = clusters.length
      ElMessage.success(`成功导入 ${points.value.length} 家门店，已直接展示 ${clusters.length} 个店群分组结果！`)
    } else {
      // Raw store list imported without pre-grouped clusters
      result.value = null
      ElMessage.success(`成功导入 ${points.value.length} 家门店，已在地图上标注展示！`)
    }

    renderClusters()
    setTimeout(() => {
      mapPanel.value?.fitView()
    }, 200)
    saveToLocalStorage()
  } catch (err) {
    ElMessage.error('Excel导入失败: ' + err.message)
  }
}

const round = (n) => Math.round(n * 1e5) / 1e5
const clusterColor = (cid) => CLUSTER_COLORS[cid % CLUSTER_COLORS.length]

const totalAvgLoads = computed(() => {
  return Math.round(points.value.reduce((sum, p) => sum + (Number(p.avg_loads || p.weight) || 0), 0))
})



function getClusterTotalLoad(cid) {
  if (!result.value) return 0
  const memberPoints = points.value.filter((_, idx) => result.value.assignments[idx] === cid)
  return Math.round(memberPoints.reduce((sum, p) => sum + (Number(p.avg_loads || p.weight) || 0), 0))
}

function saveToLocalStorage() {
  try {
    localStorage.setItem('clustering_points', JSON.stringify(points.value))
    localStorage.setItem('clustering_savedAt', new Date().toISOString())
    localStorage.setItem('clustering_result', result.value ? JSON.stringify(result.value) : '')
    localStorage.setItem('clustering_algorithm', algorithm.value)
    localStorage.setItem('clustering_k', String(k.value))
    localStorage.setItem('clustering_minZoneSize', String(minZoneSize.value))
    localStorage.setItem('clustering_maxZoneSize', String(maxZoneSize.value))
    localStorage.setItem('clustering_depotName', depotName.value)
    localStorage.setItem('clustering_depotLng', String(depotLng.value))
    localStorage.setItem('clustering_depotLat', String(depotLat.value))
  } catch (e) {
    console.warn('[LocalStorage] 存储店群数据超出配额，安全降级:', e)
  }
}

function onAlgChange() {
  result.value = null
  saveToLocalStorage()
}

const fetchDepots = async () => {
  try {
    const res = await fetch('/api/depot/')
    if (res.ok) {
      depotList.value = await res.json()
      const matched = depotList.value.find(
        (d) => d.name === depotName.value || d.dc_code === depotName.value || (Math.abs(d.longitude - Number(depotLng.value)) < 0.001 && Math.abs(d.latitude - Number(depotLat.value)) < 0.001)
      )
      if (matched) {
        selectedDepotKey.value = matched.dc_code || matched.name
        depotName.value = matched.name
        depotLng.value = Number(matched.longitude)
        depotLat.value = Number(matched.latitude)
      } else if (depotLng.value && depotLat.value) {
        selectedDepotKey.value = 'custom'
      } else if (depotList.value.length) {
        const def = depotList.value.find((d) => d.is_default) || depotList.value[0]
        selectedDepotKey.value = def.dc_code || def.name
        depotName.value = def.name
        depotLng.value = Number(def.longitude)
        depotLat.value = Number(def.latitude)
      }
    }
  } catch (err) {
    console.error('获取中心仓列表失败:', err)
  }
}

const onDepotSelectChange = () => {
  if (selectedDepotKey.value === 'custom') {
    return
  }
  const matched = depotList.value.find(
    (d) => (d.dc_code && d.dc_code === selectedDepotKey.value) || (d.name && d.name === selectedDepotKey.value)
  )
  if (matched) {
    depotName.value = matched.name
    depotLng.value = Number(matched.longitude)
    depotLat.value = Number(matched.latitude)
    ElMessage.success(`已切换中心仓为: ${matched.name} [${depotLng.value}, ${depotLat.value}]`)
    onDepotChange()
  }
}

const onDepotCustomChange = () => {
  onDepotChange()
}

function onDepotChange() {
  renderClusters()
  saveToLocalStorage()
}

function clearAll() {
  if (points.value.length > 0) {
    const confirmClear = confirm('是否确认清空当前所有的门店数据与聚类划分？')
    if (!confirmClear) return
  }
  points.value = []
  result.value = null
  selectedPointIndices.value = []
  errorMsg.value = ''
  dataSourceLabel.value = ''
  mapPanel.value?.clearAll()
  saveToLocalStorage()
}

function toggleHighlightCluster(cid) {
  if (highlightedClusterId.value === cid) {
    highlightedClusterId.value = null
  } else {
    highlightedClusterId.value = cid
  }
  renderClusters()
}

// -------------------------------------------------------------
// In-Map Marker Popover & Attribute Editing
// -------------------------------------------------------------
window.updateStoreAttribute = function(idx, key, val) {
  if (points.value[idx]) {
    if (['frequency', 'avg_loads', 'is_homepot', 'service_time'].includes(key)) {
      const num = Number(val)
      points.value[idx][key] = isNaN(num) ? val : num
    } else {
      points.value[idx][key] = val
    }
    ElMessage.success(`门店 [${points.value[idx].name || idx + 1}] 属性已更新`)
    renderClusters()
    saveToLocalStorage()
  }
}

window.moveStorePoint = function(pointIdx, targetVal) {
  if (!result.value) return
  let targetClusterId
  const affectedClusters = new Set([result.value.assignments[pointIdx]])

  if (targetVal === 'new') {
    targetClusterId = result.value.clusters.length
    result.value.clusters.push({
      cluster_id: targetClusterId,
      center: { lng: Number(points.value[pointIdx].lng), lat: Number(points.value[pointIdx].lat) },
      size: 0,
      point_indices: [],
      cdist_warehouse: 0
    })
  } else {
    targetClusterId = Number(targetVal)
  }
  affectedClusters.add(targetClusterId)

  result.value.assignments[pointIdx] = targetClusterId
  points.value[pointIdx].cluster_id = targetClusterId

  // Recalculate cluster centers & stats
  result.value.clusters.forEach(c => {
    if (!affectedClusters.has(c.cluster_id)) return
    const idxs = result.value.assignments
      .map((val, idx) => val === c.cluster_id ? idx : -1)
      .filter(idx => idx !== -1)
    
    c.size = idxs.length
    c.point_indices = idxs
    if (idxs.length > 0) {
      const sumLng = idxs.reduce((sum, idx) => sum + Number(points.value[idx].lng), 0)
      const sumLat = idxs.reduce((sum, idx) => sum + Number(points.value[idx].lat), 0)
      c.center = {
        lng: round(sumLng / idxs.length),
        lat: round(sumLat / idxs.length)
      }
      c.cdist_warehouse = getDistanceBetweenCoords(c.center, { lng: depotLng.value, lat: depotLat.value })
      idxs.forEach(idx => {
        points.value[idx].cdist_warehouse = round(c.cdist_warehouse)
        points.value[idx].center_lng = round(c.center.lng)
        points.value[idx].center_lat = round(c.center.lat)
      })
    }
  })

  ElMessage.success(`已将门店移动至店群 ${targetClusterId + 1}`)
  renderClusters()
  saveToLocalStorage()
}

window.removeStorePoint = function(idx) {
  const storeName = points.value[idx]?.name || `点${idx + 1}`
  points.value.splice(idx, 1)
  if (result.value) {
    result.value.assignments.splice(idx, 1)
    // Update cluster members
    result.value.clusters.forEach(c => {
      const idxs = result.value.assignments
        .map((val, i) => val === c.cluster_id ? i : -1)
        .filter(i => i !== -1)
      c.size = idxs.length
      c.point_indices = idxs
    })
  }
  ElMessage.info(`已移除门店 ${storeName}`)
  renderClusters()
  saveToLocalStorage()
}

// 门店搜索选中后联动: 飞到标记并打开弹窗 (无标记引用时退化为仅定位)
let storeMarkers = []
let storeInfoWindows = []

const handleSelectStore = (item) => {
  if (!item || item.index === undefined) return
  const mapObj = mapPanel.value?.getMap()
  const marker = storeMarkers[item.index]
  const infoWindow = storeInfoWindows[item.index]
  if (mapObj && marker && infoWindow) {
    mapObj.setZoomAndCenter(15, marker.getPosition())
    infoWindow.open(mapObj, marker.getPosition())
  } else if (mapObj && item.lng && item.lat) {
    mapObj.setZoomAndCenter(15, [Number(item.lng), Number(item.lat)])
  }
}

function addMarkerWithBubble(A, p, idx, markerOptions) {
  const marker = new A.Marker(markerOptions)
  
  const currentCluster = result.value ? result.value.assignments[idx] : null
  let clusterSelectHtml = ''
  if (result.value && currentCluster !== null) {
    clusterSelectHtml = `<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
      <span style="font-size: 11px; font-weight: 600; color: #475569;">所属店群:</span>
      <select onchange="window.moveStorePoint(${idx}, this.value)" style="font-size: 11px; padding: 2px 4px; border-radius: 4px; border: 1px solid #0284c7; background: #f0f9ff; font-weight: 600; color: #0369a1;">`
    result.value.clusters.forEach(c => {
      const selected = c.cluster_id === currentCluster ? 'selected' : ''
      clusterSelectHtml += `<option value="${c.cluster_id}" ${selected}>店群 ${c.cluster_id + 1} (${c.size}家)</option>`
    })
    clusterSelectHtml += `<option value="new">+ 新建并加入新店群</option>`
    clusterSelectHtml += `</select></div>`
  }

  const safeName = escapeHtml(p.name || '未命名门店')
  const infoContent = `
    <div style="padding: 12px; font-size: 12px; line-height: 1.5; color: #1e293b; min-width: 230px; max-width: 290px; background: #fff; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
      <div style="font-weight: 700; font-size: 14px; margin-bottom: 8px; color: #0f172a; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; display: flex; justify-content: space-between;">
        <span>${safeName}</span>
        <span style="font-size: 11px; color: #94a3b8;">#${idx + 1}</span>
      </div>

      ${clusterSelectHtml}

      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 5px;">
        <span style="font-size: 11px; color: #64748b;">日均箱数(avg_loads):</span>
        <input type="number" value="${p.avg_loads || p.weight || 10}" onchange="window.updateStoreAttribute(${idx}, 'avg_loads', this.value)" style="font-size: 11px; width: 70px; padding: 2px 4px; border: 1px solid #cbd5e1; border-radius: 4px; text-align: right;" />
      </div>

      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 5px;">
        <span style="font-size: 11px; color: #64748b;">周配送频次(frequency):</span>
        <select onchange="window.updateStoreAttribute(${idx}, 'frequency', this.value)" style="font-size: 11px; padding: 2px 4px; border: 1px solid #cbd5e1; border-radius: 4px;">
          ${[1,2,3,4,5,6,7].map(f => `<option value="${f}" ${p.frequency == f ? 'selected' : ''}>每周 ${f} 次</option>`).join('')}
        </select>
      </div>

      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 5px;">
        <span style="font-size: 11px; color: #64748b;">属性(is_homepot):</span>
        <select onchange="window.updateStoreAttribute(${idx}, 'is_homepot', this.value)" style="font-size: 11px; padding: 2px 4px; border: 1px solid #cbd5e1; border-radius: 4px;">
          <option value="1" ${p.is_homepot == 1 ? 'selected' : ''}>本埠门店</option>
          <option value="0" ${p.is_homepot == 0 ? 'selected' : ''}>外埠门店</option>
        </select>
      </div>

      <div style="margin-top: 8px; padding-top: 6px; border-top: 1px solid #f1f5f9;">
        <button onclick="window.removeStorePoint(${idx})" style="width: 100%; padding: 4px 0; background: #fee2e2; color: #dc2626; border: 1px solid #fecaca; border-radius: 4px; font-size: 11px; cursor: pointer; font-weight: 500;">
          移除该门店点
        </button>
      </div>
    </div>
  `

  const infoWindow = new A.InfoWindow({
    content: infoContent,
    offset: new A.Pixel(0, -18),
    closeWhenClickMap: true
  })

  marker.on('click', () => {
    const mapObj = mapPanel.value?.getMap()
    if (mapObj) {
      infoWindow.open(mapObj, marker.getPosition())
    }
  })

  storeMarkers[idx] = marker
  storeInfoWindows[idx] = infoWindow

  mapPanel.value.addOverlay(marker)
}

function renderClusters() {
  if (!amap.value || !mapPanel.value) return
  const A = amap.value
  mapPanel.value.clearAll()
  storeMarkers = []
  storeInfoWindows = []

  // Always draw warehouse depot
  if (depotLng.value && depotLat.value) {
    const { content, offset } = dotHtml({ text: '仓', color: '#475569', size: 28 })
    mapPanel.value.addOverlay(
      new A.Marker({
        position: [Number(depotLng.value), Number(depotLat.value)],
        content,
        offset: new A.Pixel(offset[0], offset[1]),
        zIndex: 150
      })
    )
  }

  const isPointSelected = (idx) => selectedPointIndices.value.includes(idx)

  if (result.value) {
    const assignments = result.value.assignments
    const hcId = highlightedClusterId.value

    points.value.forEach((p, i) => {
      if (p.lng === '' || p.lat === '') return
      const cid = assignments[i]
      
      let color = clusterColor(cid)
      let size = isPointSelected(i) ? 26 : 22
      let opacity = 1.0
      
      if (hcId !== null) {
        if (cid === hcId) {
          size = 26
        } else {
          opacity = 0.15
        }
      } else if (isPointSelected(i)) {
        color = '#0d9488'
      }

      const { content, offset } = dotHtml({
        text: String(i + 1),
        color,
        size,
      })
      
      let finalContent = content
      if (opacity < 1.0) {
        finalContent = `<div style="opacity: ${opacity}; transition: opacity 0.25s;">${content}</div>`
      } else if (hcId !== null && cid === hcId) {
        finalContent = `<div style="box-shadow: 0 0 12px ${color}; border-radius: 50%; outline: 3px solid ${color}; outline-offset: 2px;">${content}</div>`
      }
      
      addMarkerWithBubble(A, p, i, {
        position: [Number(p.lng), Number(p.lat)],
        content: finalContent,
        offset: new A.Pixel(offset[0], offset[1]),
      })
    })

    // Draw cluster centers
    result.value.clusters.forEach((c) => {
      const color = clusterColor(c.cluster_id)
      const { content, offset } = dotHtml({
        text: `C${c.cluster_id + 1}`,
        color,
        size: 32,
      })
      
      const centerMarker = new A.Marker({
        position: [c.center.lng, c.center.lat],
        content,
        offset: new A.Pixel(offset[0], offset[1]),
        zIndex: 200,
      })

      const centerContent = `
        <div style="padding: 10px 14px; font-size: 13px; line-height: 1.6; color: #1e293b; min-width: 170px;">
          <strong style="font-size: 14px; color: ${color};">店群 ${c.cluster_id + 1} 概览</strong><br>
          <hr style="margin: 6px 0; border: none; border-top: 1px solid #e2e8f0;">
          <strong>门店总数:</strong> ${c.size} 家<br>
          <strong>日均总装载:</strong> ${getClusterTotalLoad(c.cluster_id)} 箱<br>
          <strong>距仓库:</strong> ${c.cdist_warehouse ? c.cdist_warehouse.toFixed(2) : '-'} km
        </div>
      `

      const centerInfoWindow = new A.InfoWindow({
        content: centerContent,
        offset: new A.Pixel(0, -22),
        closeWhenClickMap: true
      })

      centerMarker.on('click', () => {
        toggleHighlightCluster(c.cluster_id)
        const mapObj = mapPanel.value?.getMap()
        if (mapObj) {
          centerInfoWindow.open(mapObj, centerMarker.getPosition())
        }
      })

      mapPanel.value.addOverlay(centerMarker)
    })
  } else {
    // Render unclustered points
    points.value.forEach((p, i) => {
      if (p.lng === '' || p.lat === '') return
      const { content, offset } = dotHtml({ 
        text: String(i + 1), 
        color: isPointSelected(i) ? '#0d9488' : '#94a3b8', 
        size: isPointSelected(i) ? 24 : 20 
      })
      
      addMarkerWithBubble(A, p, i, {
        position: [Number(p.lng), Number(p.lat)],
        content,
        offset: new A.Pixel(offset[0], offset[1]),
      })
    })
  }
}

async function solve() {
  errorMsg.value = ''
  if (points.value.length < 2) {
    errorMsg.value = '请至少添加 2 个门店点'
    return
  }
  
  if (algorithm.value === 'kmeans' && (!k.value || k.value < 1)) {
    errorMsg.value = 'K 必须为正整数'
    return
  }
  loading.value = true
  try {
    const formattedPoints = points.value.map((p) => {
      const pt = { name: p.name, lng: Number(p.lng), lat: Number(p.lat) }
      Object.entries(p).forEach(([key, val]) => {
        if (!['name', 'lng', 'lat'].includes(key)) {
          pt[key] = val
        }
      })
      return pt
    })

    const payload = {
      points: formattedPoints,
      k: Number(k.value || 1),
      algorithm: algorithm.value,
      depot_lng: Number(depotLng.value),
      depot_lat: Number(depotLat.value),
      options: {
        min_zone_size: Number(minZoneSize.value),
        max_zone_size: Number(maxZoneSize.value),
      }
    }
    const resp = await clusteringApi.solve(payload)
    result.value = resp
    if (resp.points) {
      points.value = resp.points.map(p => {
        const cid = p.cluster_id
        const c = resp.clusters.find(cl => cl.cluster_id === cid)
        return {
          ...p,
          center_lng: c ? round(c.center.lng) : '',
          center_lat: c ? round(c.center.lat) : ''
        }
      })
    }
    renderClusters()
    mapPanel.value?.fitView()
    saveToLocalStorage()
    ElMessage.success(`聚类计算完成，共划分 ${resp.clusters?.length || k.value} 个店群`)
  } catch (e) {
    errorMsg.value = '店群规划失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}

// -------------------------------------------------------------
// Save & Load Plan Implementations
// -------------------------------------------------------------
const openSaveModal = () => {
  planTitle.value = `店群规划方案_${new Date().toLocaleDateString()}`
  saveDialogVisible.value = true
}

const handleSavePlan = async () => {
  if (!points.value.length) return
  saving.value = true
  try {
    const payload = {
      title: planTitle.value,
      algorithm: algorithm.value,
      depot_name: depotName.value,
      depot_lng: Number(depotLng.value),
      depot_lat: Number(depotLat.value),
      points: points.value,
      clusters: result.value?.clusters || [],
      assignments: result.value?.assignments || [],
      k: Number(k.value)
    }

    const res = await fetch('/api/clustering/save_plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) throw new Error('保存方案失败')
    const data = await res.json()
    ElMessage.success(data.message || '方案已成功保存至历史记录！')
    saveDialogVisible.value = false
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    saving.value = false
  }
}

const openHistoryModal = async () => {
  historyDialogVisible.value = true
  fetchHistory()
}

const fetchHistory = async () => {
  loadingHistory.value = true
  try {
    const params = new URLSearchParams()
    params.append('task_type', 'CLUSTERING')
    if (historySaveType.value) params.append('save_type', historySaveType.value)
    const res = await fetch(`/api/history/?${params.toString()}`)
    if (!res.ok) throw new Error('获取历史方案失败')
    const data = await res.json()
    historyList.value = data
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    loadingHistory.value = false
  }
}

const getPlanTitle = (row) => {
  try {
    if (row.parameters) {
      const p = typeof row.parameters === 'string' ? JSON.parse(row.parameters) : row.parameters
      if (p.title) return p.title
      if (p.algorithm) {
        const count = p.points_count || (Array.isArray(p.points) ? p.points.length : '')
        return `店群聚类方案 (${p.algorithm}${count ? `, ${count}家门店` : ''})`
      }
    }
  } catch (e) {}
  return `店群聚类方案 (${row.task_id.substring(0, 8)})`
}

const loadHistoryPlan = (row) => {
  try {
    if (!row.result && !row.parameters) {
      ElMessage.warning('该历史记录中无有效数据')
      return
    }
    const resData = row.result ? (typeof row.result === 'string' ? JSON.parse(row.result) : row.result) : {}
    const paramData = row.parameters ? (typeof row.parameters === 'string' ? JSON.parse(row.parameters) : row.parameters) : {}
    
    // Points list can come from resData.points or paramData.points
    const pointsList = (resData.points && resData.points.length) ? resData.points : (paramData.points || [])
    if (Array.isArray(pointsList) && pointsList.length) {
      points.value = pointsList.map((p, idx) => ({
        name: p.name || `门店${idx + 1}`,
        shop_code: p.shop_code || '',
        lng: Number(p.lng !== undefined ? p.lng : p.longitude),
        lat: Number(p.lat !== undefined ? p.lat : p.latitude),
        avg_loads: Number(p.avg_loads || p.weight || 10),
        frequency: Number(p.frequency || 1),
        is_homepot: p.is_homepot !== undefined ? Number(p.is_homepot) : 0,
        district: p.district || '',
        warzone: p.warzone || '',
        service_time: p.service_time || 0.65,
        available_truck: p.available_truck || '',
        address: p.address || '',
        cluster_id: p.cluster_id !== undefined ? p.cluster_id : (resData.assignments ? resData.assignments[idx] : undefined),
        center_lng: p.center_lng,
        center_lat: p.center_lat,
        cdist_warehouse: p.cdist_warehouse,
        sdist_warehouse: p.sdist_warehouse
      }))
    }

    if (resData.depot_name || paramData.depot_name) depotName.value = resData.depot_name || paramData.depot_name
    if (resData.depot_lng || paramData.depot_lng) depotLng.value = Number(resData.depot_lng || paramData.depot_lng)
    if (resData.depot_lat || paramData.depot_lat) depotLat.value = Number(resData.depot_lat || paramData.depot_lat)
    if (resData.algorithm || paramData.algorithm) algorithm.value = resData.algorithm || paramData.algorithm
    if (resData.k || paramData.k) k.value = Number(resData.k || paramData.k)

    if (resData.clusters && resData.assignments) {
      result.value = {
        algorithm: resData.algorithm || algorithm.value,
        clusters: resData.clusters,
        assignments: resData.assignments,
        k: resData.k || resData.clusters.length
      }
    } else {
      result.value = null
    }

    renderClusters()
    if (points.value.length) {
      mapPanel.value?.fitView()
    }
    dataSourceLabel.value = `历史方案「${getPlanTitle(row)}」`
    saveToLocalStorage()
    historyDialogVisible.value = false
    ElMessage.success(`已成功载入历史规划方案（包含 ${points.value.length} 家门店）！`)
  } catch (err) {
    ElMessage.error('载入方案失败: ' + err.message)
  }
}

// -------------------------------------------------------------
// Box Selection Tools
// -------------------------------------------------------------
function toggleBoxSelect() {
  if (!mapPanel.value) return
  const map = mapPanel.value.getMap()
  const A = amap.value
  if (!map || !A) return

  if (isSelecting.value) {
    if (mouseTool) mouseTool.close(true)
    isSelecting.value = false
    return
  }

  isSelecting.value = true
  A.plugin(['AMap.MouseTool'], () => {
    if (!mouseTool) {
      mouseTool = new A.MouseTool(map)
    }
    mouseTool.rectangle({
      strokeColor: '#0d9488',
      strokeOpacity: 0.8,
      strokeWeight: 2,
      fillColor: '#14b8a6',
      fillOpacity: 0.25
    })
    mouseTool.on('draw', (e) => {
      const bounds = e.obj.getBounds()
      const selected = []
      points.value.forEach((p, idx) => {
        if (p.lng === '' || p.lat === '') return
        const pos = new A.LngLat(Number(p.lng), Number(p.lat))
        if (bounds.contains(pos)) {
          selected.push(idx)
        }
      })
      selectedPointIndices.value = selected
      mouseTool.close(true)
      isSelecting.value = false
      renderClusters()
      ElMessage.info(`框选了 ${selected.length} 家门店`)
    })
  })
}

function applyBatchMove() {
  if (!result.value || batchTargetCluster.value === '') return
  const targetVal = batchTargetCluster.value
  let targetClusterId
  const affectedClusters = new Set()

  selectedPointIndices.value.forEach(idx => {
    affectedClusters.add(result.value.assignments[idx])
  })

  if (targetVal === 'new') {
    targetClusterId = result.value.clusters.length
    const firstIdx = selectedPointIndices.value[0]
    result.value.clusters.push({
      cluster_id: targetClusterId,
      center: { lng: Number(points.value[firstIdx].lng), lat: Number(points.value[firstIdx].lat) },
      size: 0,
      point_indices: [],
      cdist_warehouse: 0
    })
  } else {
    targetClusterId = Number(targetVal)
  }
  affectedClusters.add(targetClusterId)
  
  selectedPointIndices.value.forEach(idx => {
    result.value.assignments[idx] = targetClusterId
    points.value[idx].cluster_id = targetClusterId
  })
  
  // Recalculate
  result.value.clusters.forEach(c => {
    if (!affectedClusters.has(c.cluster_id)) return
    const idxs = result.value.assignments
      .map((val, idx) => val === c.cluster_id ? idx : -1)
      .filter(idx => idx !== -1)
    
    c.size = idxs.length
    c.point_indices = idxs
    if (idxs.length > 0) {
      const sumLng = idxs.reduce((sum, idx) => sum + Number(points.value[idx].lng), 0)
      const sumLat = idxs.reduce((sum, idx) => sum + Number(points.value[idx].lat), 0)
      c.center = {
        lng: round(sumLng / idxs.length),
        lat: round(sumLat / idxs.length)
      }
      c.cdist_warehouse = getDistanceBetweenCoords(c.center, { lng: depotLng.value, lat: depotLat.value })
      idxs.forEach(idx => {
        points.value[idx].cdist_warehouse = round(c.cdist_warehouse)
        points.value[idx].center_lng = round(c.center.lng)
        points.value[idx].center_lat = round(c.center.lat)
      })
    }
  })
  
  selectedPointIndices.value = []
  batchTargetCluster.value = ''
  renderClusters()
  saveToLocalStorage()
  ElMessage.success('批量换区完成')
}

function applyBatchAttrEdit() {
  if (!batchAttrKey.value) return
  const key = batchAttrKey.value.trim()
  const rawVal = batchAttrVal.value
  
  selectedPointIndices.value.forEach(idx => {
    if (points.value[idx]) {
      if (['frequency', 'avg_loads', 'is_homepot'].includes(key)) {
        const num = Number(rawVal)
        points.value[idx][key] = isNaN(num) ? rawVal : num
      } else {
        points.value[idx][key] = rawVal
      }
    }
  })
  
  selectedPointIndices.value = []
  batchAttrKey.value = ''
  batchAttrVal.value = ''
  renderClusters()
  saveToLocalStorage()
  ElMessage.success('批量属性修改完成')
}

function batchDelete() {
  if (!selectedPointIndices.value.length) return
  const toDelete = new Set(selectedPointIndices.value)
  points.value = points.value.filter((_, idx) => !toDelete.has(idx))
  
  if (result.value) {
    result.value.assignments = result.value.assignments.filter((_, idx) => !toDelete.has(idx))
    result.value.clusters.forEach(c => {
      const idxs = result.value.assignments
        .map((val, idx) => val === c.cluster_id ? idx : -1)
        .filter(idx => idx !== -1)
      c.size = idxs.length
      c.point_indices = idxs
    })
  }
  selectedPointIndices.value = []
  renderClusters()
  saveToLocalStorage()
  ElMessage.success('已批量删除所选门店')
}

async function loadPlanningData() {
  // Restore last-edited points from localStorage
  let loadedPoints = null
  const savedPoints = localStorage.getItem('clustering_points')
  if (savedPoints) {
    try {
      const parsed = JSON.parse(savedPoints)
      if (Array.isArray(parsed) && parsed.length) {
        loadedPoints = parsed
      }
    } catch (e) {}
  }

  if (loadedPoints && loadedPoints.length) {
    points.value = loadedPoints
    const savedAt = localStorage.getItem('clustering_savedAt')
    const dateStr = savedAt ? new Date(savedAt).toLocaleDateString() : ''
    dataSourceLabel.value = dateStr ? `上次编辑（${dateStr}）` : '上次编辑'
    ElMessage.info(`已恢复上次编辑的 ${loadedPoints.length} 家门店${dateStr ? `（${dateStr}）` : ''}`)
  }

  const savedDepotName = localStorage.getItem('clustering_depotName')
  const savedDepotLng = localStorage.getItem('clustering_depotLng')
  const savedDepotLat = localStorage.getItem('clustering_depotLat')
  const savedAlgorithm = localStorage.getItem('clustering_algorithm')
  const savedK = localStorage.getItem('clustering_k')
  const savedMinZoneSize = localStorage.getItem('clustering_minZoneSize')
  const savedMaxZoneSize = localStorage.getItem('clustering_maxZoneSize')
  const savedResult = localStorage.getItem('clustering_result')

  if (savedDepotName) depotName.value = savedDepotName
  if (savedDepotLng) depotLng.value = Number(savedDepotLng)
  if (savedDepotLat) depotLat.value = Number(savedDepotLat)

  await fetchDepots()
  if (savedAlgorithm) algorithm.value = savedAlgorithm
  if (savedK) k.value = Number(savedK)
  if (savedMinZoneSize) minZoneSize.value = Number(savedMinZoneSize)
  if (savedMaxZoneSize) maxZoneSize.value = Number(savedMaxZoneSize)

  if (savedResult && savedResult !== '') {
    try {
      result.value = JSON.parse(savedResult)
    } catch (e) {
      result.value = null
    }
  } else {
    result.value = null
  }

  try {
    if (!amap.value && mapPanel.value) {
      amap.value = await (mapPanel.value.whenReady ? mapPanel.value.whenReady() : mapPanel.value.getAmap())
    }
  } catch (e) {
    console.error('Failed to get AMap instance', e)
  }

  setTimeout(() => {
    renderClusters()
    if (points.value.length) {
      mapPanel.value?.fitView()
    }
  }, 300)
}

onMounted(async () => {
  await loadPlanningData()
})

watch(
  () => [route.path, route.query.t],
  ([newPath]) => {
    if (newPath === '/clustering/plan') {
      loadPlanningData()
    }
  }
)

onBeforeUnmount(() => {
  delete window.removeStorePoint
  delete window.moveStorePoint
  delete window.updateStoreAttribute
  if (mouseTool) {
    mouseTool.close(true)
  }
})
</script>

<style scoped>
.clustering-view-wrapper {
  height: 100%;
  width: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  margin-bottom: 12px;
}

.desc {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.6;
  margin: 4px 0 0 0;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
}

.cluster-summary-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 320px;
  overflow-y: auto;
}

.cluster-card-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 8px 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.cluster-card-item:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.cluster-card-item.is-highlighted {
  border-color: #0284c7;
  background: #e0f2fe;
  box-shadow: 0 0 0 1px #0284c7;
}

.cluster-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.cluster-size-tag {
  font-size: 11px;
  background: #e2e8f0;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.cluster-card-body {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #64748b;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
</style>
