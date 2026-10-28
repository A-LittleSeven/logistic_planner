<template>
  <el-dialog
    :model-value="modelValue"
    title="✨ 新建规划画布 (Scope Workspace)"
    width="820px"
    :close-on-click-modal="false"
    destroy-on-close
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <el-steps :active="createStep" finish-status="success" align-center style="margin-bottom: 24px;">
      <el-step title="基础与中心仓设定" description="设定画布名称与起点仓库" />
      <el-step title="挑选规划门店池" description="从系统池勾选或导入门店" />
    </el-steps>

    <!-- Step 1: Base Info & Depot -->
    <div v-show="createStep === 0" class="dialog-step-content">
      <el-form label-position="top" :model="newCanvasForm">
        <el-form-item label="画布名称" required>
          <el-input
            v-model="newCanvasForm.name"
            placeholder="例如：南宁仓库2026Q3配送规划 / 南宁核心区店群排班画布"
          />
        </el-form-item>

        <el-form-item label="选择已有中心仓 / 起点">
          <div style="display: flex; gap: 8px; width: 100%;">
            <el-select
              v-model="selectedDepotId"
              placeholder="从起点库选用，或在下方直接自定义"
              clearable
              :loading="loadingDepots"
              style="flex: 1;"
              @change="onDepotSelected"
            >
              <el-option
                v-for="d in depotList"
                :key="d.id"
                :label="`${d.name} (${d.dc_code || '无编码'}) [${d.longitude}, ${d.latitude}]`"
                :value="d.id"
              />
            </el-select>
            <el-button 
              :icon="Refresh" 
              title="刷新起点列表" 
              :loading="loadingDepots"
              @click="fetchDepotsAndStores" 
            />
          </div>
          <div style="font-size: 11px; color: #94a3b8; margin-top: 4px; display: flex; justify-content: space-between; align-items: center;">
            <span>已载入 {{ depotList.length }} 个中心仓。如需添加，请在「起点管理」中维护。</span>
            <el-button link type="primary" size="small" style="font-size: 11px; padding: 0;" @click="goToDepotManage">
              前往起点管理 ➔
            </el-button>
          </div>
        </el-form-item>

        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px;">
          <el-form-item label="中心仓名称" required>
            <el-input v-model="newCanvasForm.depot_name" placeholder="例如：南宁中心仓" />
          </el-form-item>
          <el-form-item label="中心仓经度 (Lng)" required>
            <el-input-number
              v-model="newCanvasForm.depot_lng"
              :precision="6"
              :step="0.0001"
              style="width: 100%;"
            />
          </el-form-item>
          <el-form-item label="中心仓纬度 (Lat)" required>
            <el-input-number
              v-model="newCanvasForm.depot_lat"
              :precision="6"
              :step="0.0001"
              style="width: 100%;"
            />
          </el-form-item>
        </div>

        <el-form-item label="中心仓地址">
          <el-input v-model="newCanvasForm.depot_address" placeholder="详细地址信息（可选）" />
        </el-form-item>

        <el-form-item label="规划说明 / 备注">
          <el-input
            v-model="newCanvasForm.description"
            type="textarea"
            :rows="2"
            placeholder="记录本次规划的业务背景、目标或约束条件..."
          />
        </el-form-item>
      </el-form>
    </div>

    <!-- Step 2: Store Pool Selection -->
    <div v-show="createStep === 1" class="dialog-step-content">
      <!-- Mode Switch: System Store Master vs. Excel Import -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px;">
        <el-radio-group v-model="storeSelectMode" size="small">
          <el-radio-button label="system">
            从系统门店库挑选 (已选 {{ selectedStoreIds.size }} 家)
          </el-radio-button>
          <el-radio-button label="excel">
            从 Excel / CSV 导入 ({{ importedExcelStores.length ? `已解析 ${importedExcelStores.length} 家` : '上传文件' }})
          </el-radio-button>
        </el-radio-group>

        <div v-if="storeSelectMode === 'excel'" style="display: flex; gap: 8px;">
          <input
            ref="createExcelInput"
            type="file"
            accept=".xlsx,.xls,.csv"
            style="display: none;"
            @change="handleCreateExcelImport"
          />
          <el-button type="primary" size="small" :icon="Upload" @click="createExcelInput?.click()">
            选择并解析 Excel 文件
          </el-button>
          <el-button size="small" :icon="Download" @click="$emit('download-template')">
            下载标准模板
          </el-button>
        </div>
      </div>

      <!-- 坐标系选择与自动检测（仅 Excel 导入模式） -->
      <div v-if="storeSelectMode === 'excel'" class="coord-system-panel">
        <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 8px;">
          <span style="font-size: 13px; color: #64748b;">导入坐标系:</span>
          <el-radio-group v-model="createImportCoordSystem" size="small" :disabled="importedExcelStores.length === 0">
            <el-radio-button label="gcj02">GCJ-02（高德/腾讯）</el-radio-button>
            <el-radio-button label="wgs84">WGS-84（GPS 原始）</el-radio-button>
          </el-radio-group>
          <el-button
            size="small"
            :loading="createCoordDetecting"
            :disabled="importedExcelStores.length === 0"
            @click="runCreateCoordDetect"
          >
            自动检测坐标系
          </el-button>
        </div>
        <div v-if="createImportCoordSystem === 'wgs84'" style="font-size: 12px; color: #b45309; margin-top: 6px;">
          已按 WGS-84 解析：所有坐标已自动转换为高德 GCJ-02 后入库，地图展示与路网测算不再偏移。
        </div>
        <div v-if="createCoordDetectResult" :class="['coord-detect-result', createCoordDetectResult.system === 'wgs84' ? 'is-wgs' : 'is-gcj']">
          <strong>{{ createCoordDetectResult.system === 'wgs84' ? '检测结论：WGS-84（GPS 原始坐标）' : createCoordDetectResult.system === 'gcj02' ? '检测结论：GCJ-02（高德坐标）' : '检测结论：无法自动判断' }}</strong>
          <span style="margin-left: 8px;">{{ createCoordDetectResult.reason }}</span>
        </div>
      </div>

      <!-- Mode A: System Store Pool -->
      <div v-if="storeSelectMode === 'system'">
        <div class="store-filter-bar">
          <div class="store-filter-left">
            <el-input
              v-model="storeFilterKeyword"
              placeholder="搜索门店名称/编码/区域..."
              clearable
              size="small"
              style="width: 220px;"
            />
            <el-select
              v-model="storeFilterDistrict"
              placeholder="行政区划"
              clearable
              size="small"
              style="width: 130px;"
            >
              <el-option v-for="d in districtOptions" :key="d" :label="d" :value="d" />
            </el-select>
            <el-select
              v-model="storeFilterHomepot"
              placeholder="本/外埠"
              clearable
              size="small"
              style="width: 100px;"
            >
              <el-option label="本埠" :value="1" />
              <el-option label="外埠" :value="0" />
            </el-select>
          </div>
          <div class="store-filter-right">
            <el-button size="small" type="primary" plain @click="selectAllFilteredStores">
              全选当前筛选 ({{ filteredPoolStores.length }})
            </el-button>
            <el-button size="small" @click="selectedStoreIds.clear()">清空勾选</el-button>
          </div>
        </div>

        <el-table
          :data="filteredPoolStores"
          max-height="300px"
          stripe
          border
          size="small"
          row-key="id"
          style="width: 100%; margin-top: 8px;"
        >
          <el-table-column width="45" align="center">
            <template #default="{ row }">
              <el-checkbox
                :model-value="selectedStoreIds.has(row.id)"
                @change="(val) => toggleStoreCheck(row.id, val)"
              />
            </template>
          </el-table-column>
          <el-table-column prop="shop_code" label="门店编码" width="100" />
          <el-table-column prop="name" label="门店名称" min-width="140" show-overflow-tooltip />
          <el-table-column prop="district" label="行政区" width="90">
            <template #default="{ row }">
              <el-tag size="small" effect="plain">{{ row.district || '未划分' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="avg_loads" label="日均箱数" width="90" align="right">
            <template #default="{ row }">{{ row.avg_loads }} 箱</template>
          </el-table-column>
          <el-table-column prop="frequency" label="周频次" width="80" align="center">
            <template #default="{ row }">{{ row.frequency }} 次</template>
          </el-table-column>
          <el-table-column label="坐标" width="160">
            <template #default="{ row }">
              {{ formatCoord(row.longitude) }}, {{ formatCoord(row.latitude) }}
            </template>
          </el-table-column>
        </el-table>

        <div style="margin-top: 10px; font-size: 13px; color: #475569; display: flex; justify-content: space-between;">
          <span>
            已选择 <strong>{{ selectedStoreIds.size }}</strong> / {{ systemStores.length }} 家门店
          </span>
          <span style="color: #0284c7; font-weight: 600;">
            日均预估运量: {{ selectedTotalDemand }} 箱
          </span>
        </div>
      </div>

      <!-- Mode B: Excel Imported Stores Preview -->
      <div v-else>
        <div v-if="!importedExcelStores.length" style="padding: 40px 20px; text-align: center; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 8px;">
          <p style="font-size: 14px; color: #64748b; margin-bottom: 12px;">
            请上传包含门店经纬度、日均箱数的 Excel/CSV 文件，支持自动识别历史店群与作业日排班信息
          </p>
          <el-button type="primary" :icon="Upload" @click="createExcelInput?.click()">
            点击上传 Excel 文件
          </el-button>
        </div>

        <div v-else>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-size: 12px; color: #059669; font-weight: 600;">
              ✅ 成功解析 {{ importedExcelStores.length }} 家门店
              <span v-if="importedHasSchedule" style="color: #0284c7; margin-left: 8px;">
                (已识别到全周排班作业日方案)
              </span>
              <span v-if="importedHasCluster" style="color: #d97706; margin-left: 8px;">
                (已识别到店群划分)
              </span>
            </span>
            <el-button size="small" type="danger" link @click="clearExcelImport">
              清空重新上传
            </el-button>
          </div>

          <el-table
            :data="importedExcelStores"
            max-height="300px"
            stripe
            border
            size="small"
            style="width: 100%;"
          >
            <el-table-column prop="shop_code" label="门店编码" width="100" />
            <el-table-column prop="name" label="门店名称" min-width="130" show-overflow-tooltip />
            <el-table-column prop="district" label="行政区" width="85" />
            <el-table-column prop="avg_loads" label="日均箱数" width="85" align="right">
              <template #default="{ row }">{{ row.avg_loads }} 箱</template>
            </el-table-column>
            <el-table-column prop="delivery_days_str" label="排班作业日" min-width="110">
              <template #default="{ row }">
                <el-tag v-if="row.delivery_days_str" size="small" type="success">
                  {{ row.delivery_days_str }}
                </el-tag>
                <span v-else style="color: #94a3b8; font-size: 11px;">未指定</span>
              </template>
            </el-table-column>
            <el-table-column prop="cluster_id" label="所属店群" width="90" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.cluster_id !== undefined && row.cluster_id !== null" size="small" type="warning">
                  店群 {{ Number(row.cluster_id) + 1 }}
                </el-tag>
                <span v-else style="color: #94a3b8; font-size: 11px;">未指定</span>
              </template>
            </el-table-column>
            <el-table-column label="坐标" width="150">
              <template #default="{ row }">
                {{ formatCoord(row.lng) }}, {{ formatCoord(row.lat) }}
              </template>
            </el-table-column>
          </el-table>

          <div style="margin-top: 10px; font-size: 13px; color: #475569; display: flex; justify-content: space-between;">
            <span>已导入 <strong>{{ importedExcelStores.length }}</strong> 家规划门店</span>
            <span style="color: #0284c7; font-weight: 600;">
              日均总运量: {{ importedTotalDemand }} 箱
            </span>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 12px; color: #94a3b8;">
          创建后将在该画布内自动开启 V1 版本
        </span>
        <div>
          <el-button v-if="createStep > 0" @click="createStep--">上一步</el-button>
          <el-button v-if="createStep === 0" type="primary" @click="goToStep2">
            下一步：选择规划门店
          </el-button>
          <el-button
            v-if="createStep === 1"
            type="primary"
            :loading="creating"
            @click="submitCreateCanvas"
          >
            🚀 创建画布并进入
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh, Upload, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { canvasApi, depotApi, storeApi } from '../../../api/client.js'
import { parseFileUniversal } from '../../../utils/excelImport.js'
import { detectCoordinateSystemByAddress } from '../../../utils/coordSystem.js'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'created', 'download-template'])
const router = useRouter()

