<template>
  <div class="store-manage-container">
    <!-- Top Statistics Banner -->
    <div class="stats-row">
      <StatCard
        layout="vertical"
        label="总门店数"
        :value="stores.length"
        unit="家"
        theme="blue"
      />
      <StatCard
        layout="vertical"
        label="本埠 / 外埠门店"
        theme="green"
      >
        <template #value>
          {{ homepotCount }} <span class="stat-unit">/ {{ stores.length - homepotCount }} 家</span>
        </template>
      </StatCard>
      <StatCard
        layout="vertical"
        label="覆盖仓库数"
        :value="warehouseOptions.length"
        unit="个仓库"
        theme="amber"
      />
      <StatCard
        layout="vertical"
        label="日均总需求量"
        :value="totalAvgLoads.toLocaleString()"
        unit="箱"
        theme="purple"
      />
    </div>

    <!-- Main Content Card -->
    <el-card shadow="never" class="main-card">
      <!-- Action & Filter Bar -->
      <div class="toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索门店名称 / 编号 / 行政区 / 仓库..."
            clearable
            :prefix-icon="Search"
            style="width: 260px"
          />
          <el-select v-model="filterWarehouse" placeholder="所有所属仓库(DC)" clearable style="width: 180px" @change="filterCluster = null">
            <el-option v-for="w in warehouseOptions" :key="w.code" :label="w.label" :value="w.code" />
          </el-select>
          <el-select v-model="filterCluster" placeholder="所有所属店群" clearable style="width: 140px">
            <el-option v-for="c in clusterOptions" :key="c" :label="`店群 #${c}`" :value="c" />
          </el-select>
          <el-select v-model="filterDistrict" placeholder="所有行政区" clearable style="width: 140px">
            <el-option v-for="d in districtOptions" :key="d" :label="d" :value="d" />
          </el-select>
          <el-select v-model="filterHomepot" placeholder="全部属性" clearable style="width: 120px">
            <el-option label="本埠门店" :value="1" />
            <el-option label="外埠门店" :value="0" />
          </el-select>
          <el-select v-model="filterFrequency" placeholder="全部频次" clearable style="width: 120px">
            <el-option v-for="f in [1, 2, 3, 4, 5, 6, 7]" :key="f" :label="`每周 ${f} 次`" :value="f" />
          </el-select>
        </div>

        <div class="toolbar-right">
          <el-button type="primary" :icon="Plus" @click="openAddDialog">新增门店</el-button>
          <el-button type="success" :icon="Upload" @click="openImportDialog">Excel/CSV 导入</el-button>
          <el-button :icon="Download" @click="exportStoresToCSV">导出数据</el-button>
          <el-button :icon="Refresh" @click="fetchStores">刷新</el-button>
          <el-popconfirm title="确定要清空全部门店数据吗？" @confirm="handleClearAll">
            <template #reference>
              <el-button type="danger" plain :icon="Delete">清空全部</el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>

      <!-- Table View -->
      <el-table
        :data="paginatedStores"
        v-loading="loading"
        stripe
        border
        style="width: 100%; margin-top: 16px;"
        max-height="calc(100vh - 350px)"
      >
        <el-table-column type="index" label="序号" width="60" align="center" :index="indexMethod" />
        <el-table-column prop="shop_code" label="门店编号" width="110" sortable>
          <template #default="{ row }">
            <span class="font-mono">{{ row.shop_code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="门店名称" min-width="160" show-overflow-tooltip sortable />
        <el-table-column prop="dc_code" label="所属仓库" width="130" show-overflow-tooltip sortable>
          <template #default="{ row }">
            <el-tag size="small" type="info" effect="plain" style="font-weight: 600; font-family: monospace;">
              🏬 {{ row.dc_code || '9050' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="cluster_center_id" label="所属店群" width="110" align="center" sortable>
          <template #default="{ row }">
            <el-tag v-if="row.cluster_center_id !== null && row.cluster_center_id !== undefined" size="small" type="success" effect="light">
              店群 #{{ row.cluster_center_id }}
            </el-tag>
            <span v-else style="color: #94a3b8; font-size: 12px;">未归属</span>
          </template>
        </el-table-column>
        <el-table-column prop="district" label="行政区划" width="110">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.district || '未划分' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="longitude" label="经度" width="110" align="right">
          <template #default="{ row }">{{ Number(row.longitude).toFixed(5) }}</template>
        </el-table-column>
        <el-table-column prop="latitude" label="纬度" width="110" align="right">
          <template #default="{ row }">{{ Number(row.latitude).toFixed(5) }}</template>
        </el-table-column>
        <el-table-column prop="avg_loads" label="日均箱数" width="110" align="right" sortable>
          <template #default="{ row }">
            <span class="font-semibold">{{ row.avg_loads }} 箱</span>
          </template>
        </el-table-column>
        <el-table-column prop="frequency" label="周频次" width="90" align="center" sortable>
          <template #default="{ row }">
            <el-tag :type="row.frequency >= 3 ? 'danger' : (row.frequency >= 2 ? 'warning' : 'info')" size="small">
              {{ row.frequency }} 次/周
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_homepot" label="属性" width="85" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_homepot === 1 ? 'success' : 'info'" size="small">
              {{ row.is_homepot === 1 ? '本埠' : '外埠' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="service_time" label="卸货耗时" width="95" align="center">
          <template #default="{ row }">
            <span>{{ Math.round((row.service_time || 0.65) * 60) }} 分钟</span>
          </template>
        </el-table-column>
        <el-table-column prop="available_truck" label="指定车型" width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.available_truck || '不限车型' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="address" label="地址" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="140" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-popconfirm title="确定删除此门店？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button type="danger" link size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100, 200, 500]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="filteredStores.length"
        />
      </div>
    </el-card>

    <!-- Dialog 1: Add/Edit Store -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑门店数据' : '新增门店'"
      width="680px"
      destroy-on-close
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="110px" label-position="right">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="门店编号" prop="shop_code">
              <el-input v-model="form.shop_code" :disabled="isEdit" placeholder="例如: 1008" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="门店名称" prop="name">
              <el-input v-model="form.name" placeholder="例如: 南宁西乡塘店" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="部门/战区ID">
              <el-input v-model="form.dept_id" placeholder="可选，例如 1008" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所属行政区">
              <el-input v-model="form.district" placeholder="例如: 青秀区、西乡塘区" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="门店经度" prop="longitude">
              <el-input-number v-model="form.longitude" :precision="6" :step="0.001" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="门店纬度" prop="latitude">
              <el-input-number v-model="form.latitude" :precision="6" :step="0.001" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="日均箱数" prop="avg_loads">
              <el-input-number v-model="form.avg_loads" :min="0" :step="5" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="周配送频次" prop="frequency">
              <el-select v-model="form.frequency" style="width: 100%">
                <el-option v-for="f in [1, 2, 3, 4, 5, 6, 7]" :key="f" :label="`每周 ${f} 次`" :value="f" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="本埠/外埠">
              <el-radio-group v-model="form.is_homepot">
                <el-radio :label="1">本埠门店</el-radio>
                <el-radio :label="0">外埠门店</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="卸货服务时间">
              <el-input-number v-model="form.service_time" :min="0.1" :max="5.0" :step="0.1" :precision="2" style="width: 120px" />
              <span style="margin-left: 8px; color: #64748b; font-size: 12px;">小时 ({{ Math.round((form.service_time || 0.65) * 60) }}分)</span>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="所属仓库 (DC)" prop="dc_code">
              <el-select v-model="form.dc_code" filterable allow-create default-first-option placeholder="选择或输入仓库编码(dc_code)" style="width: 100%" @change="onFormDcCodeChange">
                <el-option v-for="d in depotList" :key="d.dc_code" :label="`🏬 ${d.dc_code}`" :value="d.dc_code" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所属店群编号">
              <el-input-number v-model="form.cluster_center_id" :min="0" :step="1" placeholder="例如: 1" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="可配送车型">
              <el-input v-model="form.available_truck" placeholder="空表示不限，例如: 4.2米厢车" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="战区分类">
              <el-input v-model="form.warzone" placeholder="例如: 桂南战区" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="详细地址">
          <el-input v-model="form.address" placeholder="详细门牌地址" />
        </el-form-item>

        <el-form-item label="配送使能">
          <el-switch v-model="form.store_is_need_dist" active-text="需要排班配送" inactive-text="不需配送(自提/电商)" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存数据</el-button>
      </template>
    </el-dialog>

    <!-- Dialog 2: Excel / CSV Import & Preview Modal -->
    <el-dialog
      v-model="importDialogVisible"
      title="从 Excel / CSV 批量导入门店"
      width="900px"
      destroy-on-close
    >
      <div class="import-content">
        <!-- Template Guide Banner -->
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-size: 13px; font-weight: 600; color: #1e293b;">
              📋 门店导入规范与标准模板
            </span>
            <div style="display: flex; gap: 8px;">
              <el-button size="small" type="primary" :icon="Download" @click="downloadTemplateExcel">
                下载标准 Excel (.xlsx) 模板
              </el-button>
              <el-button size="small" :icon="Document" @click="downloadTemplateCSV">
                下载 CSV 模板
              </el-button>
            </div>
          </div>
          <div style="font-size: 12px; color: #64748b; line-height: 1.6;">
            <strong>核心字段说明：</strong>
            <span style="color: #ef4444;">*门店编号</span>（唯一编码）、
            <span style="color: #ef4444;">*门店名称</span>、
            <span style="color: #ef4444;">*经度 / *纬度</span>（必填，高德/WGS84坐标）、
            <span>所属仓库</span>（如 南宁中心仓）、
            <span>所属店群</span>（如 1）、
            <span>日均箱数</span>（需求量）、
            <span>配送频次</span>（1-7次/周）、
            <span>是否本埠</span>（1=本埠, 0=外埠）、
            <span>行政区划</span>、
            <span>战区分类</span>、
            <span>指定车型</span>、
            <span>详细地址</span>。
          </div>
        </div>

        <div class="import-upload-zone">
          <el-upload
            drag
            action=""
            :auto-upload="false"
            :show-file-list="false"
            accept=".xlsx,.xls,.csv"
            @change="handleFileSelected"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将 Excel 或 CSV 文件拖拽到此处，或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 .xlsx, .xls, .csv 格式。系统已针对中英文表头（门店名称、经度、纬度、仓库、店群、箱数、频次、本埠等）进行全自动智能映射。
              </div>
            </template>
          </el-upload>
        </div>

        <div v-if="parsedList.length > 0" style="display: flex; justify-content: flex-end; align-items: center; margin: 16px 0 8px;">
          <span style="font-size: 13px; color: #64748b; margin-right: 12px;">导入模式:</span>
          <el-radio-group v-model="importMode" size="small">
            <el-radio-button label="overwrite">清空并覆盖现有数据</el-radio-button>
            <el-radio-button label="append">追加 / 更新现有数据</el-radio-button>
          </el-radio-group>
        </div>

        <!-- Preview Table -->
        <div v-if="parsedList.length > 0" class="import-preview-section">
          <div class="preview-header">
            <strong>数据解析预览 (共识别 {{ parsedList.length }} 条有效记录):</strong>
            <el-tag type="success" size="small">解析成功</el-tag>
          </div>
          <el-table :data="parsedList.slice(0, 10)" border stripe size="small" max-height="260px">
            <el-table-column prop="shop_code" label="门店编号" width="100" />
            <el-table-column prop="name" label="门店名称" width="140" show-overflow-tooltip />
            <el-table-column prop="warehouse_name" label="所属仓库" width="110" show-overflow-tooltip>
              <template #default="{ row }">{{ row.warehouse_name || '南宁中心仓' }}</template>
            </el-table-column>
            <el-table-column prop="cluster_center_id" label="店群" width="70" align="center">
              <template #default="{ row }">{{ row.cluster_center_id !== undefined && row.cluster_center_id !== null ? row.cluster_center_id : '-' }}</template>
            </el-table-column>
            <el-table-column prop="district" label="行政区" width="90" />
            <el-table-column prop="longitude" label="经度" width="95" />
            <el-table-column prop="latitude" label="纬度" width="95" />
            <el-table-column prop="avg_loads" label="箱数" width="70" />
            <el-table-column prop="frequency" label="频次" width="70" />
            <el-table-column prop="is_homepot" label="本埠" width="65">
              <template #default="{ row }">{{ row.is_homepot === 1 ? '是' : '否' }}</template>
            </el-table-column>
            <el-table-column prop="available_truck" label="车型" width="100" show-overflow-tooltip />
            <el-table-column prop="address" label="地址" show-overflow-tooltip />
          </el-table>
          <div v-if="parsedList.length > 10" style="font-size: 12px; color: #94a3b8; margin-top: 6px;">
            * 仅显示前 10 条预览记录，全部 {{ parsedList.length }} 条将一并提交入库。
          </div>
        </div>

        <div v-if="parseWarnings.length > 0" class="warning-box">
          <strong>数据校验提示 ({{ parseWarnings.length }} 条):</strong>
          <ul>
            <li v-for="(w, idx) in parseWarnings.slice(0, 5)" :key="idx">{{ w }}</li>
            <li v-if="parseWarnings.length > 5">... 等其余 {{ parseWarnings.length - 5 }} 条警告已忽略</li>
          </ul>
        </div>
      </div>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :disabled="parsedList.length === 0"
          :loading="importing"
          @click="submitBatchImport"
        >
          确认导入入库 ({{ parsedList.length }} 家)
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Plus, Refresh, Search, Upload, Download, Delete, UploadFilled, Document, ArrowDown } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as XLSX from 'xlsx'
import { parseFileUniversal } from '../../utils/excelImport.js'
import { storeApi, depotApi } from '../../api/client.js'
import StatCard from '../../components/common/StatCard.vue'

const stores = ref([])
const loading = ref(false)

// Filters
const searchKeyword = ref('')
const filterWarehouse = ref('')
const filterCluster = ref(null)
const filterDistrict = ref('')
const filterHomepot = ref('')
const filterFrequency = ref('')

const depotList = ref([])

// Pagination
const currentPage = ref(1)
const pageSize = ref(50)

// Dialogs
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)

const importDialogVisible = ref(false)
const parsedList = ref([])
const parseWarnings = ref([])
const importMode = ref('overwrite')
const importing = ref(false)

const form = ref({
  id: null,
  shop_code: '',
  name: '',
  dept_id: '',
  district: '',
  warzone: '',
  warehouse_name: '南宁中心仓',
  dc_code: '南宁中心仓',
  cluster_center_id: null,
  longitude: 108.318344,
  latitude: 22.846367,
  avg_loads: 20,
  frequency: 3,
  is_homepot: 0,
  store_is_need_dist: true,
  service_time: 0.65,
  available_truck: '',
  address: ''
})

const rules = {
  shop_code: [{ required: true, message: '请输入门店编号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入门店名称', trigger: 'blur' }],
  longitude: [{ required: true, message: '请输入经度', trigger: 'blur' }],
  latitude: [{ required: true, message: '请输入纬度', trigger: 'blur' }],
}

// Statistical Metrics
const homepotCount = computed(() => stores.value.filter(s => s.is_homepot === 1).length)
const totalAvgLoads = computed(() => Math.round(stores.value.reduce((acc, s) => acc + (Number(s.avg_loads) || 0), 0)))

// Distinct Warehouses for Dropdown
const warehouseOptions = computed(() => {
  const set = new Set()
  depotList.value.forEach(d => {
    if (d.dc_code) set.add(d.dc_code)
  })
  stores.value.forEach(s => {
    if (s.dc_code) set.add(s.dc_code)
  })
  if (set.size === 0) set.add('9050')
  return Array.from(set).sort().map(code => ({ code, label: `🏬 ${code}` }))
})

// Distinct Clusters for Dropdown
const clusterOptions = computed(() => {
  const set = new Set()
  let targetStores = stores.value
  if (filterWarehouse.value) {
    targetStores = targetStores.filter(s => (s.warehouse_name === filterWarehouse.value || s.dc_code === filterWarehouse.value))
  }
  targetStores.forEach(s => {
    if (s.cluster_center_id !== null && s.cluster_center_id !== undefined && s.cluster_center_id !== '') {
      set.add(Number(s.cluster_center_id))
    }
  })
  return Array.from(set).sort((a, b) => a - b)
})

// Distinct Districts for Dropdown
const districtOptions = computed(() => {
  const set = new Set()
  stores.value.forEach(s => {
    if (s.district && s.district.trim()) set.add(s.district.trim())
  })
  return Array.from(set).sort()
})

// Filtered List
const filteredStores = computed(() => {
  let list = stores.value
  if (filterWarehouse.value) {
    list = list.filter(s => (s.dc_code === filterWarehouse.value || s.warehouse_name === filterWarehouse.value))
  }
  if (filterCluster.value !== null && filterCluster.value !== undefined && filterCluster.value !== '') {
    list = list.filter(s => s.cluster_center_id === filterCluster.value)
  }
  if (filterDistrict.value) {
    list = list.filter(s => s.district === filterDistrict.value)
  }
  if (filterHomepot.value !== '' && filterHomepot.value !== null) {
    list = list.filter(s => s.is_homepot === filterHomepot.value)
  }
  if (filterFrequency.value) {
    list = list.filter(s => s.frequency === filterFrequency.value)
  }
  if (searchKeyword.value) {
    const q = searchKeyword.value.toLowerCase().trim()
    list = list.filter(
      s => (s.name && s.name.toLowerCase().includes(q)) ||
           (s.shop_code && s.shop_code.toLowerCase().includes(q)) ||
           (s.dc_code && s.dc_code.toLowerCase().includes(q)) ||
           (s.warehouse_name && s.warehouse_name.toLowerCase().includes(q)) ||
           (s.district && s.district.toLowerCase().includes(q)) ||
           (s.address && s.address.toLowerCase().includes(q))
    )
  }
  return list
})

// Paginated Table Data
const paginatedStores = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredStores.value.slice(start, start + pageSize.value)
})

const indexMethod = (index) => (currentPage.value - 1) * pageSize.value + index + 1

const fetchDepots = async () => {
  try {
    const data = await depotApi.list()
    depotList.value = data
  } catch (e) {}
}

const fetchStores = async () => {
  loading.value = true
  try {
    const data = await storeApi.list()
    stores.value = data
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    loading.value = false
  }
}

const onFormDcCodeChange = (val) => {
  const matched = depotList.value.find(d => d.dc_code === val)
  if (matched) {
    form.value.warehouse_name = matched.name
  }
}

const openAddDialog = () => {
  isEdit.value = false
  const defaultDepot = depotList.value.find(d => d.dc_code === filterWarehouse.value) || depotList.value[0]
  form.value = {
    id: null,
    shop_code: 'STORE_' + Math.floor(1000 + Math.random() * 9000),
    name: '',
    dept_id: '',
    district: '',
    warzone: '',
    dc_code: filterWarehouse.value || (defaultDepot?.dc_code || '9050'),
    warehouse_name: defaultDepot?.name || '南宁中心仓',
    cluster_center_id: null,
    longitude: 108.33,
    latitude: 22.82,
    avg_loads: 25,
    frequency: 3,
    is_homepot: 0,
    store_is_need_dist: true,
    service_time: 0.5,
    available_truck: '',
    address: ''
  }
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  isEdit.value = true
  const matchedDepot = depotList.value.find(d => d.dc_code === row.dc_code || d.name === row.warehouse_name)
  form.value = {
    ...row,
    dc_code: row.dc_code || (matchedDepot?.dc_code || '9050'),
    warehouse_name: row.warehouse_name || (matchedDepot?.name || '南宁中心仓')
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      if (isEdit.value) {
        await storeApi.update(form.value.id, form.value)
        ElMessage.success('门店信息更新成功')
      } else {
        await storeApi.create(form.value)
        ElMessage.success('新增门店成功')
      }
      dialogVisible.value = false
      fetchStores()
    } catch (err) {
      ElMessage.error(err.message)
    } finally {
      submitting.value = false
    }
  })
}

