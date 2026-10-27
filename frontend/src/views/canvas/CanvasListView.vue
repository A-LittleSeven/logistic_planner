<template>
  <div class="canvas-list-container">
    <!-- Header Summary Bar -->
    <AppPageHeader
      title="规划画布 (Planning Canvas)"
      subtitle="以中心仓为作用域的单次独立物流规划工作空间。支持店群分组、周排班均衡与多车型路线规划的全生命周期管理，支持增量版本演进与历史快照回溯。"
    >
      <template #actions>
        <el-button type="primary" :icon="Plus" @click="openCreateModal">
          新建规划画布
        </el-button>
        <el-button :icon="Download" @click="downloadImportTemplate">
          下载导入模板
        </el-button>
        <el-button :icon="Refresh" @click="fetchCanvases">刷新</el-button>
      </template>
    </AppPageHeader>

    <!-- Metrics Cards -->
    <div class="metrics-grid">
      <StatCard
        label="规划画布总数"
        :value="canvases.length"
        :icon="DataAnalysis"
        theme="blue"
      />
      <StatCard
        label="已完成路线规划"
        :value="routedCount"
        :icon="Compass"
        theme="green"
      />
      <StatCard
        label="排班规划中"
        :value="scheduledCount"
        :icon="Calendar"
        theme="amber"
      />
      <StatCard
        label="累计管理门店点"
        :value="totalStoresCount"
        :icon="Collection"
        theme="purple"
      />
    </div>

    <!-- Filter Bar -->
    <el-card shadow="never" class="filter-card">
      <div class="filter-bar">
        <div class="filter-left">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索画布名称 / 仓库名称 / 仓库编码..."
            clearable
            :prefix-icon="Search"
            style="width: 300px;"
          />
          <el-select
            v-model="filterStage"
            placeholder="规划阶段"
            clearable
            style="width: 150px;"
          >
            <el-option label="初始建库 (INIT)" value="INIT" />
            <el-option label="店群已规划 (CLUSTERED)" value="CLUSTERED" />
            <el-option label="排班已规划 (SCHEDULED)" value="SCHEDULED" />
            <el-option label="路线已规划 (ROUTED)" value="ROUTED" />
          </el-select>
        </div>
        <div class="filter-right">
          <el-radio-group v-model="viewMode" size="small">
            <el-radio-button label="card">卡片视图</el-radio-button>
            <el-radio-button label="table">列表视图</el-radio-button>
          </el-radio-group>
        </div>
      </div>
    </el-card>

    <!-- Canvas Cards View -->
    <div v-if="viewMode === 'card'" v-loading="loading" class="canvas-cards-grid">
      <div
        v-for="c in filteredCanvases"
        :key="c.canvas_id"
        class="canvas-card"
        @click="enterCanvas(c.canvas_id)"
      >
        <div class="card-header">
          <div class="card-title-row">
            <span class="card-title" :title="c.name">{{ c.name }}</span>
            <el-tag size="small" :type="getStageTagType(c.stage)" effect="dark">
              {{ getStageLabel(c.stage) }}
            </el-tag>
          </div>
          <div class="card-depot-info">
            <el-icon style="margin-right: 4px; color: #0284c7;"><OfficeBuilding /></el-icon>
            <span class="depot-name">{{ c.depot_name || '中心仓' }}</span>
            <span v-if="c.dc_code" class="dc-code">({{ c.dc_code }})</span>
            <span class="coords">[{{ formatCoord(c.depot_lng) }}, {{ formatCoord(c.depot_lat) }}]</span>
          </div>
        </div>

        <p class="card-desc">{{ c.description || '暂无描述信息' }}</p>

        <!-- Core KPI Mini Badges Ribbon -->
        <div class="card-kpi-ribbon">
          <div class="kpi-mini-badge" title="规划门店与周配送总箱数 (日均负载 × 配送频次)">
            <span class="kpi-icon" style="background: #e0f2fe; color: #0284c7;">🏪</span>
            <div class="kpi-text">
              <span class="kpi-val">{{ c.store_count }} <span class="kpi-unit">家</span></span>
              <span class="kpi-sub" v-if="c.total_loads">{{ c.total_loads }} 箱/周</span>
              <span class="kpi-sub" v-else>待排班运量</span>
            </div>
          </div>

          <div class="kpi-mini-badge" title="规划路线与总里程">
            <span class="kpi-icon" style="background: #f0fdf4; color: #16a34a;">🚚</span>
            <div class="kpi-text">
              <span class="kpi-val" :style="{ color: c.route_count ? '#16a34a' : '#475569' }">
                {{ c.route_count ? c.route_count + ' 条路线' : (c.cluster_count ? c.cluster_count + ' 个店群' : '未规划路线') }}
              </span>
              <span class="kpi-sub" v-if="c.total_distance">{{ c.total_distance }} km</span>
              <span class="kpi-sub" v-else-if="c.cluster_count">店群已分</span>
              <span class="kpi-sub" v-else>待求解</span>
            </div>
          </div>

          <div class="kpi-mini-badge" title="当前快照版本与演进历史">
            <span class="kpi-icon" style="background: #fef3c7; color: #d97706;">⚡</span>
            <div class="kpi-text">
              <span class="kpi-val version-text">V{{ c.current_version_number || 1 }}</span>
              <span class="kpi-sub">共 {{ c.version_count || 1 }} 个快照</span>
            </div>
          </div>
        </div>

        <div class="card-footer" @click.stop>
          <span class="update-time">更新于: {{ formatTime(c.updated_at) }}</span>
          <div class="card-actions">
            <el-button type="primary" size="small" @click="enterCanvas(c.canvas_id)">
              进入画布
            </el-button>
            <el-dropdown trigger="click" @command="(cmd) => handleCardAction(cmd, c)">
              <el-button size="small" :icon="More" circle />
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="clone">克隆分支 (What-If)</el-dropdown-item>
                  <el-dropdown-item command="edit">编辑基本信息</el-dropdown-item>
                  <el-dropdown-item command="delete" divided style="color: #ef4444;">
                    删除画布
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>

      <div v-if="!loading && filteredCanvases.length === 0" class="empty-state">
        <el-empty description="暂无匹配的规划画布，点击上方按钮新建一个吧" />
      </div>
    </div>

    <!-- Canvas Table View -->
    <el-card v-else shadow="never" class="table-card">
      <el-table
        :data="filteredCanvases"
        v-loading="loading"
        stripe
        border
        style="width: 100%"
      >
        <el-table-column prop="name" label="画布名称" min-width="180">
          <template #default="{ row }">
            <a class="table-link" @click="enterCanvas(row.canvas_id)">{{ row.name }}</a>
          </template>
        </el-table-column>
        <el-table-column label="关联中心仓" min-width="160">
          <template #default="{ row }">
            <div><strong>{{ row.depot_name || '中心仓' }}</strong></div>
            <div style="font-size: 11px; color: #64748b;">
              {{ formatCoord(row.depot_lng) }}, {{ formatCoord(row.depot_lat) }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="门店 / 周总箱数" min-width="130">
          <template #default="{ row }">
            <div style="font-weight: 600; color: #0f172a;">{{ row.store_count }} 家</div>
            <div style="font-size: 11px; color: #64748b;" v-if="row.total_loads">
              {{ row.total_loads }} 箱/周
            </div>
          </template>
        </el-table-column>
        <el-table-column label="规划路线 / 里程" min-width="150">
          <template #default="{ row }">
            <div v-if="row.route_count" style="color: #16a34a; font-weight: 600;">
              {{ row.route_count }} 条路线 ({{ row.total_distance }} km)
            </div>
            <div v-else-if="row.cluster_count" style="color: #0284c7; font-size: 12px;">
              {{ row.cluster_count }} 个店群已划分
            </div>
            <span v-else style="color: #94a3b8; font-size: 11px;">未规划路线</span>
          </template>
        </el-table-column>
        <el-table-column label="当前版本" width="110" align="center">
          <template #default="{ row }">
            <el-tag type="info" size="small">V{{ row.current_version_number }} (共{{ row.version_count }}版)</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="规划阶段" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="getStageTagType(row.stage)">
              {{ getStageLabel(row.stage) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="160">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="enterCanvas(row.canvas_id)">
              进入画布
            </el-button>
            <el-button type="success" link size="small" @click="handleCardAction('clone', row)">
              克隆
            </el-button>
            <el-button type="warning" link size="small" @click="handleCardAction('edit', row)">
              编辑
            </el-button>
            <el-button type="danger" link size="small" @click="handleCardAction('delete', row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Create Canvas Wizard Dialog Modal Component -->
    <CreateCanvasWizardDialog
      v-model="createDialogVisible"
      @created="fetchCanvases"
      @download-template="downloadImportTemplate"
    />

    <!-- Edit Canvas Modal -->
    <el-dialog v-model="editDialogVisible" title="编辑画布基础信息" width="500px">
      <el-form label-position="top" :model="editForm">
        <el-form-item label="画布名称" required>
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="中心仓名称">
          <el-input v-model="editForm.depot_name" />
        </el-form-item>
        <el-form-item label="描述与备注">
          <el-input v-model="editForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingEdit" @click="submitEditCanvas">保存修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Refresh,
  Search,
  More,
  DataAnalysis,
  Compass,
  Calendar,
  Collection,
  OfficeBuilding,
  Download,
} from '@element-plus/icons-vue'
import * as XLSX from 'xlsx'
import { canvasApi } from '../../api/client'
import CreateCanvasWizardDialog from './dialogs/CreateCanvasWizardDialog.vue'
import AppPageHeader from '../../components/common/AppPageHeader.vue'
import StatCard from '../../components/common/StatCard.vue'

const router = useRouter()

const loading = ref(false)
const canvases = ref([])
const searchKeyword = ref('')
const filterStage = ref('')
const viewMode = ref('card')

// Dialog states
const createDialogVisible = ref(false)
const editDialogVisible = ref(false)
const savingEdit = ref(false)

const editForm = reactive({
  canvas_id: '',
  name: '',
  depot_name: '',
  description: '',
})

// Metrics
const routedCount = computed(() => canvases.value.filter((c) => c.stage === 'ROUTED').length)
const scheduledCount = computed(() => canvases.value.filter((c) => c.stage === 'SCHEDULED').length)
const totalStoresCount = computed(() => canvases.value.reduce((acc, c) => acc + (c.store_count || 0), 0))

// Filtered Canvases
const filteredCanvases = computed(() => {
  return canvases.value.filter((c) => {
    const kw = searchKeyword.value.trim().toLowerCase()
    const matchKw =
      !kw ||
      c.name?.toLowerCase().includes(kw) ||
      c.depot_name?.toLowerCase().includes(kw) ||
      c.dc_code?.toLowerCase().includes(kw)
    const matchStage = !filterStage.value || c.stage === filterStage.value
    return matchKw && matchStage
  })
})

const formatCoord = (num) => {
  if (num === null || num === undefined) return '--'
  return Number(num).toFixed(4)
}

const formatTime = (timeStr) => {
  if (!timeStr) return '--'
  const date = new Date(timeStr)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

const getStageLabel = (stage) => {
  switch (stage) {
    case 'INIT':
      return '初始建库'
    case 'CLUSTERED':
      return '店群已规划'
    case 'SCHEDULED':
      return '排班已规划'
    case 'ROUTED':
      return '路线已规划'
    case 'FINALIZED':
      return '方案已定稿'
    default:
      return stage || '规划中'
  }
}

const getStageTagType = (stage) => {
  switch (stage) {
    case 'INIT':
      return 'info'
    case 'CLUSTERED':
      return 'warning'
    case 'SCHEDULED':
      return ''
    case 'ROUTED':
    case 'FINALIZED':
      return 'success'
    default:
      return 'info'
  }
}

const downloadImportTemplate = () => {
  const sampleData = [
    {
      '门店编号': 'STORE_1001',
      '门店名称': '南宁兴宁万达店',
      '所属仓库': '南宁中心仓',
      '所属店群': 1,
      '所属行政区': '兴宁区',
      '计划配送作业日': '周一,周三,周五',
      '周配送频次': 3,
      '日均箱数': 45,
      '本外埠': '本埠',
      '经度': 108.324838,
      '纬度': 22.846567,
      '卸货耗时_小时': 0.65,
      '指定车型': '4.2米厢车',
      '详细地址': '南宁市兴宁区东州路',
    },
    {
      '门店编号': 'STORE_1002',
      '门店名称': '南宁东葛路店',
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
      '详细地址': '南宁市青秀区东葛路',
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
      '经度': 109.402860,
      '纬度': 24.304495,
      '卸货耗时_小时': 0.9,
      '指定车型': '4.2米厢车',
      '详细地址': '柳州市鱼峰区驾鹤路',
    },
  ]

  const wb = XLSX.utils.book_new()
  const ws = XLSX.utils.json_to_sheet(sampleData)
  ws['!cols'] = [
    { wch: 14 },
    { wch: 18 },
    { wch: 14 },
    { wch: 10 },
    { wch: 12 },
    { wch: 18 },
    { wch: 12 },
    { wch: 10 },
    { wch: 10 },
    { wch: 12 },
    { wch: 12 },
    { wch: 14 },
    { wch: 14 },
    { wch: 24 },
  ]
  XLSX.utils.book_append_sheet(wb, ws, '规划门店导入模板')
  XLSX.writeFile(wb, '规划画布门店导入标准模板.xlsx')
  ElMessage.success('已成功下载规划画布门店导入标准模板')
}

const fetchCanvases = async () => {
  loading.value = true
  try {
    const data = await canvasApi.list()
    canvases.value = data || []
  } catch (err) {
    ElMessage.error(`获取画布列表失败: ${err.message}`)
  } finally {
    loading.value = false
  }
}

const enterCanvas = (canvasId) => {
  router.push(`/canvas/workspace/${canvasId}`)
}

const openCreateModal = () => {
  createDialogVisible.value = true
}

const handleCardAction = async (command, canvasItem) => {
  if (command === 'clone') {
    try {
      await ElMessageBox.confirm(
        `确定要克隆画布「${canvasItem.name}」吗？系统将复制当前最新版本快照，建立独立的方案分支。`,
        '克隆规划分支',
        { confirmButtonText: '立即克隆', cancelButtonText: '取消', type: 'info' }
      )
      const cloned = await canvasApi.clone(canvasItem.canvas_id, {
        new_name: `${canvasItem.name} (分支副本)`,
      })
      ElMessage.success(`已成功克隆分支「${cloned.name}」`)
      fetchCanvases()
    } catch (e) {
      if (e !== 'cancel') ElMessage.error(`克隆失败: ${e.message}`)
    }
  } else if (command === 'edit') {
    editForm.canvas_id = canvasItem.canvas_id
    editForm.name = canvasItem.name
    editForm.depot_name = canvasItem.depot_name || ''
    editForm.description = canvasItem.description || ''
    editDialogVisible.value = true
  } else if (command === 'delete') {
    try {
      await ElMessageBox.confirm(
        `确定要删除画布「${canvasItem.name}」及其所有演进版本历史吗？此操作无法撤销。`,
        '警告',
        { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
      )
      await canvasApi.delete(canvasItem.canvas_id)
      ElMessage.success('画布已删除')
      fetchCanvases()
    } catch (e) {
      if (e !== 'cancel') ElMessage.error(`删除失败: ${e.message}`)
    }
  }
}

const submitEditCanvas = async () => {
  if (!editForm.name.trim()) {
    ElMessage.warning('画布名称不能为空')
    return
  }
  savingEdit.value = true
  try {
    await canvasApi.update(editForm.canvas_id, {
      name: editForm.name.trim(),
      depot_name: editForm.depot_name.trim() || undefined,
      description: editForm.description || undefined,
    })
    ElMessage.success('基础信息修改成功')
    editDialogVisible.value = false
    fetchCanvases()
  } catch (err) {
    ElMessage.error(`修改失败: ${err.message}`)
  } finally {
    savingEdit.value = false
  }
}

onMounted(() => {
  fetchCanvases()
})
</script>

<style scoped>
.canvas-list-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.filter-card {
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.filter-left {
  display: flex;
  gap: 12px;
  align-items: center;
}

.canvas-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.canvas-card {
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  padding: 16px;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.canvas-card:hover {
  transform: translateY(-2px);
  border-color: #38bdf8;
  box-shadow: 0 8px 20px rgba(56, 189, 248, 0.12);
}

.card-header {
  margin-bottom: 10px;
}

.card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 6px;
}

.card-title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-depot-info {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: #475569;
  flex-wrap: wrap;
  gap: 4px;
}

.depot-name {
  font-weight: 600;
  color: #0f172a;
}

.dc-code {
  color: #64748b;
}

.coords {
  color: #94a3b8;
  font-size: 11px;
}

.card-desc {
  font-size: 12px;
  color: #64748b;
  line-height: 1.4;
  margin: 0 0 14px 0;
  height: 34px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* KPI Mini Badges Ribbon */
.card-kpi-ribbon {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 14px;
}

.kpi-mini-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.kpi-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}

.kpi-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.kpi-val {
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kpi-val.version-text {
  color: #0284c7;
  font-family: monospace;
  font-size: 13px;
}

.kpi-unit {
  font-size: 10px;
  font-weight: normal;
  color: #64748b;
}

.kpi-sub {
  font-size: 10px;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 1px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
  font-size: 11px;
}

.update-time {
  color: #94a3b8;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.table-card {
  border-radius: 8px;
}

.table-link {
  color: #0284c7;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
}

.table-link:hover {
  text-decoration: underline;
}

.empty-state {
  grid-column: 1 / -1;
  padding: 40px 0;
}
</style>