const createStep = ref(0)
const creating = ref(false)
const loadingDepots = ref(false)

const depotList = ref([])
const systemStores = ref([])
const selectedDepotId = ref(null)

const storeSelectMode = ref('system')
const selectedStoreIds = reactive(new Set())
const storeFilterKeyword = ref('')
const storeFilterDistrict = ref('')
const storeFilterHomepot = ref('')

const importedExcelStores = ref([])
const createExcelInput = ref(null)

// ---- 坐标系选择与自动检测（系统内部统一 GCJ-02，WGS-84 在解析时自动转换） ----
const createImportCoordSystem = ref('gcj02')
const createLastRawFile = ref(null)
const createCoordDetecting = ref(false)
const createCoordDetectResult = ref(null)

const newCanvasForm = reactive({
  name: '',
  dc_code: '',
  depot_name: '南宁中心仓',
  depot_lng: 108.36654,
  depot_lat: 22.81700,
  depot_address: '广西南宁市物流集散中心',
  description: '',
})

const formatCoord = (num) => {
  if (num === null || num === undefined) return '--'
  return Number(num).toFixed(4)
}

const goToDepotManage = () => {
  emit('update:modelValue', false)
  router.push('/config/depot')
}

const districtOptions = computed(() => {
  const set = new Set()
  systemStores.value.forEach((s) => {
    if (s.district) set.add(s.district)
  })
  return Array.from(set)
})

