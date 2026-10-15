<template>
  <div class="clustering-view-wrapper">
    <ViewLayout>
      <template #side>
        <div class="sidebar-header">
          <h2 class="lp-section-title">门店排班</h2>
          <p class="desc">
            在店群分组基础上，执行按周作业日智能排班。支持从历史店群结果一键导入，并在地图上微调各门店的送货作业日。
          </p>
          <div v-if="dataSourceLabel" class="data-source-badge">
            📦 数据来源：{{ dataSourceLabel }}
          </div>
        </div>

        <!-- 1. Empty State Guidance Card -->
        <div v-if="!points.length" class="lp-card empty-guide-card">
          <div class="empty-guide-text" style="margin-bottom: 0;">
            💡 当前画布暂无排班数据，请从下方工具箱点击<strong>「📂 载入历史」</strong>或<strong>「📥 导入Excel」</strong>开始排班。
          </div>
        </div>

        <!-- 2. Day Selection Filter Card -->
        <div v-if="points.length" class="lp-card" style="margin-bottom: 12px;">
          <div class="form-group">
            <label class="form-label">按配送作业日查看</label>
            <select v-model="selectedDay" class="lp-input select-day" @change="renderPoints">
              <option value="全部">全部时间 (全周总览)</option>
              <option value="周一">周一配送门店</option>
              <option value="周二">周二配送门店</option>
              <option value="周三">周三配送门店</option>
              <option value="周四">周四配送门店</option>
              <option value="周五">周五配送门店</option>
              <option value="周六">周六配送门店</option>
              <option value="周日">周日配送门店</option>
            </select>
          </div>
          <div style="margin-top: 8px; font-size: 12px; color: var(--text-muted); display: flex; justify-content: space-between; align-items: center;">
            <span>当前筛选显示: <strong>{{ activePoints.length }}</strong> / {{ points.length }} 家</span>
            <span v-if="selectedDay !== '全部'" style="font-weight: 600; color: #0284c7;">{{ selectedDay }} 货量: {{ activeDayLoad }} 箱</span>
          </div>
        </div>

        <!-- 3. Scheduling Strategy & Algorithm Config Card -->
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
            <label class="form-label">排班求解策略</label>
            <div style="font-size: 12px; font-weight: 600; color: #0284c7; background: #f0fdf4; border: 1px solid #bbf7d0; padding: 6px 10px; border-radius: 4px; display: flex; align-items: center; justify-content: space-between;">
              <span style="color: #166534;">⚡ TruckSchedule 平滑均衡算法</span>
              <span style="font-size: 11px; color: #15803d; font-weight: normal;">周期 {{ scheduleOptions.work_days || 6 }} 天</span>
            </div>
          </div>
        </div>

        <!-- 4. Core Actions Toolbar -->
        <div class="actions-container lp-card">
          <div class="main-solve-row">
            <button class="lp-btn lp-btn--primary main-solve-btn" :disabled="loading || points.length < 2" @click="solveSchedule">
              {{ loading ? '排班计算中…' : '⚡ 一键自动排班' }}
            </button>
            <button
              class="lp-btn lp-btn--ghost gear-btn"
              title="TruckSchedule 算法参数设置"
              @click="openConfigModal"
            >
              ⚙️
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
              @click="toggleSelectTool"
            >
              {{ isSelecting ? '取消框选' : '📐 框选批量设配送日' }}
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
            <button class="footer-sub-btn" @click="downloadScheduleTemplate" title="下载符合算法输出字段规范的标准 Excel 模板">
              📋 下载模板
            </button>
            <button class="footer-sub-btn footer-clear-btn" :disabled="!points.length" @click="clearAll">
              🗑️ 清空画布
            </button>
          </div>
        </div>

        <!-- 5. Batch Operations Card -->
        <div v-if="selectedPointIndices.length" class="lp-card batch-action-card">
          <div class="batch-card-header">
            <span class="batch-card-title">
              <span class="batch-icon">📐</span>
              已框选 <strong>{{ selectedPointIndices.length }}</strong> 家门店
            </span>
            <button class="batch-close-btn" @click="selectedPointIndices = []">×</button>
          </div>
          <div class="batch-card-body">
            <label style="font-size: 11px; font-weight: 600; color: #555;">批量修改计划配送作业日：</label>
            <div style="display: flex; gap: 6px;">
              <select v-model="batchTargetDay" style="font-size: 12px; padding: 6px; flex: 1; border-radius: 4px; border: 1px solid #cbd5e1; background: white;">
                <option value="" disabled>选择配送作业日模式</option>
                <optgroup v-for="g in SCHEDULE_DAY_GROUPS" :key="g.label" :label="g.label">
                  <option v-for="opt in g.options" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </optgroup>
              </select>
              <button class="lp-btn" style="font-size: 11px; padding: 6px 12px;" :disabled="!batchTargetDay" @click="applyBatchDayChange">
                应用
              </button>
            </div>
            <div style="display: flex; gap: 8px; margin-top: 4px;">
              <button class="lp-btn lp-btn--ghost" style="flex: 1; font-size: 11px; padding: 4px 0;" @click="selectedPointIndices = []">取消选择</button>
            </div>
          </div>
        </div>

        <!-- 4. Result Card for Daily Summary -->
        <ResultCard title="周度排班均衡看板" :visible="points.length > 0">
          <ScheduleBalanceCard
            :stores="points"
            :selected-day="selectedDay"
            @select-day="(d) => { selectedDay = d; renderPoints(); }"
          />
        </ResultCard>

        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
      </template>

      <template #map>
        <div style="position: relative; height: 100%; width: 100%;">
          <MapStoreSearch :stores="points" @select="handleSelectStore" />
          <MapPanel ref="mapPanel" :center="mapCenter" :zoom="11" />
        </div>
      </template>
    </ViewLayout>

    <!-- Save Schedule Modal Dialog -->
    <el-dialog v-model="saveDialogVisible" title="保存店群排班方案" width="480px" destroy-on-close :append-to-body="true">
      <el-form label-width="90px">
        <el-form-item label="方案名称">
          <el-input v-model="planTitle" placeholder="例如: 南宁店群排班计划_202608" />
        </el-form-item>
        <el-form-item label="排班摘要">
          <div style="font-size: 13px; color: #64748b; line-height: 1.6;">
            包含 <strong>{{ points.length }}</strong> 家门店，涵盖周一至周日完整作业日分配。
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="saveDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveSchedule">确认保存</el-button>
      </template>
    </el-dialog>

    <!-- TruckSchedule Configuration Dialog -->
    <el-dialog v-model="configDialogVisible" title="⚙️ 运筹调度算法参数设置 (TruckSchedule)" width="560px" destroy-on-close :append-to-body="true">
      <el-form label-width="160px" label-position="left" style="padding: 4px 10px;">
        <el-form-item label="目标最大装载率">
          <div style="display: flex; align-items: center; gap: 12px; width: 100%;">
            <el-slider v-model="scheduleOptions.max_truck_capacity_rate" :min="0.5" :max="1.0" :step="0.01" style="flex: 1;" />
            <span style="font-weight: 700; width: 45px; text-align: right; color: #0284c7;">{{ Math.round(scheduleOptions.max_truck_capacity_rate * 100) }}%</span>
          </div>
          <div style="font-size: 11px; color: #94a3b8; line-height: 1.4;">(max_truck_capacity_rate) 单车装载货量上限目标比例，默认 96%</div>
        </el-form-item>

        <el-form-item label="局部搜索邻居簇数">
          <el-input-number v-model="scheduleOptions.search_n_neighbor" :min="1" :max="10" />
          <div style="font-size: 11px; color: #94a3b8; line-height: 1.4; margin-top: 2px;">(search_n_neighbor) 搜索跨相邻店群串点优化时的邻居簇数量，默认 1</div>
        </el-form-item>

        <el-form-item label="最大允许绕路距离">
          <div style="display: flex; align-items: center; gap: 8px;">
            <el-input-number v-model="scheduleOptions.detour_thres" :min="10" :max="2000" :step="50" />
            <span style="font-size: 12px; color: #64748b;">km</span>
          </div>
          <div style="font-size: 11px; color: #94a3b8; line-height: 1.4; margin-top: 2px;">(detour_thres) 串点规划时允许的最大折返绕路距离，默认 500 km</div>
        </el-form-item>

        <el-form-item label="临近店判定阈值">
          <el-input-number v-model="scheduleOptions.dist_thres" :min="0.1" :max="5.0" :step="0.1" />
          <div style="font-size: 11px; color: #94a3b8; line-height: 1.4; margin-top: 2px;">(dist_thres) 判断门店是否同属紧密片区的相对距离系数，默认 0.9</div>
        </el-form-item>

        <el-form-item label="单程最大跨度">
          <div style="display: flex; align-items: center; gap: 8px;">
            <el-input-number v-model="scheduleOptions.one_way_dist_max" :min="5" :max="300" :step="5" />
            <span style="font-size: 12px; color: #64748b;">km</span>
          </div>
          <div style="font-size: 11px; color: #94a3b8; line-height: 1.4; margin-top: 2px;">(one_way_dist_max) 同一路线上相邻两店最大允许直线距离，默认 40 km</div>
        </el-form-item>

        <el-form-item label="周作业排班天数">
          <el-select v-model="scheduleOptions.work_days" style="width: 200px;">
            <el-option label="6 天 (周一 ~ 周六)" :value="6" />
            <el-option label="7 天 (周一 ~ 周日)" :value="7" />
            <el-option label="5 天 (周一 ~ 周五)" :value="5" />
          </el-select>
          <div style="font-size: 11px; color: #94a3b8; line-height: 1.4; margin-top: 2px;">(work_days) 均衡排班算法循环分配作业日的总周期天数</div>
        </el-form-item>
      </el-form>

      <template #footer>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <el-button @click="resetDefaultOptions">恢复默认值</el-button>
          <div>
            <el-button @click="configDialogVisible = false">取消</el-button>
            <el-button type="primary" @click="saveScheduleOptions">保存参数</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- Load History Modal Dialog -->
    <el-dialog v-model="historyDialogVisible" title="导入历史店群分组 / 排班方案" width="760px" destroy-on-close :append-to-body="true">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; gap: 12px; flex-wrap: wrap;">
        <el-tabs v-model="historyTab" @tab-change="fetchHistory" style="margin-bottom: 0;">
          <el-tab-pane label="从店群分组历史导入" name="CLUSTERING" />
          <el-tab-pane label="从店群排班历史导入" name="CLUSTER_SCHEDULE" />
        </el-tabs>

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
            <el-button type="primary" size="small" @click="loadHistoryData(row)">导入此方案</el-button>
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
import ScheduleBalanceCard from '../components/planning/ScheduleBalanceCard.vue'
import { clusteringApi } from '../api/client.js'
import { dotHtml } from '../utils/mapMarkers.js'
import { parseFileUniversal } from '../utils/excelImport.js'
import * as XLSX from 'xlsx'
import { ElMessage } from 'element-plus'