const handleDelete = async (id) => {
  try {
    await storeApi.delete(id)
    ElMessage.success('门店已删除')
    fetchStores()
  } catch (err) {
    ElMessage.error(err.message)
  }
}

const handleClearAll = async () => {
  try {
    await storeApi.clearAll()
    ElMessage.success('所有门店已清空')
    stores.value = []
    currentPage.value = 1
    await fetchStores()
  } catch (err) {
    ElMessage.error(err.message)
  }
}

// -------------------------------------------------------------
// Excel / CSV File Import Implementation
// -------------------------------------------------------------
const openImportDialog = () => {
  parsedList.value = []
  parseWarnings.value = []
  importDialogVisible.value = true
}

const handleFileSelected = async (fileObj) => {
  const rawFile = fileObj.raw
  if (!rawFile) return

  try {
    const { points, warnings } = await parseFileUniversal(rawFile)
    parseWarnings.value = warnings || []

    if (!points || points.length === 0) {
      ElMessage.warning(warnings[0] || '未在文件中识别到有效门店经纬度数据，请检查文件格式')
      return
    }

    parsedList.value = points
    ElMessage.success(`成功解析 ${parsedList.value.length} 家门店数据`)
  } catch (err) {
    ElMessage.error('文件解析失败: ' + (err.message || err))
  }
}