const filteredPoolStores = computed(() => {
  return systemStores.value.filter((s) => {
    const kw = storeFilterKeyword.value.toLowerCase().trim()
    const matchKw =
      !kw ||
      s.name?.toLowerCase().includes(kw) ||
      s.shop_code?.toLowerCase().includes(kw) ||
      s.district?.toLowerCase().includes(kw)
    const matchDistrict = !storeFilterDistrict.value || s.district === storeFilterDistrict.value
    const matchHomepot =
      storeFilterHomepot.value === '' ||
      storeFilterHomepot.value === null ||
      s.is_homepot === storeFilterHomepot.value
    return matchKw && matchDistrict && matchHomepot
  })
})

const selectedTotalDemand = computed(() => {
  let sum = 0
  systemStores.value.forEach((s) => {
    if (selectedStoreIds.has(s.id)) {
      sum += Number(s.avg_loads || 10)
    }
  })
  return Math.round(sum)
})

const importedTotalDemand = computed(() => {
  return Math.round(importedExcelStores.value.reduce((acc, s) => acc + (Number(s.avg_loads) || 10), 0))
})

const importedHasSchedule = computed(() => {
  return importedExcelStores.value.some((s) => s.delivery_days_str || s.schedule_day)
})

const importedHasCluster = computed(() => {
  return importedExcelStores.value.some((s) => s.cluster_id !== undefined && s.cluster_id !== null)
})