const route = useRoute()
const mapCenter = [108.33, 22.80]

const mapPanel = ref(null)
const amap = ref(null)
const points = ref([])
const dataSourceLabel = ref('')
const loading = ref(false)
const errorMsg = ref('')

const selectedDay = ref('全部')
const depotName = ref('南宁中心仓')
const depotLng = ref(108.318344)
const depotLat = ref(22.846367)
const depotList = ref([])
const selectedDepotKey = ref('')

const selectedPointIndices = ref([])
const batchTargetDay = ref('')
const isSelecting = ref(false)
let mouseTool = null

let storeMarkers = []
let singleInfoWindow = null
let labelsLayer = null

function getStoreBubbleContent(p, idx) {
  const storeFreq = Math.round(Number(p.frequency || (p.delivery_days_str ? p.delivery_days_str.split(',').filter(Boolean).length : 1)))
  const validOpts = getValidScheduleOptionsForFreq(storeFreq)
  let optionsHtml = validOpts.map(opt => `<option value="${opt.value}" ${p.delivery_days_str === opt.value ? 'selected' : ''}>${opt.label}</option>`).join('')
  if (p.delivery_days_str && !validOpts.some(opt => opt.value === p.delivery_days_str)) {
    optionsHtml = `<option value="${p.delivery_days_str}" selected disabled>⚠️ 当前非标准作业日: ${p.delivery_days_str} (请选择合规模式)</option>` + optionsHtml
  }

  const isHp = Number(p.is_homepot !== undefined && p.is_homepot !== null ? p.is_homepot : 0)
  return `
    <div style="padding: 12px; font-size: 12px; line-height: 1.5; color: #1e293b; min-width: 260px; background: #fff; border-radius: 8px;">
      <div style="font-weight: 700; font-size: 14px; margin-bottom: 8px; color: #0f172a; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; display: flex; justify-content: space-between;">
        <span>${p.name || '未命名门店'}</span>
        <span style="font-size: 11px; color: #94a3b8;">#${idx + 1}</span>
      </div>
      <div style="margin-bottom: 5px; color: #64748b;">
        所属店群: <strong style="color: #0284c7;">店群 ${(p.cluster_id !== undefined ? p.cluster_id : 0) + 1}</strong>
      </div>
      <div style="margin-bottom: 5px; color: #64748b;">
        日均货量: <strong>${p.avg_loads || 0.0}</strong> 箱 | 配送频次: <strong style="color: #0284c7;">每周 ${storeFreq} 次</strong>
      </div>
      <div style="margin-bottom: 5px; color: #64748b; display: flex; align-items: center; justify-content: space-between;">
        <span>门店属性:</span>
        <select onchange="window.updateStoreHomepot(${idx}, this.value)" style="font-size: 11px; padding: 2px 6px; border: 1px solid #cbd5e1; border-radius: 4px; background: #f8fafc; font-weight: 600;">
          <option value="1" ${isHp === 1 ? 'selected' : ''}>🏠 本埠门店</option>
          <option value="0" ${isHp === 0 ? 'selected' : ''}>🚗 外埠门店</option>
        </select>
      </div>
      <div style="margin-top: 8px;">
        <div style="font-size: 11px; font-weight: 600; color: #475569; margin-bottom: 4px;">
          调整配送作业日 (限定 ${storeFreq}次/周 规则):
        </div>
        <select onchange="window.updateScheduleDays(${idx}, this.value)" style="width: 100%; font-size: 11px; padding: 5px; border: 1px solid #0284c7; border-radius: 4px; background: #f0f9ff; color: #0369a1; font-weight: 600;">
          ${optionsHtml}
        </select>
      </div>
    </div>
  `
}

