<template>
  <div class="canvas-list-container">
    <!-- Header Summary Bar -->
    <div class="page-header">
      <div>
        <h2 class="title">规划画布 (Planning Canvas)</h2>
        <p class="subtitle">
          以中心仓为作用域的单次独立物流规划工作空间。支持店群分组、周排班均衡与多车型路线规划的全生命周期管理，支持增量版本演进与历史快照回溯。
        </p>
      </div>
      <div class="header-actions">
        <el-button type="primary" :icon="Plus" @click="openCreateModal">
          新建规划画布
        </el-button>
        <el-button :icon="Download" @click="downloadImportTemplate">
          下载导入模板
        </el-button>
        <el-button :icon="Refresh" @click="fetchCanvases">刷新</el-button>
      </div>
    </div>

    <!-- Metrics Cards -->
    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-icon" style="background: #e0f2fe; color: #0284c7;">
          <el-icon><DataAnalysis /></el-icon>
        </div>
        <div class="metric-info">
          <span class="metric-label">规划画布总数</span>
          <span class="metric-value">{{ canvases.length }}</span>
        </div>
      </div>
      <div class="metric-card">
        <div class="metric-icon" style="background: #f0fdf4; color: #16a34a;">
          <el-icon><Compass /></el-icon>
        </div>
        <div class="metric-info">
          <span class="metric-label">已完成路线规划</span>
          <span class="metric-value">{{ routedCount }}</span>
        </div>
      </div>
      <div class="metric-card">
        <div class="metric-icon" style="background: #fef3c7; color: #d97706;">
          <el-icon><Calendar /></el-icon>
        </div>
        <div class="metric-info">
          <span class="metric-label">排班规划中</span>
          <span class="metric-value">{{ scheduledCount }}</span>
        </div>
      </div>
      <div class="metric-card">
        <div class="metric-icon" style="background: #f3e8ff; color: #9333ea;">
          <el-icon><Collection /></el-icon>
        </div>
        <div class="metric-info">
          <span class="metric-label">累计管理门店点</span>
          <span class="metric-value">{{ totalStoresCount }}</span>
        </div>
      </div>
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
            @input="filterCanvases"
          />
          <el-select
            v-model="filterStage"
            placeholder="规划阶段"
            clearable
            style="width: 150px;"
            @change="filterCanvases"
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

    <!-- Create Canvas Dialog Modal -->
    <el-dialog
      v-model="createDialogVisible"
      title="✨ 新建规划画布 (Scope Workspace)"
      width="820px"
      :close-on-click-modal="false"
      destroy-on-close
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
              <el-button link type="primary" size="small" style="font-size: 11px; padding: 0;" @click="router.push('/config/depot')">
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
            <el-button size="small" :icon="Download" @click="downloadImportTemplate">
              下载标准模板
            </el-button>
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
              <el-button size="small" type="danger" link @click="importedExcelStores = []">
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
  Upload,
  Download,
} from '@element-plus/icons-vue'
import * as XLSX from 'xlsx'
import http, { canvasApi, depotApi, storeApi } from '../../api/client'
import { parseFileUniversal } from '../../utils/excelImport.js'

const router = useRouter()

const loading = ref(false)
const loadingDepots = ref(false)
const canvases = ref([])
const searchKeyword = ref('')
const filterStage = ref('')
const viewMode = ref('card')

// Depot & Store pool list for creation
const depotList = ref([])
const systemStores = ref([])
const selectedDepotId = ref(null)
const selectedStoreIds = reactive(new Set())

// Excel import in creation modal
const storeSelectMode = ref('system')
const createExcelInput = ref(null)
const importedExcelStores = ref([])

const importedTotalDemand = computed(() => {
  return Math.round(
    importedExcelStores.value.reduce((acc, s) => acc + Number(s.avg_loads || 10), 0)
  )
})

const importedHasSchedule = computed(() => {
  return importedExcelStores.value.some(
    (s) => !!s.delivery_days_str && s.delivery_days_str.trim().length > 0
  )
})

const importedHasCluster = computed(() => {
  return importedExcelStores.value.some(
    (s) => s.cluster_id !== undefined && s.cluster_id !== null
  )
})