const submitBatchImport = async () => {
  if (parsedList.value.length === 0) return
  importing.value = true
  try {
    const payload = {
      stores: parsedList.value,
      mode: importMode.value
    }
    const result = await storeApi.batchCreate(payload)
    ElMessage.success(`导入成功！新增 ${result.inserted} 家，更新 ${result.updated} 家`)
    importDialogVisible.value = false
    fetchStores()
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    importing.value = false
  }
}

const handleTemplateDownload = (cmd) => {
  if (cmd === 'xlsx') {
    downloadTemplateExcel()
  } else {
    downloadTemplateCSV()
  }
}

const downloadTemplateExcel = () => {
  try {
    const wb = XLSX.utils.book_new()
    
    // Sheet 1: 门店导入数据表
    const headers = [
      '门店编号',
      '门店名称',
      '经度',
      '纬度',
      '所属仓库',
      '所属店群',
      '日均箱数',
      '周配送频次',
      '是否本埠',
      '行政区划',
      '战区分类',
      '指定车型',
      '卸货耗时_小时',
      '详细地址'
    ]

    const sampleData = [
      [
        '1008',
        '南宁津头店',
        108.335965,
        22.799882,
        '南宁中心仓',
        1,
        77,
        3,
        '本埠',
        '青秀区',
        '桂南战区',
        '4.2米厢车',
        0.65,
        '南宁市青秀区津头路1号'
      ],
      [
        '1022',
        '朝阳广场店',
        108.339847,
        22.823789,
        '南宁中心仓',
        1,
        36,
        3,
        '本埠',
        '兴宁区',
        '桂南战区',
        '4.2米厢车',
        0.65,
        '南宁市兴宁区朝阳路9号'
      ],
      [
        '1039',
        '柳州鱼峰店',
        109.428731,
        24.316892,
        '南宁中心仓',
        2,
        45,
        2,
        '外埠',
        '鱼峰区',
        '桂中战区',
        '4.2米厢车',
        0.8,
        '柳州市鱼峰区驾鹤路88号'
      ],
      [
        '1044',
        '桂林象山店',
        110.290123,
        25.273554,
        '桂林分仓',
        3,
        28,
        2,
        '外埠',
        '象山区',
        '桂北战区',
        '4.2米厢车',
        0.65,
        '桂林市象山区中山南路16号'
      ]
    ]

    const wsData = [headers, ...sampleData]
    const ws = XLSX.utils.aoa_to_sheet(wsData)

    // Set column widths
    ws['!cols'] = [
      { wch: 12 }, // 门店编号
      { wch: 16 }, // 门店名称
      { wch: 14 }, // 经度
      { wch: 14 }, // 纬度
      { wch: 14 }, // 所属仓库
      { wch: 10 }, // 所属店群
      { wch: 10 }, // 日均箱数
      { wch: 12 }, // 周配送频次
      { wch: 10 }, // 是否本埠
      { wch: 12 }, // 行政区划
      { wch: 12 }, // 战区分类
      { wch: 12 }, // 指定车型
      { wch: 14 }, // 卸货耗时
      { wch: 28 }  // 详细地址
    ]

    XLSX.utils.book_append_sheet(wb, ws, '门店维护导入表')

    // Sheet 2: 字段说明与枚举值
    const guideHeaders = ['字段名称', '是否必填', '示例值 / 枚举值', '说明']
    const guideData = [
      ['门店编号', '必填', '1008 或 STORE_001', '门店唯一主键编码'],
      ['门店名称', '必填', '南宁津头店', '门店全称或营业简称'],
      ['经度', '必填', '108.335965', '高德坐标系 GCJ-02 或 WGS84 经度'],
      ['纬度', '必填', '22.799882', '高德坐标系 GCJ-02 或 WGS84 纬度'],
      ['所属仓库', '选填', '9050 / 9130', '中心仓或所属仓库编码 (dc_code)'],
      ['所属店群', '选填', '1 / 2 / 3', '店群聚类编号 (整数)'],
      ['日均箱数', '选填', '35', '日均配送需求箱数 (整数或浮点数)'],
      ['周配送频次', '选填', '1 ~ 7', '每周配送次数 (建议1~7次)'],
      ['是否本埠', '选填', '1 / 0 / 本埠 / 外埠', '1或本埠表示本埠门店，0或外埠表示外埠门店'],
      ['行政区划', '选填', '青秀区 / 西乡塘区', '行政区域'],
      ['战区分类', '选填', '桂南战区 / 桂北战区', '业务所属大区/战区'],
      ['指定车型', '选填', '4.2米厢车', '如限制配送车型可填写，不限可留空'],
      ['卸货耗时_小时', '选填', '0.5', '卸货服务时间 (小时，0.5 即 30分钟)'],
      ['详细地址', '选填', '南宁市青秀区津头路1号', '门店实际道路与门牌号地址']
    ]

    const wsGuide = XLSX.utils.aoa_to_sheet([guideHeaders, ...guideData])
    wsGuide['!cols'] = [{ wch: 14 }, { wch: 10 }, { wch: 22 }, { wch: 40 }]
    XLSX.utils.book_append_sheet(wb, wsGuide, '填写规范说明')

    XLSX.writeFile(wb, '门店信息维护导入模板.xlsx')
    ElMessage.success('已成功生成并下载标准 Excel 导入模板！')
  } catch (err) {
    ElMessage.error('生成 Excel 模板失败: ' + err.message)
  }
}