function openStoreInfoWindow(p, idx, pos) {
  const mapObj = mapPanel.value?.getMap()
  const A = amap.value
  if (!mapObj || !A) return
  if (!singleInfoWindow) {
    singleInfoWindow = new A.InfoWindow({
      offset: new A.Pixel(0, -18),
      closeWhenClickMap: true
    })
  }
  singleInfoWindow.setContent(getStoreBubbleContent(p, idx))
  singleInfoWindow.open(mapObj, pos || [Number(p.lng), Number(p.lat)])
}

const handleSelectStore = (item) => {
  if (!item || item.index === undefined) return
  const mapObj = mapPanel.value?.getMap()
  const p = points.value[item.index]
  if (!p || !mapObj) return
  const pos = [Number(p.lng), Number(p.lat)]
  mapObj.setZoomAndCenter(15, pos)
  openStoreInfoWindow(p, item.index, pos)
}

// Save & History Modal States
const saveDialogVisible = ref(false)
const planTitle = ref('')
const saving = ref(false)

const historyDialogVisible = ref(false)
const historyTab = ref('CLUSTERING')
const historySaveType = ref('')
const historyList = ref([])
const loadingHistory = ref(false)

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
      ElMessage.error('未能成功解析有效门店排班数据，请检查文件内容与经纬度字段')
      return
    }

    if (warnings && warnings.length) {
      ElMessage.warning(`解析提示: ${warnings[0]}`)
    }

    // 映射到排班视图格式，并智能初始化排班作业日与周频次
    points.value = parsedPoints.map((p, idx) => {
      let daysStr = p.delivery_days_str ? p.delivery_days_str.trim() : ''
      const daysCount = daysStr ? daysStr.split(/[,，、\s]+/).filter(Boolean).length : 0
      let freq = daysCount > 0 ? daysCount : Math.max(1, Number(p.frequency || 1))

      // 若导入文件未包含作业日列，根据频次智能初始化默认作业日
      if (!daysStr) {
        if (freq >= 6) {
          daysStr = '周一,周二,周三,周四,周五,周六'
        } else if (freq >= 4) {
          daysStr = '周一,周二,周四,周五'
        } else if (freq === 3) {
          daysStr = '周一,周三,周五'
        } else if (freq === 2) {
          daysStr = '周一,周四'
        } else {
          daysStr = '周一'
        }
      }

      const finalFreq = daysStr.split(',').filter(Boolean).length || freq

      if (p.warehouse_name || p.dc_code) {
        depotName.value = p.warehouse_name || p.dc_code
      }

      return {
        name: p.name || `门店${idx + 1}`,
        shop_code: p.shop_code || '',
        dept_id: p.dept_id || '',
        district: p.district || '',
        warzone: p.warzone || '',
        lng: Number(p.lng),
        lat: Number(p.lat),
        longitude: Number(p.lng),
        latitude: Number(p.lat),
        avg_loads: Number(p.avg_loads || p.weight || 10),
        frequency: finalFreq,
        is_homepot: p.is_homepot !== undefined ? Number(p.is_homepot) : 0,
        service_time: p.service_time || 0.65,
        available_truck: p.available_truck || '',
        address: p.address || '',
        cluster_id: p.cluster_id !== undefined ? p.cluster_id : (p.cluster_center_id !== undefined ? p.cluster_center_id : 0),
        center_lng: p.center_lng ? Number(p.center_lng) : Number(p.lng),
        center_lat: p.center_lat ? Number(p.center_lat) : Number(p.lat),
        cdist_warehouse: p.cdist_warehouse ? Number(p.cdist_warehouse) : 0,
        sdist_warehouse: p.sdist_warehouse ? Number(p.sdist_warehouse) : 0,
        delivery_days_str: daysStr
      }
    })

    dataSourceLabel.value = `Excel 导入「${file.name}」`
    selectedPointIndices.value = []
    renderPoints()
    if (points.value.length) {
      mapPanel.value?.fitView()
    }
    saveToLocalStorage()
    ElMessage.success(`成功导入 ${points.value.length} 家门店排班数据！`)
  } catch (err) {
    ElMessage.error(`导入排班文件失败: ${err.message || err}`)
  }
}