const handleCreateExcelImport = async (e) => {
  const file = e.target?.files?.[0]
  if (!file) return
  try {
    const { points: parsedPoints, warnings } = await parseFileUniversal(file)
    if (!parsedPoints || !parsedPoints.length) {
      ElMessage.warning('Excel 文件中未能解析到有效门店数据，请检查经纬度与表头')
      return
    }

    importedExcelStores.value = parsedPoints.map((p, idx) => {
      const daysStr = p.delivery_days_str || p.schedule_day || ''
      const storeFreq = daysStr
        ? daysStr.split(',').filter(Boolean).length
        : Math.max(1, Number(p.frequency || 1))

      return {
        name: p.name || `门店${idx + 1}`,
        shop_code: p.shop_code || `STORE_${idx + 1}`,
        dept_id: p.dept_id || p.shop_code || '',
        district: p.district || '',
        warzone: p.warzone || '',
        address: p.address || '',
        service_time: p.service_time || 0.65,
        available_truck: p.available_truck || '',
        lng: Number(p.lng || p.longitude),
        lat: Number(p.lat || p.latitude),
        avg_loads: Number(p.avg_loads || p.weight || p.demand || 10),
        frequency: storeFreq,
        is_homepot: p.is_homepot !== undefined && p.is_homepot !== null ? Number(p.is_homepot) : 0,
        cluster_id: p.cluster_id !== undefined && p.cluster_id !== null ? Number(p.cluster_id) : undefined,
        delivery_days_str: daysStr,
        schedule_day: daysStr,
      }
    })

    if (parsedPoints[0]?.warehouse_name && (!newCanvasForm.depot_name || newCanvasForm.depot_name === '南宁中心仓')) {
      newCanvasForm.depot_name = parsedPoints[0].warehouse_name
    }

    ElMessage.success(`🎉 成功解析 ${importedExcelStores.value.length} 家门店数据！`)
  } catch (err) {
    ElMessage.error(`解析 Excel 文件失败: ${err.message || err}`)
  } finally {
    if (e.target) e.target.value = ''
  }
}

// Download Excel Import Template
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

// Dialog state
const createDialogVisible = ref(false)
const createStep = ref(0)
const creating = ref(false)

const newCanvasForm = reactive({
  name: '',
  dc_code: '',
  depot_name: '南宁中心仓',
  depot_lng: 108.36654,
  depot_lat: 22.81700,
  depot_address: '广西南宁市物流集散中心',
  description: '',
})

// Store pool filter
const storeFilterKeyword = ref('')
const storeFilterDistrict = ref('')
const storeFilterHomepot = ref('')

// Edit state
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

// District options from system stores
const districtOptions = computed(() => {
  const set = new Set()
  systemStores.value.forEach((s) => {
    if (s.district) set.add(s.district)
  })
  return Array.from(set)
})

// Filtered pool stores
const filteredPoolStores = computed(() => {
  return systemStores.value.filter((s) => {
    const kw = storeFilterKeyword.value.trim().toLowerCase()
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

const enterCanvas = (canvasId) => {
  router.push(`/canvas/workspace/${canvasId}`)
}

const openCreateModal = async () => {
  createStep.value = 0
  storeSelectMode.value = 'system'
  importedExcelStores.value = []
  
  // 每次打开新建对话框，实时重新拉取最新维护的起点与门店数据
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

  // Default select all stores if reasonable size
  if (systemStores.value.length) {
    systemStores.value.slice(0, 100).forEach((s) => selectedStoreIds.add(s.id))
  }

  createDialogVisible.value = true
}

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

    // 如果系统门店库里有属于该中心仓的门店，智能预选并提示
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
        is_homepot: Number(s.is_homepot || 0),
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
      depot_name: newCanvasForm.depot_name || '中心仓',
      depot_lng: Number(newCanvasForm.depot_lng),
      depot_lat: Number(newCanvasForm.depot_lat),
      depot_address: newCanvasForm.depot_address || undefined,
      description: newCanvasForm.description || undefined,
      points: chosenStores,
      algorithm_configs: {
        clustering_algorithm: 'kmeans',
        clustering_k: Math.max(2, Math.min(8, Math.round(chosenStores.length / 10))),
      },
    }

    const createdCanvas = await canvasApi.create(payload)
    ElMessage.success(`🎉 画布「${createdCanvas.name}」创建成功，数据已完成初始化与持久化！`)
    createDialogVisible.value = false
    enterCanvas(createdCanvas.canvas_id)
  } catch (err) {
    ElMessage.error(`创建画布失败: ${err.message}`)
  } finally {
    creating.value = false
  }
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
  fetchDepotsAndStores()
})
</script>

<style scoped>
.canvas-list-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.title {
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 4px 0;
}

.subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
  max-width: 850px;
  line-height: 1.5;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.metric-card {
  background: #ffffff;
  border-radius: 10px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #f1f5f9;
}

.metric-icon {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}

.metric-info {
  display: flex;
  flex-direction: column;
}

.metric-label {
  font-size: 12px;
  color: #64748b;
}

.metric-value {
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
  margin-top: 2px;
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

.store-filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  background: #f8fafc;
  padding: 8px 12px;
  border-radius: 6px;
}

.store-filter-left {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.store-filter-right {
  display: flex;
  gap: 6px;
}
</style>