const fetchDepotsAndStores = async () => {
  loadingDepots.value = true
  try {
    const [depots, stores] = await Promise.all([
      depotApi.list(),
      storeApi.list(),
    ])
    depotList.value = depots || []
    systemStores.value = stores || []
  } catch (err) {
    console.warn('Failed to load depots or stores:', err)
  } finally {
    loadingDepots.value = false
  }
}

const initWizard = async () => {
  createStep.value = 0
  storeSelectMode.value = 'system'
  importedExcelStores.value = []
  createLastRawFile.value = null
  createCoordDetectResult.value = null
  createImportCoordSystem.value = 'gcj02'
  
  await fetchDepotsAndStores()

  const defaultDepot = depotList.value.find((d) => d.is_default) || depotList.value[0]
  if (defaultDepot) {
    selectedDepotId.value = defaultDepot.id
    newCanvasForm.dc_code = defaultDepot.dc_code || ''
    newCanvasForm.depot_name = defaultDepot.name || '中心仓'
    newCanvasForm.depot_lng = Number(defaultDepot.longitude)
    newCanvasForm.depot_lat = Number(defaultDepot.latitude)
    newCanvasForm.depot_address = defaultDepot.address || ''
    newCanvasForm.name = `${defaultDepot.name}规划画布-${new Date().getMonth() + 1}月${new Date().getDate()}日`
  } else {
    selectedDepotId.value = null
    newCanvasForm.name = `南宁仓库规划画布-${new Date().getMonth() + 1}月${new Date().getDate()}日`
    newCanvasForm.depot_name = '南宁中心仓'
    newCanvasForm.depot_lng = 108.36654
    newCanvasForm.depot_lat = 22.81700
    newCanvasForm.depot_address = '广西南宁市物流集散中心'
  }
  newCanvasForm.description = '针对配送门店的一体化店群、排班与多车型路径规划'
  selectedStoreIds.clear()

  if (systemStores.value.length) {
    systemStores.value.slice(0, 100).forEach((s) => selectedStoreIds.add(s.id))
  }
}

watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      initWizard()
    }
  }
)

const onDepotSelected = (id) => {
  if (!id) return
  const d = depotList.value.find((item) => item.id === id)
  if (d) {
    newCanvasForm.dc_code = d.dc_code || ''
    newCanvasForm.depot_name = d.name || '中心仓'
    newCanvasForm.depot_lng = Number(d.longitude)
    newCanvasForm.depot_lat = Number(d.latitude)
    newCanvasForm.depot_address = d.address || ''
    newCanvasForm.name = `${d.name}配送规划画布`

    const matchedStores = systemStores.value.filter((s) => s.dc_code === d.dc_code || s.warehouse_name === d.name)
    if (matchedStores.length > 0) {
      selectedStoreIds.clear()
      matchedStores.forEach((s) => selectedStoreIds.add(s.id))
      ElMessage.info(`已切换至「${d.name}」，并为您预选关联的 ${matchedStores.length} 家门店`)
    }
  }
}

const goToStep2 = () => {
  if (!newCanvasForm.name.trim()) {
    ElMessage.warning('请输入画布名称')
    return
  }
  if (!newCanvasForm.depot_lng || !newCanvasForm.depot_lat) {
    ElMessage.warning('请输入有效的中心仓经纬度')
    return
  }
  createStep.value = 1
}

const toggleStoreCheck = (id, checked) => {
  if (checked) {
    selectedStoreIds.add(id)
  } else {
    selectedStoreIds.delete(id)
  }
}

const selectAllFilteredStores = () => {
  filteredPoolStores.value.forEach((s) => selectedStoreIds.add(s.id))
}

// 解析结果落地：更新门店列表并回填中心仓信息（仅首次/空值时回填，不覆盖用户输入）
const applyExcelPoints = (points) => {
  importedExcelStores.value = points

  const firstPoint = points[0]
  if (firstPoint.warehouse_name && (!newCanvasForm.depot_name || newCanvasForm.depot_name === '中心仓')) {
    newCanvasForm.depot_name = firstPoint.warehouse_name
  }
  if (firstPoint.dc_code && !newCanvasForm.dc_code) {
    newCanvasForm.dc_code = firstPoint.dc_code
  }
  if (firstPoint.warehouse_lon && firstPoint.warehouse_lat) {
    newCanvasForm.depot_lng = Number(firstPoint.warehouse_lon)
    newCanvasForm.depot_lat = Number(firstPoint.warehouse_lat)
  }
}

// 切换坐标系后，用原始文件重新解析，保证门店坐标始终为高德 GCJ-02
watch(createImportCoordSystem, async (sys) => {
  createCoordDetectResult.value = null
  const rawFile = createLastRawFile.value
  if (!rawFile) return
  try {
    const { points } = await parseFileUniversal(rawFile, { coordSystem: sys })
    if (points && points.length) {
      applyExcelPoints(points)
      if (sys === 'wgs84') {
        ElMessage.success(`已按 WGS-84 解析并转换为高德坐标（共 ${points.length} 条）`)
      }
    }
  } catch (err) {
    ElMessage.error('重新解析失败: ' + (err.message || err))
  }
})

const runCreateCoordDetect = async () => {
  if (importedExcelStores.value.length === 0) return
  createCoordDetecting.value = true
  createCoordDetectResult.value = null
  try {
    const result = await detectCoordinateSystemByAddress(importedExcelStores.value, { sampleSize: 5 })
    createCoordDetectResult.value = result
    if (result.system !== 'unknown' && result.system !== createImportCoordSystem.value) {
      ElMessage.warning(`检测到数据为 ${result.system === 'wgs84' ? 'WGS-84（GPS 原始）' : 'GCJ-02（高德）'}，已自动切换导入坐标系并重新解析`)
      createImportCoordSystem.value = result.system // watch 会自动重新解析
    } else if (result.system !== 'unknown') {
      ElMessage.success('检测结果与当前选择一致，无需调整')
    }
  } catch (err) {
    ElMessage.error('坐标系检测失败: ' + (err.message || err))
  } finally {
    createCoordDetecting.value = false
  }
}

// 清空已解析的导入数据（同时丢弃原始文件与检测结论，避免切换坐标系复活旧文件）
const clearExcelImport = () => {
  importedExcelStores.value = []
  createLastRawFile.value = null
  createCoordDetectResult.value = null
  createImportCoordSystem.value = 'gcj02'
}