const downloadScheduleTemplate = () => {
  const sampleData = [
    {
      '门店编号': 'STORE_1001',
      '门店名称': '南宁津头店',
      '所属仓库': '南宁中心仓',
      '所属店群': 1,
      '所属行政区': '青秀区',
      '计划配送作业日': '周一,周三,周五',
      '周配送频次': 3,
      '日均箱数': 77,
      '本外埠': '本埠',
      '经度': 108.335965,
      '纬度': 22.799882,
      '卸货耗时_小时': 0.9,
      '指定车型': '4.2米厢车',
      '详细地址': '南宁市青秀区津头街道'
    },
    {
      '门店编号': 'STORE_1002',
      '门店名称': '南宁东葛店',
      '所属仓库': '南宁中心仓',
      '所属店群': 1,
      '所属行政区': '青秀区',
      '计划配送作业日': '周二,周四,周六',
      '周配送频次': 3,
      '日均箱数': 36,
      '本外埠': '本埠',
      '经度': 108.339847,
      '纬度': 22.823789,
      '卸货耗时_小时': 0.8,
      '指定车型': '4.2米厢车',
      '详细地址': '南宁市青秀区东葛路'
    },
    {
      '门店编号': 'STORE_1003',
      '门店名称': '柳州鱼峰店',
      '所属仓库': '南宁中心仓',
      '所属店群': 2,
      '所属行政区': '柳州市',
      '计划配送作业日': '周一,周四',
      '周配送频次': 2,
      '日均箱数': 25,
      '本外埠': '外埠',
      '经度': 109.40286,
      '纬度': 24.304495,
      '卸货耗时_小时': 0.9,
      '指定车型': '4.2米厢车',
      '详细地址': '柳州市鱼峰区驾鹤路'
    }
  ]

  const wb = XLSX.utils.book_new()
  const ws = XLSX.utils.json_to_sheet(sampleData)
  ws['!cols'] = [
    { wch: 14 }, { wch: 18 }, { wch: 14 }, { wch: 10 }, { wch: 12 },
    { wch: 18 }, { wch: 12 }, { wch: 10 }, { wch: 10 }, { wch: 12 },
    { wch: 12 }, { wch: 14 }, { wch: 14 }, { wch: 24 }
  ]
  XLSX.utils.book_append_sheet(wb, ws, '门店排班模板')
  XLSX.writeFile(wb, '门店排班算法格式导入模板.xlsx')
  ElMessage.success('已下载标准排班导入模板')
}

// TruckSchedule Algorithm Options
const defaultScheduleOptions = {
  max_truck_capacity_rate: 0.96,
  search_n_neighbor: 1,
  simple_mode_thres: 0,
  detour_thres: 500,
  dist_thres: 0.9,
  one_way_dist_max: 40,
  work_days: 6
}

const scheduleOptions = ref({ ...defaultScheduleOptions })
try {
  const saved = localStorage.getItem('schedule_truck_options')
  if (saved) {
    scheduleOptions.value = { ...defaultScheduleOptions, ...JSON.parse(saved) }
  }
} catch (e) {}

const configDialogVisible = ref(false)

const openConfigModal = () => {
  const saved = localStorage.getItem('schedule_truck_options')
  if (saved) {
    try {
      scheduleOptions.value = { ...defaultScheduleOptions, ...JSON.parse(saved) }
    } catch (e) {}
  }
  configDialogVisible.value = true
}

const resetDefaultOptions = () => {
  scheduleOptions.value = { ...defaultScheduleOptions }
  localStorage.setItem('schedule_truck_options', JSON.stringify(scheduleOptions.value))
  ElMessage.info('已恢复为系统默认参数设置')
}

const saveScheduleOptions = () => {
  localStorage.setItem('schedule_truck_options', JSON.stringify(scheduleOptions.value))
  configDialogVisible.value = false
  ElMessage.success('TruckSchedule 运力排班参数已更新并保存！')
}

const DAY_COLORS = {
  '周一': '#3b82f6', // bright blue
  '周二': '#10b981', // emerald green
  '周三': '#ef4444', // vibrant red
  '周四': '#f59e0b', // amber orange
  '周五': '#8b5cf6', // violet purple
  '周六': '#ec4899', // hot pink
  '周日': '#06b6d4'  // dark cyan
}