const downloadTemplateCSV = () => {
  const headers = [
    '门店编号',
    '门店名称',
    '经度',
    '纬度',
    '所属仓库',
    '所属店群',
    '日均箱数',
    '周配送频次',
    '是否本埠',
    '行政区划',
    '战区分类',
    '指定车型',
    '卸货耗时_小时',
    '详细地址'
  ]
  const sampleRows = [
    '1008,南宁津头店,108.335965,22.799882,9050,1,77,3,本埠,青秀区,桂南战区,4.2米厢车,0.5,南宁市青秀区津头路1号',
    '1022,朝阳广场店,108.339847,22.823789,9050,1,36,3,本埠,兴宁区,桂南战区,4.2米厢车,0.5,南宁市兴宁区朝阳路9号',
    '1039,柳州鱼峰店,109.428731,24.316892,9050,2,45,2,外埠,鱼峰区,桂中战区,4.2米厢车,0.8,柳州市鱼峰区驾鹤路88号'
  ]
  const csvContent = '\uFEFF' + headers.join(',') + '\n' + sampleRows.join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '门店信息维护导入模板.csv'
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('已下载 CSV 导入模板！')
}

const exportStoresToCSV = () => {
  if (stores.value.length === 0) {
    ElMessage.warning('当前暂无可导出的门店数据')
    return
  }
  const headers = [
    'name',
    'lng',
    'lat',
    'dc_code',
    'cluster_id',
    'shop_code',
    'dept_id',
    'shop_name',
    'frequency',
    'dis_way',
    'is_homepot',
    'district',
    'warzone',
    'avg_loads',
    'address'
  ]
  const rows = filteredStores.value.map(s => [
    `"${s.name || ''}"`,
    s.longitude,
    s.latitude,
    `"${s.dc_code || '9050'}"`,
    s.cluster_center_id !== null && s.cluster_center_id !== undefined ? s.cluster_center_id : '',
    `"${s.shop_code || ''}"`,
    `"${s.dept_id || ''}"`,
    `"${s.name || ''}"`,
    s.frequency,
    `"${s.available_truck || ''}"`,
    s.is_homepot,
    `"${s.district || ''}"`,
    `"${s.warzone || ''}"`,
    s.avg_loads,
    `"${s.address || ''}"`
  ].join(','))

  const csvContent = '\uFEFF' + headers.join(',') + '\n' + rows.join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `门店基础数据导出_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success(`已导出 ${filteredStores.value.length} 家门店数据`)
}

onMounted(() => {
  fetchStores()
  fetchDepots()
})
</script>

<style scoped>
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.font-semibold {
  font-weight: 600;
  color: var(--text);
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.import-upload-zone {
  margin-bottom: 12px;
}

.import-preview-section {
  margin-top: 12px;
  background: #f8fafc;
  padding: 12px;
  border-radius: var(--radius-sm);
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.warning-box ul {
  margin: 4px 0 0 16px;
  padding: 0;
}
</style>