const handleCreateExcelImport = async (e) => {
  const file = e.target.files?.[0]
  if (!file) return

  try {
    const { points, warnings } = await parseFileUniversal(file, { coordSystem: createImportCoordSystem.value })
    if (!points || !points.length) {
      ElMessage.error('未能识别有效门店数据，请检查经纬度与表头')
      return
    }

    if (warnings && warnings.length) {
      ElMessage.warning(`解析提示: ${warnings[0]}`)
    }

    createLastRawFile.value = file
    createCoordDetectResult.value = null
    applyExcelPoints(points)
    ElMessage.success(`成功解析并载入 ${points.length} 家门店数据`)
  } catch (err) {
    ElMessage.error(`Excel解析失败: ${err.message || err}`)
  } finally {
    if (e.target) e.target.value = ''
  }
}

const submitCreateCanvas = async () => {
  let chosenStores = []
  if (storeSelectMode.value === 'excel') {
    if (!importedExcelStores.value.length) {
      ElMessage.warning('请先选择并解析包含门店数据的 Excel 文件')
      return
    }
    chosenStores = importedExcelStores.value.map((s) => ({
      shop_code: s.shop_code || '',
      name: s.name || '',
      lng: Number(s.lng),
      lat: Number(s.lat),
      avg_loads: Number(s.avg_loads || 10),
      frequency: Number(s.frequency || 1),
      is_homepot: Number(s.is_homepot ?? 0),
      district: s.district || '',
      address: s.address || '',
      cluster_id: s.cluster_id !== undefined && s.cluster_id !== null ? Number(s.cluster_id) : undefined,
      delivery_days_str: s.delivery_days_str || undefined,
      schedule_day: s.schedule_day || s.delivery_days_str || undefined,
      store_is_need_dist: true,
      available_truck: s.available_truck || '',
      service_time: Number(s.service_time || 0.5),
    }))
  } else {
    if (selectedStoreIds.size < 2) {
      ElMessage.warning('请至少勾选 2 家门店参与规划')
      return
    }
    chosenStores = systemStores.value
      .filter((s) => selectedStoreIds.has(s.id))
      .map((s) => ({
        id: s.id,
        shop_code: s.shop_code,
        name: s.name,
        lng: Number(s.longitude),
        lat: Number(s.latitude),
        avg_loads: Number(s.avg_loads || 10),
        frequency: Number(s.frequency || 1),
        is_homepot: Number(s.is_homepot ?? 0),
        district: s.district || '',
        address: s.address || '',
        store_is_need_dist: s.store_is_need_dist ?? true,
        available_truck: s.available_truck || '',
        service_time: Number(s.service_time || 0.5),
      }))
  }

  creating.value = true
  try {
    const payload = {
      name: newCanvasForm.name.trim(),
      dc_code: newCanvasForm.dc_code || undefined,
      depot_name: newCanvasForm.depot_name,
      depot_lng: Number(newCanvasForm.depot_lng),
      depot_lat: Number(newCanvasForm.depot_lat),
      depot_address: newCanvasForm.depot_address,
      description: newCanvasForm.description,
      points: chosenStores,
      algorithm_configs: {
        clustering_algorithm: 'kmeans',
        clustering_k: Math.max(3, Math.min(12, Math.ceil(chosenStores.length / 25))),
        minZoneSize: 5,
        maxZoneSize: 40,
      },
    }

    const createdCanvas = await canvasApi.create(payload)
    ElMessage.success(`🎉 规划画布「${createdCanvas.name}」创建成功！`)
    emit('update:modelValue', false)
    emit('created', createdCanvas)
    router.push(`/canvas/workspace/${createdCanvas.canvas_id}`)
  } catch (err) {
    ElMessage.error(`创建画布失败: ${err.message}`)
  } finally {
    creating.value = false
  }
}
</script>

<style scoped>
.dialog-step-content {
  padding: 10px 4px;
}

.store-filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.store-filter-left {
  display: flex;
  gap: 8px;
  align-items: center;
}

.store-filter-right {
  display: flex;
  gap: 8px;
}

.coord-system-panel {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 14px;
  margin: 10px 0 8px;
  background: #fbfdff;
}

.coord-detect-result {
  font-size: 12px;
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  line-height: 1.5;
}

.coord-detect-result.is-wgs {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fcd34d;
}

.coord-detect-result.is-gcj {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}
</style>