// 严格间隔约束的排班作业日枚举
const SCHEDULE_DAY_GROUPS = [
  {
    label: '每周 1 次 (单日配送 - 可设为任意单日)',
    options: [
      { label: '周一 (1次/周)', value: '周一' },
      { label: '周二 (1次/周)', value: '周二' },
      { label: '周三 (1次/周)', value: '周三' },
      { label: '周四 (1次/周)', value: '周四' },
      { label: '周五 (1次/周)', value: '周五' },
      { label: '周六 (1次/周)', value: '周六' },
      { label: '周日 (1次/周)', value: '周日' }
    ]
  },
  {
    label: '每周 2 次 (间隔 3 天均衡配送)',
    options: [
      { label: '周一 / 周四 (2次/周)', value: '周一,周四' },
      { label: '周二 / 周五 (2次/周)', value: '周二,周五' },
      { label: '周三 / 周六 (2次/周)', value: '周三,周六' }
    ]
  },
  {
    label: '每周 3 次 (隔天均衡配送)',
    options: [
      { label: '周一 / 周三 / 周五 (3次/周: 1/3/5)', value: '周一,周三,周五' },
      { label: '周二 / 周四 / 周六 (3次/周: 2/4/6)', value: '周二,周四,周六' }
    ]
  },
  {
    label: '高频 / 全周配送',
    options: [
      { label: '周一 / 周二 / 周四 / 周五 (4次/周)', value: '周一,周二,周四,周五' },
      { label: '周一 至 周六 (6次/周)', value: '周一,周二,周三,周四,周五,周六' },
      { label: '每天配送 (7次/周)', value: '周一,周二,周三,周四,周五,周六,周日' }
    ]
  }
]

const activePoints = computed(() => {
  if (selectedDay.value === '全部') return points.value
  return points.value.filter(p => p.delivery_days_str && p.delivery_days_str.includes(selectedDay.value))
})

const activeDayLoad = computed(() => {
  return Math.round(activePoints.value.reduce((sum, p) => sum + (Number(p.avg_loads || p.weight) || 0), 0))
})

const dailyStats = computed(() => {
  const stats = {
    '周一': { count: 0, load: 0.0 },
    '周二': { count: 0, load: 0.0 },
    '周三': { count: 0, load: 0.0 },
    '周四': { count: 0, load: 0.0 },
    '周五': { count: 0, load: 0.0 },
    '周六': { count: 0, load: 0.0 },
    '周日': { count: 0, load: 0.0 }
  }
  points.value.forEach(p => {
    if (!p.delivery_days_str) return
    const days = p.delivery_days_str.split(',')
    days.forEach(d => {
      const trimDay = d.trim()
      if (stats[trimDay]) {
        stats[trimDay].count += 1
        stats[trimDay].load += Number(p.avg_loads || 0.0)
      }
    })
  })
  return stats
})

function clearAll() {
  if (points.value.length > 0) {
    const confirmClear = confirm('是否确认清空当前排班数据？')
    if (!confirmClear) return
  }
  points.value = []
  selectedPointIndices.value = []
  errorMsg.value = ''
  dataSourceLabel.value = ''
  mapPanel.value?.clearAll()
  saveToLocalStorage()
}

function getPointColor(p, idx) {
  if (selectedPointIndices.value.includes(idx)) {
    return '#0d9488'
  }
  if (!p.delivery_days_str) return '#94a3b8'
  const firstDay = p.delivery_days_str.split(',')[0].trim()
  return DAY_COLORS[firstDay] || '#94a3b8'
}

// 获取特定频次严格允许的排班作业日枚举选项
function getValidScheduleOptionsForFreq(freq) {
  const f = Math.round(Number(freq || 1))
  if (f === 2) {
    return [
      { label: '周一 / 周四 (2次/周: 间隔3天)', value: '周一,周四' },
      { label: '周二 / 周五 (2次/周: 间隔3天)', value: '周二,周五' },
      { label: '周三 / 周六 (2次/周: 间隔3天)', value: '周三,周六' }
    ]
  } else if (f === 3) {
    return [
      { label: '周一 / 周三 / 周五 (3次/周: 1/3/5)', value: '周一,周三,周五' },
      { label: '周二 / 周四 / 周六 (3次/周: 2/4/6)', value: '周二,周四,周六' }
    ]
  } else if (f === 4) {
    return [
      { label: '周一 / 周二 / 周四 / 周五 (4次/周)', value: '周一,周二,周四,周五' }
    ]
  } else if (f === 6) {
    return [
      { label: '周一 至 周六 (6次/周)', value: '周一,周二,周三,周四,周五,周六' }
    ]
  } else if (f >= 7) {
    return [
      { label: '每天配送 (7次/周: 周一至周日)', value: '周一,周二,周三,周四,周五,周六,周日' }
    ]
  } else {
    // 默认 1 次/周: 可规划至任意单个工作日
    return [
      { label: '周一 (1次/周)', value: '周一' },
      { label: '周二 (1次/周)', value: '周二' },
      { label: '周三 (1次/周)', value: '周三' },
      { label: '周四 (1次/周)', value: '周四' },
      { label: '周五 (1次/周)', value: '周五' },
      { label: '周六 (1次/周)', value: '周六' },
      { label: '周日 (1次/周)', value: '周日' }
    ]
  }
}

// In-map point attribute update
window.updateScheduleDays = function(idx, daysStr) {
  if (points.value[idx]) {
    points.value[idx].delivery_days_str = daysStr
    ElMessage.success(`门店 [${points.value[idx].name || idx + 1}] 配送作业日已更新为: ${daysStr}`)
    renderPoints()
    saveToLocalStorage()
  }
}

window.updateStoreHomepot = function(idx, val) {
  if (points.value[idx]) {
    points.value[idx].is_homepot = Number(val)
    ElMessage.success(`门店 [${points.value[idx].name || idx + 1}] 属性已更新为: ${Number(val) === 1 ? '本埠门店' : '外埠门店'}`)
    renderPoints()
    saveToLocalStorage()
  }
}

// 缓存纯色圆形图标 Base64 数据 URI，避免重复生成
const iconCache = new Map()
function getCircleIcon(color, size = 20, isSelected = false, opacity = 1.0) {
  const cacheKey = `${color}_${size}_${isSelected}_${opacity}`
  if (iconCache.has(cacheKey)) {
    return iconCache.get(cacheKey)
  }
  const canvas = document.createElement('canvas')
  const scale = 2
  canvas.width = size * scale
  canvas.height = size * scale
  const ctx = canvas.getContext('2d')
  ctx.scale(scale, scale)

  ctx.globalAlpha = opacity

  // 绘制外发光/边框 (若被选中)
  if (isSelected) {
    ctx.beginPath()
    ctx.arc(size / 2, size / 2, size / 2 - 2, 0, Math.PI * 2)
    ctx.strokeStyle = '#0d9488'
    ctx.lineWidth = 3
    ctx.stroke()
  }

  // 绘制实心圆
  ctx.beginPath()
  ctx.arc(size / 2, size / 2, size / 2 - (isSelected ? 4 : 2), 0, Math.PI * 2)
  ctx.fillStyle = color
  ctx.fill()
  ctx.strokeStyle = '#ffffff'
  ctx.lineWidth = 1.5
  ctx.stroke()

  const dataUri = canvas.toDataURL()
  iconCache.set(cacheKey, dataUri)
  return dataUri
}

function renderPoints() {
  if (!amap.value || !mapPanel.value) return
  const A = amap.value
  const mapObj = mapPanel.value?.getMap()
  if (!mapObj) return

  mapPanel.value.clearAll()
  storeMarkers = []
  if (labelsLayer) {
    try {
      labelsLayer.clear()
      mapObj.remove(labelsLayer)
    } catch (e) {}
    labelsLayer = null
  }

  // 1. Draw Depot (单个 Marker)
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

  // 2. High-Performance Canvas LabelsLayer for Stores
  labelsLayer = new A.LabelsLayer({
    zooms: [3, 20],
    zIndex: 1000,
    collision: false,
    allowCollision: true
  })

  const labelMarkers = []

  points.value.forEach((p, idx) => {
    if (p.lng === '' || p.lat === '') return

    let opacity = 1.0
    if (selectedDay.value !== '全部') {
      const match = p.delivery_days_str && p.delivery_days_str.includes(selectedDay.value)
      if (!match) {
        opacity = 0.15
      }
    }

    const isSelected = selectedPointIndices.value.includes(idx)
    const color = getPointColor(p, idx)
    const size = isSelected ? 24 : 18

    const storeFreq = Math.round(Number(p.frequency || (p.delivery_days_str ? p.delivery_days_str.split(',').filter(Boolean).length : 1)))
    p.frequency = storeFreq

    const iconUri = getCircleIcon(color, size, isSelected, opacity)

    // 配置 LabelMarker 标注
    const markerConfig = {
      position: [Number(p.lng), Number(p.lat)],
      opacity,
      rank: isSelected ? 2 : 1,
      icon: {
        type: 'image',
        image: iconUri,
        size: [size, size],
        anchor: 'center'
      },
      text: {
        content: String(idx + 1),
        direction: 'center',
        offset: [0, 0],
        style: {
          fontSize: size <= 18 ? 9 : 11,
          fontWeight: 'bold',
          fillColor: '#ffffff',
          strokeColor: color,
          strokeWidth: 0.5
        }
      },
      extData: {
        point: p,
        index: idx
      }
    }

    const labelMarker = new A.LabelMarker(markerConfig)

    labelMarker.on('click', () => {
      openStoreInfoWindow(p, idx, [Number(p.lng), Number(p.lat)])
    })

    labelMarkers.push(labelMarker)
    storeMarkers[idx] = labelMarker
  })

  labelsLayer.add(labelMarkers)
  mapObj.add(labelsLayer)
  mapPanel.value.addOverlay(labelsLayer)
}

function initMouseTool() {
  const A = amap.value
  const mapObj = mapPanel.value?.getMap()
  if (!mapObj) return

  A.plugin(['AMap.MouseTool'], () => {
    mouseTool = new A.MouseTool(mapObj)
    mouseTool.on('draw', (e) => {
      const rect = e.obj
      const bounds = rect.getBounds()
      const newSelected = []

      points.value.forEach((p, idx) => {
        if (p.lng === '' || p.lat === '') return
        const pos = new A.LngLat(Number(p.lng), Number(p.lat))
        if (bounds.contains(pos)) {
          newSelected.push(idx)
        }
      })

      selectedPointIndices.value = newSelected
      mouseTool.close(true)
      isSelecting.value = false
      renderPoints()
      ElMessage.info(`框选了 ${newSelected.length} 家门店`)
    })
  })
}

function toggleSelectTool() {
  if (isSelecting.value) {
    mouseTool?.close(true)
    isSelecting.value = false
  } else {
    selectedPointIndices.value = []
    isSelecting.value = true
    mouseTool?.rectangle({
      fillColor: '#0d9488',
      strokeColor: '#0d9488',
      fillOpacity: 0.15,
      strokeOpacity: 0.8,
      strokeWeight: 1
    })
  }
  renderPoints()
}

function applyBatchDayChange() {
  if (!batchTargetDay.value) return
  const targetFreq = batchTargetDay.value.split(',').filter(Boolean).length
  let updatedCount = 0
  let skippedCount = 0
  selectedPointIndices.value.forEach(idx => {
    const p = points.value[idx]
    if (!p) return
    const storeFreq = Math.round(Number(p.frequency || 1))
    if (storeFreq === targetFreq) {
      p.delivery_days_str = batchTargetDay.value
      updatedCount++
    } else {
      skippedCount++
    }
  })
  selectedPointIndices.value = []
  batchTargetDay.value = ''
  renderPoints()
  saveToLocalStorage()
  if (updatedCount > 0 && skippedCount === 0) {
    ElMessage.success(`已为选中的 ${updatedCount} 家门店批量应用排班: ${batchTargetDay.value}`)
  } else if (updatedCount > 0 && skippedCount > 0) {
    ElMessage.warning(`已为 ${updatedCount} 家频次为 ${targetFreq} 次的门店应用排班，跳过了 ${skippedCount} 家频次不一致的门店`)
  } else {
    ElMessage.error(`未匹配到频次为 ${targetFreq} 次/周 的门店（框选门店的频次属性与所选模式不匹配）`)
  }
}

async function solveSchedule() {
  errorMsg.value = ''
  if (points.value.length < 2) {
    errorMsg.value = '请至少添加 2 个门店点'
    return
  }
  loading.value = true
  try {
    const payload = {
      points: points.value.map(p => ({
        ...p,
        name: p.name || '',
        shop_code: p.shop_code || '',
        dept_id: p.dept_id || '',
        district: p.district || '',
        warzone: p.warzone || '',
        address: p.address || '',
        service_time: p.service_time || 0.65,
        available_truck: p.available_truck || '',
        lng: Number(p.lng),
        lat: Number(p.lat),
        avg_loads: Number(p.avg_loads || 0.0),
        frequency: Number(p.frequency || 1),
        is_homepot: p.is_homepot !== undefined ? Number(p.is_homepot) : 0,
        cluster_id: p.cluster_id || 0,
        center_lng: p.center_lng ? Number(p.center_lng) : Number(p.lng),
        center_lat: p.center_lat ? Number(p.center_lat) : Number(p.lat),
        cdist_warehouse: p.cdist_warehouse ? Number(p.cdist_warehouse) : 0.0,
        sdist_warehouse: p.sdist_warehouse ? Number(p.sdist_warehouse) : 0.0
      })),
      depot_lng: Number(depotLng.value),
      depot_lat: Number(depotLat.value),
      options: scheduleOptions.value
    }

    const resp = await clusteringApi.solveSchedule(payload)
    if (resp?.points && resp.points.length) {
      points.value = points.value.map((p, idx) => {
        const updated = resp.points[idx] || resp.points.find(up => (up.name && up.name === p.name) || (up.shop_code && up.shop_code === p.shop_code))
        return {
          ...p,
          ...(updated || {}),
          // 确保用户维护的本埠属性与排班结果严格保留
          is_homepot: p.is_homepot !== undefined ? Number(p.is_homepot) : (updated?.is_homepot !== undefined ? Number(updated.is_homepot) : 0),
          delivery_days_str: updated ? (updated.delivery_days_str || p.delivery_days_str) : p.delivery_days_str
        }
      })
    }
    renderPoints()
    saveToLocalStorage()
    ElMessage.success('周作业日自动排班计算完成！')
  } catch (e) {
    const msg = e.message || '网络连接异常或求解超时'
    errorMsg.value = '自动排班失败: ' + msg
    ElMessage.error(errorMsg.value)
  } finally {
    loading.value = false
  }
}

function saveToLocalStorage() {
  try {
    localStorage.setItem('schedule_points', JSON.stringify(points.value))
    localStorage.setItem('schedule_savedAt', new Date().toISOString())
    localStorage.setItem('schedule_depot_name', depotName.value)
    localStorage.setItem('schedule_depot_lng', String(depotLng.value))
    localStorage.setItem('schedule_depot_lat', String(depotLat.value))
  } catch (e) {
    console.warn('[LocalStorage] 存储排班数据超出配额，安全降级:', e)
  }
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
    renderPoints()
    saveToLocalStorage()
  }
}

const onDepotCustomChange = () => {
  renderPoints()
  saveToLocalStorage()
}

// -------------------------------------------------------------
// Save & Load History Implementations
// -------------------------------------------------------------
const openSaveModal = () => {
  planTitle.value = `店群排班方案_${new Date().toLocaleDateString()}`
  saveDialogVisible.value = true
}

const handleSaveSchedule = async () => {
  if (!points.value.length) return
  saving.value = true
  try {
    const payload = {
      title: planTitle.value || `店群排班方案_${new Date().toLocaleDateString()}`,
      depot_name: depotName.value,
      depot_lng: Number(depotLng.value),
      depot_lat: Number(depotLat.value),
      points: points.value
    }

    const res = await fetch('/api/clustering/save_schedule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}))
      throw new Error(errData.detail || '保存排班方案失败')
    }
    ElMessage.success('店群排班方案已成功保存至历史记录！')
    saveDialogVisible.value = false
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    saving.value = false
  }
}

const openHistoryModal = () => {
  historyDialogVisible.value = true
  fetchHistory()
}

const fetchHistory = async () => {
  loadingHistory.value = true
  try {
    const params = new URLSearchParams()
    if (historyTab.value) params.append('task_type', historyTab.value)
    if (historySaveType.value) params.append('save_type', historySaveType.value)
    const res = await fetch(`/api/history/?${params.toString()}`)
    if (!res.ok) throw new Error('获取历史数据失败')
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
        return `店群分组方案 (${p.algorithm}${count ? `, ${count}家门店` : ''})`
      }
    }
  } catch (e) {}
  return `${row.task_type === 'CLUSTERING' ? '店群分组方案' : '店群排班方案'} (${row.task_id.substring(0, 8)})`
}

const loadHistoryData = (row) => {
  try {
    if (!row.result && !row.parameters) {
      ElMessage.warning('该历史记录中无有效数据')
      return
    }
    const resData = row.result ? (typeof row.result === 'string' ? JSON.parse(row.result) : row.result) : {}
    const paramData = row.parameters ? (typeof row.parameters === 'string' ? JSON.parse(row.parameters) : row.parameters) : {}
    
    const pointsList = (resData.points && resData.points.length) ? resData.points : (paramData.points || [])
    if (Array.isArray(pointsList) && pointsList.length) {
      points.value = pointsList.map((p, idx) => {
        const daysStr = p.delivery_days_str || (p.frequency >= 3 ? '周一,周三,周五' : (p.frequency === 2 ? '周一,周四' : '周一'))
        const freq = daysStr ? daysStr.split(',').filter(Boolean).length : Number(p.frequency || 1)
        return {
          name: p.name || `门店${idx + 1}`,
          shop_code: p.shop_code || '',
          lng: Number(p.lng !== undefined ? p.lng : p.longitude),
          lat: Number(p.lat !== undefined ? p.lat : p.latitude),
          avg_loads: Number(p.avg_loads || p.weight || 10),
          frequency: freq,
          delivery_days_str: daysStr,
          is_homepot: p.is_homepot !== undefined ? Number(p.is_homepot) : 0,
          district: p.district || '',
          warzone: p.warzone || '',
          cluster_id: p.cluster_id !== undefined ? p.cluster_id : (resData.assignments ? resData.assignments[idx] : 0),
          center_lng: p.center_lng,
          center_lat: p.center_lat,
          cdist_warehouse: p.cdist_warehouse,
          sdist_warehouse: p.sdist_warehouse
        }
      })
    }

    if (resData.depot_name || paramData.depot_name) depotName.value = resData.depot_name || paramData.depot_name
    if (resData.depot_lng || paramData.depot_lng) depotLng.value = Number(resData.depot_lng || paramData.depot_lng)
    if (resData.depot_lat || paramData.depot_lat) depotLat.value = Number(resData.depot_lat || paramData.depot_lat)

    renderPoints()
    if (points.value.length) {
      mapPanel.value?.fitView()
    }
    dataSourceLabel.value = `历史方案「${getPlanTitle(row)}」`
    saveToLocalStorage()
    historyDialogVisible.value = false
    ElMessage.success(`已成功导入历史店群方案（${points.value.length} 家门店）！`)
  } catch (err) {
    ElMessage.error('导入方案失败: ' + err.message)
  }
}

async function loadScheduleData() {
  try {
    if (!amap.value && mapPanel.value) {
      amap.value = await (mapPanel.value.whenReady ? mapPanel.value.whenReady() : mapPanel.value.getAmap())
    }
  } catch (e) {}

  initMouseTool()
  
  // Restore last-edited points from localStorage
  const savedPoints = localStorage.getItem('schedule_points')
  if (savedPoints) {
    try {
      points.value = JSON.parse(savedPoints)
    } catch (e) {}
  }
  const savedName = localStorage.getItem('schedule_depot_name')
  if (savedName) depotName.value = savedName
  const savedLng = localStorage.getItem('schedule_depot_lng')
  if (savedLng) depotLng.value = Number(savedLng)
  const savedLat = localStorage.getItem('schedule_depot_lat')
  if (savedLat) depotLat.value = Number(savedLat)

  await fetchDepots()

  if (points.value.length) {
    const savedAt = localStorage.getItem('schedule_savedAt')
    const dateStr = savedAt ? new Date(savedAt).toLocaleDateString() : ''
    dataSourceLabel.value = dateStr ? `上次编辑（${dateStr}）` : '上次编辑'
    ElMessage.info(`已恢复上次编辑的 ${points.value.length} 家门店${dateStr ? `（${dateStr}）` : ''}`)
  }

  // Auto-sync is_homepot with database stores if available
  if (points.value.length) {
    try {
      const sRes = await fetch('/api/store/?limit=5000')
      if (sRes.ok) {
        const dbList = await sRes.json()
        const dbMap = new Map()
        dbList.forEach(s => {
          if (s.shop_code) dbMap.set(String(s.shop_code).trim(), Number(s.is_homepot))
          if (s.name) dbMap.set(String(s.name).trim(), Number(s.is_homepot))
        })
        let updated = false
        points.value.forEach(p => {
          const code = p.shop_code ? String(p.shop_code).trim() : ''
          const name = p.name ? String(p.name).trim() : ''
          if (dbMap.has(code)) {
            const dbVal = dbMap.get(code)
            if (p.is_homepot !== dbVal) {
              p.is_homepot = dbVal
              updated = true
            }
          } else if (dbMap.has(name)) {
            const dbVal = dbMap.get(name)
            if (p.is_homepot !== dbVal) {
              p.is_homepot = dbVal
              updated = true
            }
          } else if (p.is_homepot === undefined || p.is_homepot === null) {
            p.is_homepot = 1
            updated = true
          }
        })
        if (updated) {
          saveToLocalStorage()
        }
      }
    } catch (e) {}
  }

  setTimeout(() => {
    renderPoints()
    if (points.value.length) {
      mapPanel.value?.fitView()
    }
  }, 300)
}

onMounted(async () => {
  await loadScheduleData()
})

watch(
  () => [route.path, route.query.t],
  ([newPath]) => {
    if (newPath === '/clustering/schedule') {
      loadScheduleData()
    }
  }
)

onBeforeUnmount(() => {
  delete window.updateScheduleDays
  delete window.updateStoreHomepot
  if (mouseTool) {
    mouseTool.close(true)
  }
  if (labelsLayer) {
    try {
      labelsLayer.clear()
    } catch (e) {}
    labelsLayer = null
  }
  if (singleInfoWindow) {
    try {
      singleInfoWindow.close()
    } catch (e) {}
    singleInfoWindow = null
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
</style>
