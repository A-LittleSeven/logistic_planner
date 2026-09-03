<template>
  <div class="clustering-view-wrapper">
    <ViewLayout>
      <template #side>
        <div class="sidebar-header">
          <h2 class="lp-section-title">路线规划与调度</h2>
          <p class="desc">
            多日多车型车辆路径规划。支持单日规划与全局排程，并在地图上可视化呈现车辆轨迹与直接调线。
          </p>
          <div v-if="dataSourceLabel" class="data-source-badge">
            📦 数据来源：{{ dataSourceLabel }}
          </div>
        </div>

        <!-- 1. Empty State Guidance Card -->
        <div v-if="!points.length" class="lp-card empty-guide-card">
          <div class="empty-guide-text" style="margin-bottom: 0;">
            💡 当前画布暂无路线数据，请从下方工具箱点击<strong>「📂 载入历史」</strong>或<strong>「📥 导入Excel」</strong>开始路线规划。
          </div>
        </div>

        <!-- 2. Day Selection & Demand Overview -->
        <div v-if="points.length" class="lp-card" style="margin-bottom: 12px;">
          <div class="form-group">
            <label class="form-label">计划配送作业日</label>
            <select v-model="selectedDay" class="lp-input select-day" @change="onDayChange">
              <option value="全部">全部时间 (全周总览)</option>
              <option value="周一">周一配送路线</option>
              <option value="周二">周二配送路线</option>
              <option value="周三">周三配送路线</option>
              <option value="周四">周四配送路线</option>
              <option value="周五">周五配送路线</option>
              <option value="周六">周六配送路线</option>
              <option value="周日">周日配送路线</option>
            </select>
          </div>
          <div style="margin-top: 8px; font-size: 12px; color: var(--text-muted); display: flex; justify-content: space-between; align-items: center;">
            <span>当前筛选门店: <strong>{{ activePoints.length }}</strong> 家</span>
            <span style="font-weight: 600; color: #0284c7;">日均总装载: {{ activeDayLoads }} 箱</span>
          </div>
          <div style="margin-top: 6px; display: flex; gap: 8px; font-size: 11px;">
            <span style="background: #e0f2fe; color: #0369a1; padding: 2px 6px; border-radius: 4px; font-weight: 600;">
              🏠 本埠门店: {{ activeHomepotCount }} 家
            </span>
            <span style="background: #fef3c7; color: #b45309; padding: 2px 6px; border-radius: 4px; font-weight: 600;">
              🚗 外埠门店: {{ activeOutpostCount }} 家
            </span>
          </div>
        </div>

        <!-- 3. Planning Algorithm & Fleet Strategy -->
        <div class="lp-card" style="margin-bottom: 12px;">
          <!-- Central Warehouse (Depot) Point Selection -->
          <div class="form-group" style="margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <label class="form-label" style="margin-bottom: 0;">🏬 起点配送中心 (中心仓 / 出发与返程点)</label>
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

          <div class="form-group" style="margin-bottom: 10px;">
            <label class="form-label">路径规划求解引擎</label>
            <div style="font-size: 12px; font-weight: 600; color: #0284c7; background: #f0f9ff; border: 1px solid #bae6fd; padding: 6px 10px; border-radius: 4px; display: flex; align-items: center; justify-content: space-between;">
              <span>⚡ 智能求解器 (容量与装载约束)</span>
              <span style="font-size: 11px; color: #0369a1; font-weight: normal;">已激活</span>
            </div>
          </div>

          <!-- Fleet Capacity Summary -->
          <div class="form-group">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <label class="form-label">可用车型与运力池 ({{ trucks.length }} 种)</label>
              <button class="lp-btn lp-btn--ghost" style="padding: 1px 6px; font-size: 11px;" @click="openFleetModal">+ 配置车型</button>
            </div>
            
            <div class="fleet-tag-list" style="display: flex; gap: 6px; flex-wrap: wrap;">
              <div v-for="(t, idx) in trucks" :key="idx" class="fleet-tag">
                <span style="font-weight: 600;">{{ t.name }}</span>
                <span style="color: #64748b; font-size: 10px;">({{ t.capacity }}箱 × {{ t.count }}辆)</span>
                <span class="remove-tag-btn" @click.stop="removeTruck(idx)">×</span>
              </div>
              <div v-if="!trucks.length" style="font-size: 11px; color: #94a3b8;">暂无可用车型，请点击配置</div>
            </div>
          </div>
        </div>

        <!-- Express & Delivery Method Management Card -->
        <div v-if="points.length" class="lp-card" style="margin-bottom: 12px; border-left: 4px solid #8b5cf6;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-weight: 700; font-size: 13px; color: #581c87; display: flex; align-items: center; gap: 4px;">
              <span>📦</span> 配送方式与快递直发管理
            </span>
            <span style="font-size: 11px; font-weight: 700; color: #7c3aed; background: #faf5ff; padding: 1px 6px; border-radius: 4px; border: 1px solid #d8b4fe;">
              快递: {{ currentExpressStores.length }} 家
            </span>
          </div>

          <div style="font-size: 11px; color: #64748b; line-height: 1.5; margin-bottom: 8px;">
            当前作业日: <strong>{{ selectedDay }}</strong> (常规货车 <strong>{{ activePoints.length - currentExpressStores.length }}</strong> 家 · 快递 <strong>{{ currentExpressStores.length }}</strong> 家)
          </div>

          <button class="lp-btn" style="width: 100%; font-size: 11px; padding: 4px 8px; background: #faf5ff; border: 1px solid #c4b5fd; color: #7c3aed; font-weight: 600; cursor: pointer;" @click="expressModalVisible = true">
            📋 门店配送方式列表与一键切换
          </button>
        </div>

        <!-- 4. Core Actions Toolbar -->
        <div class="actions-container lp-card">
          <div class="main-solve-row">
            <button class="lp-btn lp-btn--primary main-solve-btn" :disabled="loading || activePoints.length < 1" @click="solve">
              {{ loading ? '路线规划计算中…' : '⚡ 执行路线规划' }}
            </button>
            <button 
              class="lp-btn lp-btn--ghost gear-btn" 
              title="求解器参数设置" 
              @click="configDialogVisible = true"
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
            <button class="lp-btn lp-btn--ghost" @click="exportRoutingExcel">
              📤 导出Excel
            </button>
            <button 
              class="lp-btn lp-btn--ghost" 
              :class="{ 'is-box-selecting': isSelecting }"
              :disabled="!activePoints.length" 
              @click="toggleBoxSelect"
            >
              {{ isSelecting ? '取消框选' : '📐 框选批量调线' }}
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
            <div v-if="result?.routes?.length" style="display: flex; flex-direction: column; gap: 4px;">
              <label style="font-size: 11px; font-weight: 600; color: #555;">批量转移至目标路线：</label>
              <div style="display: flex; gap: 6px;">
                <select v-model="batchTargetRoute" style="font-size: 12px; padding: 6px; flex: 1; border-radius: 4px; border: 1px solid #cbd5e1; background: white;">
                  <option value="" disabled>选择目标路线</option>
                  <option v-for="(r, rIdx) in result.routes" :key="rIdx" :value="rIdx">
                    路线 {{ rIdx + 1 }} ({{ r.truck_name }}, 已载{{ r.load }}箱)
                  </option>
                  <option value="new">+ 新建独立车辆路线</option>
                </select>
                <button class="lp-btn" style="font-size: 11px; padding: 6px 12px;" :disabled="batchTargetRoute === ''" @click="applyBatchMoveRoute">应用</button>
              </div>
            </div>

            <div style="display: flex; gap: 6px; margin-top: 6px; flex-wrap: wrap;">
              <button class="lp-btn" style="flex: 1; font-size: 11px; padding: 4px 6px; background: #faf5ff; border: 1px solid #d8b4fe; color: #7c3aed;" @click="batchSetExpress(1)">
                📦 批量设为快递
              </button>
              <button class="lp-btn" style="flex: 1; font-size: 11px; padding: 4px 6px; background: #f0fdf4; border: 1px solid #86efac; color: #16a34a;" @click="batchSetExpress(0)">
                🚛 批量恢复货车
              </button>
            </div>

            <div style="display: flex; gap: 8px; margin-top: 6px;">
              <button class="lp-btn lp-btn--danger" style="flex: 1; font-size: 11px; padding: 4px 0;" @click="batchDeletePoints">批量删除所选</button>
              <button class="lp-btn lp-btn--ghost" style="flex: 1; font-size: 11px; padding: 4px 0;" @click="selectedPointIndices = []">取消选择</button>
            </div>
          </div>
        </div>

        <!-- 5. Route Result Card -->
        <ResultCard :title="selectedDay === '全部' ? '全周车辆路线与快递方案' : `${selectedDay} 车辆路线与快递方案`" :visible="!!displayResult || currentExpressStores.length > 0">
          <template v-if="displayResult || currentExpressStores.length">
            <!-- Summary Stats: All Week vs Single Day -->
            <div class="summary-stats-grid" v-if="selectedDay === '全部' && displayResult">
              <div class="stat-box">
                <span class="stat-label">全周总里程</span>
                <span class="stat-val" style="color: #0284c7;">{{ allWeekStats.totalDist }} <small>km</small></span>
              </div>
              <div class="stat-box">
                <span class="stat-label">已排作业日</span>
                <span class="stat-val" style="color: #10b981;">{{ allWeekStats.plannedDaysCount }} <small>天</small></span>
              </div>
              <div class="stat-box">
                <span class="stat-label">总运行车次</span>
                <span class="stat-val" style="color: #6366f1;">{{ allWeekStats.totalVehicles }} <small>辆次</small></span>
              </div>
              <div class="stat-box">
                <span class="stat-label">全周总装载</span>
                <span class="stat-val" style="color: #f59e0b;">{{ allWeekStats.totalLoad }} <small>箱</small></span>
              </div>
            </div>

            <div class="summary-stats-grid" v-else-if="result && result.routes && result.routes.length">
              <div class="stat-box">
                <span class="stat-label">总行驶里程</span>
                <span class="stat-val" style="color: #0284c7;">{{ (result.total_distance || 0).toFixed(1) }} <small>km</small></span>
              </div>
              <div class="stat-box">
                <span class="stat-label">配送门店数</span>
                <span class="stat-val" style="color: #10b981;">{{ result.total_stores || 0 }} <small>家</small></span>
              </div>
              <div class="stat-box">
                <span class="stat-label">启用车辆数</span>
                <span class="stat-val" style="color: #6366f1;">{{ result.routes.length }} <small>辆</small></span>
              </div>
              <div class="stat-box">
                <span class="stat-label">平均车装载</span>
                <span class="stat-val" style="color: #f59e0b;">{{ avgTruckLoad }} <small>箱/车</small></span>
              </div>
            </div>

            <div style="margin-top: 10px;">
              <RoutePlanList
                :routes="currentDisplayRoutes"
                :show-summary="false"
                :all-routes="currentDisplayRoutes"
                :express-stores="currentExpressStores"
                :highlighted-route-idx="highlightedRouteIdx"
                :loading-amap-route-key="loadingAmapRouteKey"
                :batch-measuring="batchMeasuring"
                :measure-progress="measureProgress"
                :get-route-color="routeColor"
                @toggle-highlight="toggleHighlightRoute"
                @calculate-amap="({ route, routeIdx }) => handleCalculateSingleAmapRoute({ route, routeIdx })"
                @batch-calculate-amap="handleBatchCalculateAmap"
                @move-store-order="({ routeIdx, storeIdx, direction }) => moveStoreOrder(routeIdx, storeIdx, direction)"
                @reorder-store="({ routeIdx, fromIdx, toIdx }) => handleReorderStore(routeIdx, fromIdx, toIdx)"
                @transfer-store="({ fromRouteIdx, storeIdx, targetRouteIdx }) => moveStoreBetweenRoutes(fromRouteIdx, storeIdx, targetRouteIdx)"
                @restore-express-store="handleRestoreExpressStore"
                @select-store="handleSelectStore"
              />
            </div>
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
    <el-dialog v-model="saveDialogVisible" title="保存车辆路线规划方案" width="480px" destroy-on-close :append-to-body="true">
      <el-form label-width="90px">
        <el-form-item label="方案名称">
          <el-input v-model="planTitle" placeholder="例如: 南宁配送中心周一送货路径规划" />
        </el-form-item>
        <el-form-item label="规划摘要">
          <div style="font-size: 13px; color: #64748b; line-height: 1.6;">
            作业日：<strong>{{ selectedDay }}</strong>，包含 <strong>{{ activePoints.length }}</strong> 家门店，规划 <strong>{{ result?.routes?.length || 0 }}</strong> 条配送路线，总里程 <strong>{{ result?.total_distance?.toFixed(1) || 0 }}</strong> km。
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="saveDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSavePlan">确认保存</el-button>
      </template>
    </el-dialog>

    <!-- Load History Modal Dialog -->
    <el-dialog v-model="historyDialogVisible" title="导入历史规划 / 排班方案" width="760px" destroy-on-close :append-to-body="true">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; gap: 12px; flex-wrap: wrap;">
        <el-tabs v-model="historyTab" @tab-change="fetchHistory" style="margin-bottom: 0;">
          <el-tab-pane label="🎨 画布工作台方案 (CANVAS)" name="CANVAS" />
          <el-tab-pane label="路线规划历史 (ROUTING)" name="ROUTING" />
          <el-tab-pane label="门店排班历史 (CLUSTER_SCHEDULE)" name="CLUSTER_SCHEDULE" />
        </el-tabs>

        <el-radio-group v-if="historyTab !== 'CANVAS'" v-model="historySaveType" size="small" @change="fetchHistory">
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
            <el-button type="primary" size="small" @click="loadHistoryData(row)">载入此方案</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- Express Manager Modal Component -->
    <ExpressManagerModal
      v-model:visible="expressModalVisible"
      :stores="points"
      :current-day="selectedDay"
      @toggle-express="({ store, day, isExpress }) => handleToggleStoreExpress(store, day, isExpress)"
      @batch-set-express="({ targets, day, isExpress }) => handleBatchSetStoresExpress(targets, day, isExpress)"
    />

    <!-- Fleet Configuration Dialog -->
    <el-dialog v-model="fleetDialogVisible" title="🚚 选用系统维护车型运力" width="700px" destroy-on-close :append-to-body="true">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; background: #f0f9ff; border: 1px solid #bae6fd; padding: 8px 12px; border-radius: 6px;">
        <span style="font-size: 12px; color: #0369a1;">
          💡 规划车型严格从系统已维护的车型库中选用。勾选本次规划需启用的车型并设置可用车数。
        </span>
        <el-button link type="primary" size="small" @click="router.push('/config/vehicle')">
          前往「车型维护」管理 ↗
        </el-button>
      </div>

      <el-table :data="systemVehicles" v-loading="loadingVehicles" border stripe size="small" max-height="320px">
        <el-table-column label="选用" width="55" align="center">
          <template #default="{ row }">
            <el-checkbox v-model="row.selected" />
          </template>
        </el-table-column>
        <el-table-column prop="vehicle_code" label="车型编码" width="100">
          <template #default="{ row }">
            <span style="font-family: monospace; font-weight: 600; color: #475569;">{{ row.vehicle_code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="车型名称" min-width="150">
          <template #default="{ row }">
            <strong style="color: #0f172a;">{{ row.name }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="capacity_weight" label="最大载重 (箱)" width="120" align="right">
          <template #default="{ row }">
            <span style="color: #0284c7; font-weight: 600;">{{ row.capacity_weight }} 箱</span>
          </template>
        </el-table-column>
        <el-table-column prop="capacity_volume" label="货箱容积" width="90" align="right">
          <template #default="{ row }">
            <span>{{ row.capacity_volume }} m³</span>
          </template>
        </el-table-column>
        <el-table-column label="本次规划车数" width="130" align="center">
          <template #default="{ row }">
            <el-input-number 
              v-model="row.count" 
              :min="1" 
              :max="row.available_count || 50" 
              :disabled="!row.selected"
              size="small" 
              style="width: 100px;" 
            />
          </template>
        </el-table-column>
      </el-table>

      <template #footer>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 12px; color: #64748b;">已勾选 <strong>{{ systemVehicles.filter(v => v.selected).length }}</strong> 种系统车型</span>
          <div>
            <el-button @click="fleetDialogVisible = false">取消</el-button>
            <el-button type="primary" @click="confirmFleetSelection">确认选用并应用</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- Route Optimization Settings Dialog -->
    <el-dialog v-model="configDialogVisible" title="⚙️ 求解器参数设置" width="520px" destroy-on-close :append-to-body="true">
      <el-form label-width="160px" label-position="left" style="padding: 4px 10px;">
        <el-form-item label="单车装载率上限">
          <div style="display: flex; align-items: center; gap: 12px; width: 100%;">
            <el-slider v-model="routeOptions.max_capacity_rate" :min="0.5" :max="1.2" :step="0.01" style="flex: 1;" />
            <span style="font-weight: 700; width: 45px; text-align: right; color: #0284c7;">{{ Math.round(routeOptions.max_capacity_rate * 100) }}%</span>
          </div>
          <div style="font-size: 11px; color: #94a3b8; line-height: 1.4;">(max_capacity_rate) 车辆满载率目标上限，默认 110%</div>
        </el-form-item>

        <el-form-item label="求解器耗时上限">
          <div style="display: flex; align-items: center; gap: 8px;">
            <el-input-number v-model="routeOptions.time_limit_seconds" :min="1" :max="300" :step="1" />
            <span style="font-size: 12px; color: #64748b;">秒</span>
          </div>
          <div style="font-size: 11px; color: #94a3b8; line-height: 1.4; margin-top: 2px;">(time_limit_seconds) 求解器最大允许计算时间，默认 60 秒</div>
        </el-form-item>

        <el-form-item label="配送完成返回中心仓">
          <el-switch 
            v-model="routeOptions.return_to_depot" 
            active-text="返回中心仓 (闭环配送)" 
            inactive-text="不返回 (以末站为终点)"
          />
          <div style="font-size: 11px; color: #94a3b8; line-height: 1.4; margin-top: 2px;">(return_to_depot) 设为否时，路线以最后一家配送门店为终点，不计算返回仓库的里程</div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="configDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveRouteOptions">保存参数</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import ViewLayout from '../components/ViewLayout.vue'
import ResultCard from '../components/ResultCard.vue'
import MapPanel from '../components/MapPanel.vue'
import MapStoreSearch from '../components/MapStoreSearch.vue'
import RoutePlanList from '../components/planning/RoutePlanList.vue'
import ExpressManagerModal from '../components/planning/ExpressManagerModal.vue'
import { useRouteOptimizer } from '../composables/useRouteOptimizer.js'
import { useRouteExport } from '../composables/useRouteExport.js'
import { useRouteMapRenderer } from '../composables/useRouteMapRenderer.js'

const { calcDistanceKm, getStoreScheduleDays, getStoreExpressDays, isStoreExpressOnDay, setStoreExpressOnDay, optimizeRouteWith2Opt, clearRouteMeasureCache, removeExpressFromRoutes, resolveHomepot, hydrateRoutePoints, moveStoreOrder: optMoveStoreOrder, recalculateRouteMetrics: optRecalculateRouteMetrics } = useRouteOptimizer()
import { DAYS_LIST, formatDuration, getDistanceBetweenCoords } from '../utils/constants.js'
const { exportRoutesToExcel } = useRouteExport()
const { renderRouteMapLayers } = useRouteMapRenderer()
import { routingApi, canvasApi, depotApi, historyApi, storeApi, vehicleApi } from '../api/client.js'
import { dotHtml, ROUTE_COLORS } from '../utils/mapMarkers.js'
import { parseFileUniversal } from '../utils/excelImport.js'
import { useRouteMeasure } from '../composables/useRouteMeasure.js'
import * as XLSX from 'xlsx'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const route = useRoute()
const mapCenter = [108.33, 22.80]

const mapPanel = ref(null)
const amap = ref(null)

const points = ref([])
const dataSourceLabel = ref('')
const algorithm = ref('ortools')
const selectedDay = ref('全部')

// 门店搜索选中后联动: 飞到门店位置 (本视图标记未缓存引用, 不联动弹窗)
const handleSelectStore = (item) => {
  if (!item || !item.lng || !item.lat) return
  const mapObj = mapPanel.value?.getMap()
  if (mapObj) mapObj.setZoomAndCenter(15, [Number(item.lng), Number(item.lat)])
}

const depotName = ref('南宁中心仓')
const depotLng = ref(108.318344)
const depotLat = ref(22.846367)
const depotList = ref([])
const selectedDepotKey = ref('')

const trucks = ref([
  { name: '4.2米厢式货车', capacity: 230, count: 20 },
])

const newTruckName = ref('')
const newTruckCapacity = ref(230)
const newTruckCount = ref(1)

const result = ref(null)

const expressModalVisible = ref(false)

const currentExpressStores = computed(() => {
  if (selectedDay.value === '全部') {
    return points.value.filter(p => isStoreExpressOnDay(p, '全部'))
  }
  return points.value.filter(p => isStoreExpressOnDay(p, selectedDay.value) && (p.delivery_days_str || '').includes(selectedDay.value))
})

const handleToggleStoreExpress = (row, day, isExp) => {
  const targetDay = day || selectedDay.value || '全部'
  setStoreExpressOnDay(row, targetDay, isExp)
  if (Number(isExp) === 1) {
    const daysToClean = targetDay === '全部' ? DAYS_LIST : [targetDay]
    const isReturn = routeOptions.value?.return_to_depot ?? false
    const depotPos = { lng: Number(depotLng.value), lat: Number(depotLat.value) }
    removeExpressFromRoutes(dailyResults.value, daysToClean, {
      depotPos,
      isReturn,
      extraRoutes: result.value?.routes,
    })
    recalculateRouteMetrics()
  }
  renderRoute()
  saveToLocalStorage()
  ElMessage.success()
}

const handleBatchSetStoresExpress = (targets, day, isExp) => {
  if (!targets.length) return
  const targetDay = day || selectedDay.value || '全部'
  targets.forEach((p) => {
    setStoreExpressOnDay(p, targetDay, isExp)
  })
  if (Number(isExp) === 1) {
    const daysToClean = targetDay === '全部' ? DAYS_LIST : [targetDay]
    const isReturn = routeOptions.value?.return_to_depot ?? false
    const depotPos = { lng: Number(depotLng.value), lat: Number(depotLat.value) }
    removeExpressFromRoutes(dailyResults.value, daysToClean, {
      depotPos,
      isReturn,
      extraRoutes: result.value?.routes,
    })
    recalculateRouteMetrics()
  }
  renderRoute()
  saveToLocalStorage()
  ElMessage.success()
}

// Global hook for map InfoWindow button
window.updateStoreExpressDay = function(globalIdx, day, isExp) {
  const store = points.value[globalIdx]
  if (store) {
    handleToggleStoreExpress(store, day, isExp)
  }
}

// AMap Route Measure Composable
const {
  loadingAmapRouteKey,
  batchMeasuring,
  measureProgress,
  measureSummary,
  measureSingleRoute,
  batchMeasureRoutes,
} = useRouteMeasure()

const handleCalculateSingleAmapRoute = async ({ route: targetRoute, routeIdx }) => {
  const isAllWeek = selectedDay.value === '全部'
  const rawStops = targetRoute.points || targetRoute.stops || []

  const routeObj = {
    ...targetRoute,
    points: rawStops,
    stops: rawStops,
    truck_name: targetRoute.truck_name || targetRoute.vehicle_name,
    raw_route: targetRoute.raw_route || targetRoute,
  }

  await measureSingleRoute(routeObj, isAllWeek ? `all_${routeIdx}` : `day_${routeIdx}`, {
    depotLng: Number(depotLng.value),
    depotLat: Number(depotLat.value),
    returnToDepot: routeOptions.value.return_to_depot,
    onSuccess: (updated) => {
      targetRoute.amap_distance = updated.amap_distance
      targetRoute.amap_duration = updated.amap_duration
      targetRoute.amap_tolls = updated.amap_tolls
      targetRoute.amap_path = updated.amap_path
      targetRoute.detailed_polyline = updated.detailed_polyline
      targetRoute.distance = updated.amap_distance
      targetRoute.distance_km = updated.amap_distance
      if (targetRoute.raw_route) {
        targetRoute.raw_route.amap_distance = updated.amap_distance
        targetRoute.raw_route.amap_duration = updated.amap_duration
        targetRoute.raw_route.amap_tolls = updated.amap_tolls
        targetRoute.raw_route.toll = updated.amap_tolls
        targetRoute.raw_route.amap_path = updated.amap_path
        targetRoute.raw_route.detailed_polyline = updated.detailed_polyline
        targetRoute.raw_route.distance = updated.amap_distance
        targetRoute.raw_route.distance_km = updated.amap_distance
      }
      renderRoute()
      saveToLocalStorage()
    },
  })
}

const handleBatchCalculateAmap = async () => {
  const isAllWeek = selectedDay.value === '全部'
  const list = isAllWeek ? allWeekRoutes.value : result.value?.routes || []
  if (!list.length) {
    ElMessage.warning('当前暂无可测算路线，请先执行路线规划')
    return
  }

  // 格式化传入测算器
  const measureList = list.map((r, rIdx) => {
    const stops = r.points || r.stops || []
    return {
      ...r,
      points: stops,
      stops,
      truck_name: r.truck_name || r.vehicle_name,
      raw_route: r.raw_route || r,
    }
  })

  await batchMeasureRoutes(measureList, {
    depotLng: Number(depotLng.value),
    depotLat: Number(depotLat.value),
    returnToDepot: routeOptions.value.return_to_depot,
    onSingleSuccess: (updated) => {
      renderRoute()
    },
    onAllCompleted: () => {
      recalculateRouteMetrics()
      renderRoute()
      saveToLocalStorage()
    },
  })
}
const dailyResults = ref({})
const loading = ref(false)
const errorMsg = ref('')

const highlightedRouteIdx = ref(null)
const expandedRouteIndices = ref(new Set())

// Selection & Box Select
const isSelecting = ref(false)
let mouseTool = null
const selectedPointIndices = ref([])
const batchTargetRoute = ref('')

// Modals
const saveDialogVisible = ref(false)
const planTitle = ref('')
const saving = ref(false)

const historyDialogVisible = ref(false)
const historyTab = ref('ROUTING')
const historySaveType = ref('')
const historyList = ref([])
const loadingHistory = ref(false)

const fleetDialogVisible = ref(false)
const configDialogVisible = ref(false)

const routeOptions = ref({
  max_capacity_rate: 1.10,
  time_limit_seconds: 60,
  return_to_depot: false,
})

const getRouteStoreOrder = (route) => {
  if (!route?.order) return []
  return route.order.filter(idx => idx !== -1)
}

const excelFileInput = ref(null)

const round = (n) => Math.round(n * 1e5) / 1e5
const routeColor = (idx) => ROUTE_COLORS[idx % ROUTE_COLORS.length]

// Filter points for current selected day
const activePoints = computed(() => {
  if (selectedDay.value === '全部') return points.value
  return points.value.filter(p => p.delivery_days_str && p.delivery_days_str.includes(selectedDay.value))
})

const activeDayLoads = computed(() => {
  return Math.round(activePoints.value.reduce((sum, p) => sum + (Number(p.avg_loads || p.weight) || 0), 0))
})

const activeHomepotCount = computed(() => {
  return activePoints.value.filter(p => Number(p.is_homepot !== undefined && p.is_homepot !== null ? p.is_homepot : 1) === 1).length
})

const activeOutpostCount = computed(() => {
  return activePoints.value.filter(p => Number(p.is_homepot !== undefined && p.is_homepot !== null ? p.is_homepot : 0) === 0).length
})



const allWeekRoutes = computed(() => {
  const list = []
  DAYS_LIST.forEach((day) => {
    const dayRes = dailyResults.value[day]
    if (dayRes?.routes?.length) {
      dayRes.routes.forEach((r, rIdx) => {
        const stops = r.points || r.stops || []
        const isHp = resolveHomepot(r, stops)

        list.push({
          ...r,
          day,
          day_route_idx: rIdx,
          route_title: `${day} 路线 ${rIdx + 1}`,
          truck_name: r.truck_name || r.vehicle_name || '默认车型',
          vehicle_name: r.vehicle_name || r.truck_name || '默认车型',
          is_homepot: isHp,
          distance: Number((r.distance ?? r.distance_km ?? 0)),
          distance_km: Number((r.distance ?? r.distance_km ?? 0)),
          load: Number(r.load ?? r.avg_loads ?? 0),
          stops,
          points: stops,
          detailed_polyline: r.detailed_polyline || r.amap_path,
          amap_path: r.amap_path || r.detailed_polyline,
          raw_route: r,
        })
      })
    }
  })
  return list
})

const allWeekStats = computed(() => {
  const plannedDays = DAYS_LIST.filter((d) => dailyResults.value[d]?.routes?.length)
  const totalDist = allWeekRoutes.value.reduce((sum, r) => sum + (Number(r.distance) || 0), 0)
  const totalLoad = allWeekRoutes.value.reduce((sum, r) => sum + (Number(r.load) || 0), 0)
  const totalVehicles = allWeekRoutes.value.length
  return {
    plannedDaysCount: plannedDays.length,
    plannedDays,
    totalDist: round(totalDist),
    totalLoad: Math.round(totalLoad),
    totalVehicles,
    avgTruckLoad: totalVehicles > 0 ? Math.round(totalLoad / totalVehicles) : 0,
  }
})

const displayResult = computed(() => {
  if (selectedDay.value === '全部') {
    if (allWeekRoutes.value.length > 0) {
      return {
        isAllWeek: true,
        total_distance: allWeekStats.value.totalDist,
        total_stores: points.value.length,
        routes: allWeekRoutes.value,
        plannedDaysCount: allWeekStats.value.plannedDaysCount,
      }
    }
    return null
  }
  return result.value
})

const currentDisplayRoutes = computed(() => {
  if (selectedDay.value === '全部') {
    return allWeekRoutes.value
  }
  const dayRoutes = dailyResults.value[selectedDay.value]?.routes || result.value?.routes || []
  return dayRoutes.map((r, rIdx) => {
    const stops = r.points || r.stops || []
    const isHp = resolveHomepot(r, stops)

    return {
      ...r,
      day: selectedDay.value,
      day_route_idx: rIdx,
      route_title: `${selectedDay.value} 路线 ${rIdx + 1}`,
      truck_name: r.truck_name || r.vehicle_name || '默认车型',
      vehicle_name: r.vehicle_name || r.truck_name || '默认车型',
      is_homepot: isHp,
      points: stops,
      stops: stops,
      detailed_polyline: r.detailed_polyline || r.amap_path,
      amap_path: r.amap_path || r.detailed_polyline,
      raw_route: r,
    }
  })
})



const avgTruckLoad = computed(() => {
  if (!result.value?.routes?.length) return 0
  const totalLoad = result.value.routes.reduce((sum, r) => sum + (r.load || 0), 0)
  return Math.round(totalLoad / result.value.routes.length)
})


async function clearAll() {
  try {
    if (points.value.length > 0 || result.value) {
      await ElMessageBox.confirm('是否确认清空当前规划画布中的全部门店、路线与结果？', '清空画布确认', {
        confirmButtonText: '确认清空',
        cancelButtonText: '取消',
        type: 'warning',
      })
    }
  } catch {
    return
  }

  points.value = []
  result.value = null
  dailyResults.value = {}
  selectedPointIndices.value = []
  expandedRouteIndices.value = new Set()
  highlightedRouteIdx.value = null
  errorMsg.value = ''
  dataSourceLabel.value = ''
  localStorage.removeItem('routing_result')
  localStorage.removeItem('routing_daily_results')
  
  if (mapPanel.value) {
    mapPanel.value.clearAll()
  }
  renderRoute()
  saveToLocalStorage()
  ElMessage.success('规划画布已全部清空！')
}

function toggleExpandRoute(rIdx) {
  if (expandedRouteIndices.value.has(rIdx)) {
    expandedRouteIndices.value.delete(rIdx)
  } else {
    expandedRouteIndices.value.add(rIdx)
  }
}

function toggleHighlightRoute(rIdx) {
  highlightedRouteIdx.value = highlightedRouteIdx.value === rIdx ? null : rIdx
  renderRoute()
}

function openFleetModal() {
  fleetDialogVisible.value = true
  fetchSystemVehicles()
}

const systemVehicles = ref([])
const loadingVehicles = ref(false)

async function fetchSystemVehicles() {
  loadingVehicles.value = true
  try {
    const list = await vehicleApi.list()
    
    // Match with current selected trucks
    systemVehicles.value = list.map(v => {
      const match = trucks.value.find(t => t.vehicle_code === v.vehicle_code || t.name === v.name)
      return {
        ...v,
        selected: !!match,
        count: match ? match.count : Math.min(v.available_count || 5, 10)
      }
    })
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    loadingVehicles.value = false
  }
}

function confirmFleetSelection() {
  const selected = systemVehicles.value.filter(v => v.selected)
  if (!selected.length) {
    ElMessage.warning('请至少勾选一种系统已维护的车型')
    return
  }

  trucks.value = selected.map(v => ({
    vehicle_code: v.vehicle_code,
    name: v.name,
    capacity: Number(v.capacity_weight),
    count: Number(v.count || 1),
    cost_per_km: Number(v.cost_per_km || 0)
  }))

  saveToLocalStorage()
  fleetDialogVisible.value = false
  ElMessage.success(`已选用 ${trucks.value.length} 种系统维护车型！`)
}

function removeTruck(idx) {
  trucks.value.splice(idx, 1)
  saveToLocalStorage()
}

function saveRouteOptions() {
  localStorage.setItem('route_solver_options', JSON.stringify(routeOptions.value))
  configDialogVisible.value = false
  ElMessage.success('路线规划参数已更新！')
}

// -------------------------------------------------------------
// 2-Opt Local TSP Optimizer for Dynamic Route Adjustments
// -------------------------------------------------------------
const optimizeRouteOrder = (routeOrder) => {
  const getCoord = (idx) => {
    if (idx === -1) return { lng: Number(depotLng.value), lat: Number(depotLat.value) }
    return activePoints.value[idx] || { lng: Number(depotLng.value), lat: Number(depotLat.value) }
  }
  return optimizeRouteWith2Opt(routeOrder, routeOptions.value.return_to_depot, getCoord)
}

// In-map point route transfer
window.updateStoreRoute = function(currentRouteIdx, storeSeq, targetRouteVal) {
  moveStoreBetweenRoutes(currentRouteIdx, storeSeq, targetRouteVal)
}

function moveStoreBetweenRoutes(sourceRouteIdx, storeSeq, targetRouteVal) {
  const displayList = currentDisplayRoutes.value
  const sourceRoute = displayList[sourceRouteIdx]
  if (!sourceRoute) return
  const sourceDay = sourceRoute.day || selectedDay.value
  const dayRes = dailyResults.value[sourceDay]
  const dayRoutes = dayRes?.routes || result.value?.routes
  if (!dayRoutes) return
  const dayRoute = dayRoutes[sourceRoute.day_route_idx ?? sourceRouteIdx]
  if (!dayRoute || !dayRoute.points) return

  const movedStore = dayRoute.points[storeSeq]
  if (!movedStore) return

  const isReturn = routeOptions.value?.return_to_depot ?? false
  const depotPos = { lng: Number(depotLng.value), lat: Number(depotLat.value) }

  // 1. 从源路线移除并执行 2-Opt 顺路优化
  dayRoute.points.splice(storeSeq, 1)
  dayRoute.stops = dayRoute.points
  clearRouteMeasureCache(dayRoute)
  if (dayRoute.points.length > 2) {
    dayRoute.points = optimizeRouteWith2Opt(dayRoute.points, isReturn, { depot: depotPos })
    dayRoute.stops = dayRoute.points
  }

  // 2. 目标动作
  if (targetRouteVal === 'express') {
    setStoreExpressOnDay(movedStore, sourceDay, 1)
    // 清理各天空路线
    DAYS_LIST.forEach((d) => {
      if (dailyResults.value[d]?.routes) {
        dailyResults.value[d].routes = dailyResults.value[d].routes.filter((r) => r.points && r.points.length > 0)
      }
    })
    if (result.value?.routes) {
      result.value.routes = result.value.routes.filter((r) => r.points && r.points.length > 0)
    }
    recalculateRouteMetrics()
    renderRoute()
    saveToLocalStorage()
    mapPanel.value?.closeInfoWindow && mapPanel.value.closeInfoWindow()
    ElMessage.success(`已将门店「${movedStore.name}」在【${sourceDay}】设为快递直发，已从货车配送路线中剔除`)
    return
  } else if (targetRouteVal === 'new') {
    const defaultTruck = trucks.value[0]?.name || '4.2米厢式货车'
    const newRoute = {
      day: sourceDay,
      day_route_idx: dayRoutes.length,
      route_title: `${sourceDay} 路线 ${dayRoutes.length + 1}`,
      truck_name: defaultTruck,
      vehicle_name: defaultTruck,
      points: [movedStore],
      stops: [movedStore],
      load: Number(movedStore.avg_loads || movedStore.weight || 10),
      total_weight: Number(movedStore.avg_loads || movedStore.weight || 10),
      distance: 0,
      distance_km: 0,
      is_homepot: Number(movedStore.is_homepot ?? 1),
    }
    dayRoutes.push(newRoute)
    ElMessage.success(`已在 ${sourceDay} 为门店「${movedStore.name}」创建新独立路线`)
  } else {
    const targetIdx = Number(targetRouteVal)
    const targetDisplayRoute = displayList[targetIdx]
    if (targetDisplayRoute && (targetDisplayRoute.day === sourceDay || selectedDay.value !== '全部')) {
      const targetDayRoute = dayRoutes[targetDisplayRoute.day_route_idx ?? targetIdx]
      if (targetDayRoute) {
        if (!targetDayRoute.points) targetDayRoute.points = []
        targetDayRoute.points.push(movedStore)
        targetDayRoute.stops = targetDayRoute.points
        clearRouteMeasureCache(targetDayRoute)
        if (targetDayRoute.points.length > 2) {
          targetDayRoute.points = optimizeRouteWith2Opt(targetDayRoute.points, isReturn, { depot: depotPos })
          targetDayRoute.stops = targetDayRoute.points
        }
        ElMessage.success(`已将门店「${movedStore.name}」转移至路线 ${(targetDisplayRoute.day_route_idx ?? targetIdx) + 1} 并完成 2-Opt 顺路优化！`)
      }
    }
  }

  // 3. 清理空路线并重新汇总指标
  DAYS_LIST.forEach((d) => {
    if (dailyResults.value[d]?.routes) {
      dailyResults.value[d].routes = dailyResults.value[d].routes.filter((r) => r.points && r.points.length > 0)
    }
  })
  if (result.value?.routes) {
    result.value.routes = result.value.routes.filter((r) => r.points && r.points.length > 0)
  }
  recalculateRouteMetrics()
  renderRoute()
  saveToLocalStorage()
  mapPanel.value?.closeInfoWindow && mapPanel.value.closeInfoWindow()
}

const moveStoreOrder = (routeIdx, storeSeq, direction) => {
  const displayList = currentDisplayRoutes.value
  const route = displayList[routeIdx]
  if (!route) return
  const sourceDay = route.day || selectedDay.value
  const dayRes = dailyResults.value[sourceDay]
  const dayRoutes = dayRes?.routes || result.value?.routes
  if (!dayRoutes) return
  const dayRoute = dayRoutes[route.day_route_idx ?? routeIdx]
  if (!dayRoute || !dayRoute.points) return

  const pts = dayRoute.points
  const targetSeq = storeSeq + direction
  if (targetSeq < 0 || targetSeq >= pts.length) return
  const temp = pts[storeSeq]
  pts[storeSeq] = pts[targetSeq]
  pts[targetSeq] = temp
  dayRoute.stops = pts
  clearRouteMeasureCache(dayRoute)

  recalculateRouteMetrics()
  renderRoute()
  saveToLocalStorage()
  ElMessage.success(`路线 ${routeIdx + 1} 站点次序已更新`)
}

const handleReorderStore = (routeIdx, fromIdx, toIdx) => {
  const displayList = currentDisplayRoutes.value
  const route = displayList[routeIdx]
  if (!route) return
  const sourceDay = route.day || selectedDay.value
  const dayRes = dailyResults.value[sourceDay]
  const dayRoutes = dayRes?.routes || result.value?.routes
  if (!dayRoutes) return
  const dayRoute = dayRoutes[route.day_route_idx ?? routeIdx]
  if (!dayRoute || !dayRoute.points) return

  const pts = dayRoute.points
  if (fromIdx < 0 || fromIdx >= pts.length || toIdx < 0 || toIdx >= pts.length || fromIdx === toIdx) return

  const [movedItem] = pts.splice(fromIdx, 1)
  pts.splice(toIdx, 0, movedItem)
  dayRoute.stops = pts
  clearRouteMeasureCache(dayRoute)

  recalculateRouteMetrics()
  renderRoute()
  saveToLocalStorage()
  ElMessage.success(`已将「${movedItem.name || '门店'}」拖拽调整至第 ${toIdx + 1} 站`)
}

const handleRestoreExpressStore = (store) => {
  if (!store) return
  const targetDay = selectedDay.value || '全部'
  setStoreExpressOnDay(store, targetDay, 0)
  renderRoute()
  saveToLocalStorage()
  ElMessage.success(`已恢复门店「${store.name}」在【${targetDay}】为货车配送`)
}

const batchSetExpress = (val) => {
  if (!selectedPointIndices.value.length) return
  const targetDay = selectedDay.value || '全部'
  selectedPointIndices.value.forEach((idx) => {
    const p = activePoints.value[idx]
    if (p) {
      setStoreExpressOnDay(p, targetDay, val)
    }
  })
  if (Number(val) === 1) {
    const daysToClean = targetDay === '全部' ? DAYS_LIST : [targetDay]
    const isReturn = routeOptions.value?.return_to_depot ?? false
    const depotPos = { lng: Number(depotLng.value), lat: Number(depotLat.value) }
    removeExpressFromRoutes(dailyResults.value, daysToClean, {
      depotPos,
      isReturn,
      extraRoutes: result.value?.routes,
    })
    recalculateRouteMetrics()
  }
  selectedPointIndices.value = []
  renderRoute()
  saveToLocalStorage()
  ElMessage.success(`已将框选门店在【${targetDay}】批量设置为: ${Number(val) === 1 ? '📦 快递直发' : '🚛 常规货车'}`)
}

window.updateStoreExpress = function(gIdx, val) {
  if (gIdx >= 0 && gIdx < points.value.length) {
    const store = points.value[gIdx]
    const isExp = Number(val)
    const targetDay = selectedDay.value || '全部'
    setStoreExpressOnDay(store, targetDay, isExp)
    if (isExp === 1) {
      handleToggleStoreExpress(store, targetDay, 1)
    } else {
      renderRoute()
      saveToLocalStorage()
      ElMessage.success(`门店「${store.name}」配送方式已更新为: 🚛 货车配送`)
    }
  }
}

window.updateStoreHomepot = function(gIdx, val) {
  if (gIdx >= 0 && gIdx < points.value.length) {
    const newHp = Number(val)
    points.value[gIdx].is_homepot = newHp
    const sName = points.value[gIdx].name || `门店${gIdx + 1}`
    saveToLocalStorage()
    recalculateRouteMetrics()
    renderRoute()
    ElMessage.success(`已将门店「${sName}」手动变更为：${newHp === 1 ? '🏠 本埠门店' : '🚗 外埠门店'}`)
  }
}

function recalculateRouteMetrics() {
  optRecalculateRouteMetrics(
    dailyResults.value,
    DAYS_LIST,
    depotLng.value,
    depotLat.value,
    Boolean(routeOptions.value?.return_to_depot)
  )
  if (selectedDay.value !== '全部' && dailyResults.value[selectedDay.value]) {
    result.value = dailyResults.value[selectedDay.value]
  }
}

function onDayChange() {
  selectedPointIndices.value = []
  highlightedRouteIdx.value = null
  // Restore the route result for the selected day, or null if not yet planned
  result.value = dailyResults.value[selectedDay.value] || null
  if (result.value?.routes) {
    expandedRouteIndices.value = new Set(result.value.routes.map((_, i) => i))
  } else {
    expandedRouteIndices.value = new Set()
  }
  renderRoute()
  mapPanel.value?.fitView()
  saveToLocalStorage()
}

// -------------------------------------------------------------
// Map Rendering Logic
// -------------------------------------------------------------
function renderRoute() {
  if (!amap.value || !mapPanel.value) return
  const A = amap.value

  const displayRoutes = currentDisplayRoutes.value
  const targetStores = selectedDay.value === '全部' ? points.value : activePoints.value
  const routedStoreSet = new Set(displayRoutes.flatMap((r) => r.stops || r.points || []))
  const unassigned = targetStores.filter((p) => !routedStoreSet.has(p) && !isStoreExpressOnDay(p, selectedDay.value))
  const currentExpress = (selectedDay.value === '全部')
    ? points.value.filter(p => isStoreExpressOnDay(p, '全部'))
    : points.value.filter(p => isStoreExpressOnDay(p, selectedDay.value))

  renderRouteMapLayers({
    amap: A,
    mapPanel: mapPanel.value,
    depot: { name: depotName.value || '中心仓', lng: Number(depotLng.value), lat: Number(depotLat.value) },
    routes: displayRoutes,
    allStores: points.value,
    expressStores: currentExpress,
    unassignedStores: unassigned,
    highlightedRouteIdx: highlightedRouteIdx.value,
    selectedPointIndices: selectedPointIndices.value || [],
    currentDay: selectedDay.value,
    openInfoWindowAt: (marker, html) => {
      const mapObj = mapPanel.value?.getMap()
      if (!mapObj) return
      const infoWindow = new A.InfoWindow({ content: html, offset: new A.Pixel(0, -18), closeWhenClickMap: true })
      infoWindow.open(mapObj, marker.getPosition())
    },
  })
}

// -------------------------------------------------------------
// Mouse Box Selection Tool
// -------------------------------------------------------------
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

      activePoints.value.forEach((p, idx) => {
        if (p.lng === '' || p.lat === '') return
        const pos = new A.LngLat(Number(p.lng), Number(p.lat))
        if (bounds.contains(pos)) {
          newSelected.push(idx)
        }
      })

      selectedPointIndices.value = newSelected
      mouseTool.close(true)
      isSelecting.value = false
      renderRoute()
      ElMessage.info(`框选了 ${newSelected.length} 家门店`)
    })
  })
}

function toggleBoxSelect() {
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
  renderRoute()
}

function applyBatchMoveRoute() {
  if (batchTargetRoute.value === '') return
  if (!result.value?.routes) return

  const target = batchTargetRoute.value
  const affectedRouteIndices = new Set()

  selectedPointIndices.value.forEach(idx => {
    // Find which route currently has idx
    result.value.routes.forEach((r, rIdx) => {
      const actualIndexInOrder = r.order.indexOf(idx)
      if (actualIndexInOrder >= 0) {
        r.order.splice(actualIndexInOrder, 1)
        affectedRouteIndices.add(rIdx)
      }
    })
    
    if (target === 'new') {
      const newRouteIdx = result.value.routes.length
      const newOrder = routeOptions.value.return_to_depot ? [-1, idx, -1] : [-1, idx]
      result.value.routes.push({
        truck_name: trucks.value[0]?.name || '4.2米厢车',
        order: newOrder,
        distance: 0,
        load: 0
      })
      affectedRouteIndices.add(newRouteIdx)
    } else {
      const targetIdx = Number(target)
      if (result.value.routes[targetIdx]) {
        if (routeOptions.value.return_to_depot && result.value.routes[targetIdx].order[result.value.routes[targetIdx].order.length - 1] === -1) {
          result.value.routes[targetIdx].order.splice(result.value.routes[targetIdx].order.length - 1, 0, idx)
        } else {
          result.value.routes[targetIdx].order.push(idx)
        }
        affectedRouteIndices.add(targetIdx)
      }
    }
  })

  // Optimize all affected routes using 2-Opt
  affectedRouteIndices.forEach(rIdx => {
    if (result.value.routes[rIdx]) {
      result.value.routes[rIdx].order = optimizeRouteOrder(result.value.routes[rIdx].order)
    }
  })

  selectedPointIndices.value = []
  batchTargetRoute.value = ''
  recalculateRouteMetrics()
  renderRoute()
  saveToLocalStorage()
  ElMessage.success('批量调整路线完成并已执行 2-Opt 路径优化！')
}

function batchDeletePoints() {
  const toDelete = new Set(selectedPointIndices.value)
  points.value = points.value.filter((_, idx) => !toDelete.has(idx))
  selectedPointIndices.value = []
  if (result.value) {
    result.value = null
  }
  renderRoute()
  saveToLocalStorage()
  ElMessage.success('已删除所选门店')
}

// -------------------------------------------------------------
// Excel Import Logic
// -------------------------------------------------------------
function triggerExcelImport() {
  if (excelFileInput.value) {
    excelFileInput.value.value = ''
    excelFileInput.value.click()
  }
}

async function handleExcelImport(e) {
  const file = e.target.files?.[0]
  if (!file) return

  try {
    const { points: parsedPoints, warnings } = await parseFileUniversal(file)
    if (!parsedPoints || !parsedPoints.length) {
      ElMessage.error('未能成功解析有效门店数据，请检查文件')
      return
    }

    if (warnings && warnings.length) {
      ElMessage.warning(`解析提示: ${warnings[0]}`)
    }

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
      delivery_days_str: p.delivery_days_str || (p.frequency >= 3 ? '周一,周三,周五' : '周一'),
      is_homepot: p.is_homepot !== undefined ? Number(p.is_homepot) : 1,
      is_express: Number(p.is_express) === 1 ? 1 : 0,
      service_time: p.service_time || 0.65,
      available_truck: p.available_truck || '',
      address: p.address || '',
    }))

    dataSourceLabel.value = `Excel 导入「${file.name}」`
    result.value = null
    dailyResults.value = {}
    localStorage.removeItem('routing_daily_results')
    localStorage.removeItem('routing_result')
    renderRoute()
    setTimeout(() => {
      mapPanel.value?.fitView()
    }, 200)
    saveToLocalStorage()
    ElMessage.success(`已成功导入 ${points.value.length} 家门店！可点击“⚡ 执行路线规划”开始计算。`)
  } catch (err) {
    ElMessage.error('Excel导入失败: ' + err.message)
  }
}

// -------------------------------------------------------------
// Excel Export Logic (包含常规路线与快递直发)
// -------------------------------------------------------------
const exportRoutingExcel = () => {
  exportRoutesToExcel({
    planName: '车辆路线规划方案',
    versionNumber: 1,
    stores: points.value,
    routes: currentDisplayRoutes.value,
    allWeekRoutes: allWeekRoutes.value,
  })
}

// -------------------------------------------------------------
// Solve VRP using solver
// -------------------------------------------------------------
async function solve() {
  errorMsg.value = ''
  if (activePoints.value.length < 1) {
    errorMsg.value = '当前筛选作业日下无计划配送门店，请切换作业日或导入数据'
    return
  }
  if (!depotLng.value || !depotLat.value) {
    errorMsg.value = '请确保配置了中心仓经纬度'
    return
  }

  loading.value = true
  try {
    if (selectedDay.value === '全部') {
      let totalPlannedRoutes = 0
      let totalPlannedDistance = 0.0
      let plannedDaysCount = 0

      for (const day of DAYS_LIST) {
        const dayPts = points.value.filter(p => p.delivery_days_str && p.delivery_days_str.includes(day) && !isStoreExpressOnDay(p, day))
        if (!dayPts.length) continue

        const reqPoints = [
          {
            name: depotName.value,
            lng: Number(depotLng.value),
            lat: Number(depotLat.value),
            is_depot: true,
            avg_loads: 0
          },
          ...dayPts.map(p => ({
            name: p.name,
            shop_code: p.shop_code || '',
            dept_id: p.dept_id || '',
            lng: Number(p.lng),
            lat: Number(p.lat),
            is_depot: false,
            avg_loads: Number(p.avg_loads || p.weight || 10),
            is_homepot: p.is_homepot !== undefined && p.is_homepot !== null ? Number(p.is_homepot) : 1
          }))
        ]

        const payload = {
          points: reqPoints,
          trucks: trucks.value,
          algorithm: 'ortools',
          options: routeOptions.value
        }

        const resp = await routingApi.solve(payload)
        const mappedRoutes = (resp.routes || []).map((r, rIdx) => {
          const storeIndices = (r.order || []).filter((idx) => idx !== -1)
          const routeStores = storeIndices.map((idx) => dayPts[idx]).filter(Boolean)
          const isHp = resolveHomepot(r, routeStores)
          return {
            ...r,
            day,
            day_route_idx: rIdx,
            route_title: `${day} 路线 ${rIdx + 1}`,
            truck_name: r.truck_name || `货车 ${rIdx + 1}`,
            vehicle_name: r.truck_name || `货车 ${rIdx + 1}`,
            is_homepot: isHp,
            return_to_depot: Boolean(routeOptions.value?.return_to_depot),
            points: routeStores,
            stops: routeStores,
            load: Math.round(Number(r.load || 0)),
            distance: Number((r.distance || 0).toFixed(1)),
            distance_km: Number((r.distance || 0).toFixed(1)),
          }
        })
        dailyResults.value[day] = {
          ...resp,
          routes: mappedRoutes,
          day,
        }
        totalPlannedRoutes += mappedRoutes.length
        totalPlannedDistance += resp.total_distance
        plannedDaysCount++
      }

      result.value = null
      renderRoute()
      mapPanel.value?.fitView()
      ElMessage.success(`全周批量路线规划完成！共规划 ${plannedDaysCount} 个作业日，生成 ${totalPlannedRoutes} 条配送路线，总里程 ${totalPlannedDistance.toFixed(1)} km。`)
      saveToLocalStorage()
    } else {
      const nonExpressActive = activePoints.value.filter(p => !isStoreExpressOnDay(p, selectedDay.value))
      if (nonExpressActive.length < 1) {
        errorMsg.value = '当前筛选作业日下所有门店均为快递直发，无需规划常规货车路线'
        result.value = { routes: [], total_distance: 0, total_stores: 0 }
        renderRoute()
        return
      }

      const reqPoints = [
        {
          name: depotName.value,
          lng: Number(depotLng.value),
          lat: Number(depotLat.value),
          is_depot: true,
          avg_loads: 0
        },
        ...nonExpressActive.map(p => ({
          name: p.name,
          shop_code: p.shop_code || '',
          dept_id: p.dept_id || '',
          lng: Number(p.lng),
          lat: Number(p.lat),
          is_depot: false,
          avg_loads: Number(p.avg_loads || p.weight || 10),
          is_homepot: p.is_homepot !== undefined && p.is_homepot !== null ? Number(p.is_homepot) : 1
        }))
      ]

      const payload = {
        points: reqPoints,
        trucks: trucks.value,
        algorithm: 'ortools',
        options: routeOptions.value
      }

      const resp = await routingApi.solve(payload)
      const mappedRoutes = (resp.routes || []).map((r, rIdx) => {
        const storeIndices = (r.order || []).filter((idx) => idx !== -1)
        const routeStores = storeIndices.map((idx) => nonExpressActive[idx]).filter(Boolean)
        const isHp = resolveHomepot(r, routeStores)
        return {
          ...r,
          day: selectedDay.value,
          day_route_idx: rIdx,
          route_title: `${selectedDay.value} 路线 ${rIdx + 1}`,
          truck_name: r.truck_name || `货车 ${rIdx + 1}`,
          vehicle_name: r.truck_name || `货车 ${rIdx + 1}`,
          is_homepot: isHp,
          return_to_depot: Boolean(routeOptions.value?.return_to_depot),
          points: routeStores,
          stops: routeStores,
          load: Math.round(Number(r.load || 0)),
          distance: Number((r.distance || 0).toFixed(1)),
          distance_km: Number((r.distance || 0).toFixed(1)),
        }
      })
      result.value = {
        ...resp,
        routes: mappedRoutes,
        day: selectedDay.value,
      }
      dailyResults.value[selectedDay.value] = result.value
      expandedRouteIndices.value = new Set(result.value.routes.map((_, i) => i))
      renderRoute()
      mapPanel.value?.fitView()
      ElMessage.success(`路线规划完成！共生成 ${mappedRoutes.length} 条配送路线，总里程 ${resp.total_distance.toFixed(1)} km。`)
      saveToLocalStorage()
    }
  } catch (e) {
    errorMsg.value = '路线规划失败: ' + (e.message || '系统异常')
    ElMessage.error(errorMsg.value)
  } finally {
    loading.value = false
  }
}

// -------------------------------------------------------------
// Save & History Handlers
// -------------------------------------------------------------
function openSaveModal() {
  planTitle.value = `路线规划方案_${selectedDay.value}_${new Date().toLocaleDateString()}`
  saveDialogVisible.value = true
}

async function handleSavePlan() {
  if (!points.value.length) return
  saving.value = true
  try {
    const payload = {
      title: planTitle.value || `路线规划方案_${selectedDay.value}`,
      depot_name: depotName.value,
      depot_lng: Number(depotLng.value),
      depot_lat: Number(depotLat.value),
      day: selectedDay.value,
      points: points.value,
      trucks: trucks.value,
      routes: result.value?.routes || [],
      daily_results: dailyResults.value,
      total_distance: result.value?.total_distance || 0.0,
      total_stores: result.value?.total_stores || activePoints.value.length
    }

    await routingApi.savePlan(payload)
    ElMessage.success('路线规划方案已成功保存至历史记录！')
    saveDialogVisible.value = false
  } catch (err) {
    ElMessage.error('保存方案失败: ' + err.message)
  } finally {
    saving.value = false
  }
}

function openHistoryModal() {
  historyDialogVisible.value = true
  fetchHistory()
}

async function fetchHistory() {
  loadingHistory.value = true
  try {
    if (historyTab.value === 'CANVAS') {
      const data = await canvasApi.list()
      historyList.value = (data || []).map((c) => ({
        ...c,
        task_id: c.canvas_id,
        is_canvas: true,
        task_type: 'CANVAS',
        save_type: `版本 V${c.current_version_number || 1}`,
        created_at: c.updated_at || c.created_at,
      }))
      return
    }

    const params = {}
    if (historyTab.value) params.task_type = historyTab.value
    if (historySaveType.value) params.save_type = historySaveType.value
    const data = await historyApi.list(params)
    historyList.value = data
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    loadingHistory.value = false
  }
}

function getPlanTitle(row) {
  if (row.is_canvas || row.task_type === 'CANVAS') {
    return `🎨 画布项目: ${row.name} (阶段: ${row.stage || 'ROUTED'})`
  }
  try {
    if (row.parameters) {
      const p = typeof row.parameters === 'string' ? JSON.parse(row.parameters) : row.parameters
      if (p.title) return p.title
    }
  } catch (e) {}
  return `规划任务 (${row.task_type || 'ROUTING'})`
}



async function loadHistoryData(row) {
  try {
    if (row.is_canvas || row.task_type === 'CANVAS') {
      loadingHistory.value = true
      const canvasDetail = await canvasApi.get(row.canvas_id)
      const curVersion = canvasDetail.current_version
      const snap = typeof curVersion?.snapshot_data === 'string' ? JSON.parse(curVersion.snapshot_data) : (curVersion?.snapshot_data || {})

      const storesList = snap.stores || snap.points || []
      if (!storesList.length) {
        ElMessage.warning('该画布暂无有效门店数据')
        return
      }

      points.value = storesList.map((s, idx) => ({
        name: s.name || `门店${idx + 1}`,
        shop_code: s.shop_code || '',
        dept_id: s.dept_id || '',
        district: s.district || '',
        warzone: s.warzone || '',
        lng: Number(s.lng !== undefined ? s.lng : (s.longitude !== undefined ? s.longitude : s.center_lng)),
        lat: Number(s.lat !== undefined ? s.lat : (s.latitude !== undefined ? s.latitude : s.center_lat)),
        avg_loads: Number(s.avg_loads || s.weight || s.demand || 10),
        frequency: Number(s.frequency || 1),
        delivery_days_str: s.schedule_day || s.delivery_days_str || (Number(s.frequency || 1) >= 3 ? '周一,周三,周五' : '周一'),
        is_homepot: s.is_homepot !== undefined ? Number(s.is_homepot) : 1,
        is_express: Number(s.is_express) === 1 ? 1 : 0,
        service_time: s.service_time || 0.65,
        available_truck: s.available_truck || '',
        address: s.address || '',
      }))

      if (canvasDetail.depot_name || snap.depot?.name) depotName.value = canvasDetail.depot_name || snap.depot?.name
      if (canvasDetail.depot_lng || snap.depot?.lng) depotLng.value = Number(canvasDetail.depot_lng || snap.depot?.lng)
      if (canvasDetail.depot_lat || snap.depot?.lat) depotLat.value = Number(canvasDetail.depot_lat || snap.depot?.lat)

      // Restore routing results with points hydration
      const routingData = snap.routing_data || {}
      const dailyRes = routingData.daily_results || snap.daily_results || {}
      if (Object.keys(dailyRes).length) {
        const hydratedDaily = {}
        DAYS_LIST.forEach((d) => {
          if (dailyRes[d]?.routes) {
            const dayPts = points.value.filter(p => (p.delivery_days_str || '').includes(d) && !isStoreExpressOnDay(p, d))
            hydratedDaily[d] = {
              ...dailyRes[d],
              day: d,
              routes: hydrateRoutePoints(dailyRes[d].routes, dayPts.length ? dayPts : points.value, { defaultReturnToDepot: routeOptions.value?.return_to_depot })
            }
          }
        })
        dailyResults.value = hydratedDaily
        selectedDay.value = '全部'
        result.value = null
      } else {
        dailyResults.value = {}
        result.value = null
      }

      renderRoute()
      if (points.value.length) mapPanel.value?.fitView()
      dataSourceLabel.value = `画布项目「${canvasDetail.name}」`
      saveToLocalStorage()
      historyDialogVisible.value = false
      ElMessage.success(`已成功载入画布工作台项目【${canvasDetail.name}】（共 ${points.value.length} 家门店）！`)
      return
    }

    if (!row.result && !row.parameters) {
      ElMessage.warning('该历史记录中无有效数据')
      return
    }
    const resData = row.result ? (typeof row.result === 'string' ? JSON.parse(row.result) : row.result) : {}
    const paramData = row.parameters ? (typeof row.parameters === 'string' ? JSON.parse(row.parameters) : row.parameters) : {}

    let pts = []
    if (Array.isArray(resData.points) && resData.points.length) {
      pts = resData.points
    } else if (Array.isArray(resData.stores) && resData.stores.length) {
      pts = resData.stores
    } else if (Array.isArray(paramData.points) && paramData.points.length) {
      pts = paramData.points
    } else if (Array.isArray(paramData.stores) && paramData.stores.length) {
      pts = paramData.stores
    }

    if (pts.length) {
      // Query DB stores to guarantee exact is_homepot synchronization
      const dbMap = new Map()
      try {
        const dbList = await storeApi.list()
        dbList.forEach(s => {
          if (s.shop_code) dbMap.set(String(s.shop_code).trim(), Number(s.is_homepot))
          if (s.name) dbMap.set(String(s.name).trim(), Number(s.is_homepot))
        })
      } catch (e) {}

      points.value = pts.map((p, idx) => {
        const code = p.shop_code ? String(p.shop_code).trim() : ''
        const name = p.name ? String(p.name).trim() : (p.shop_name ? String(p.shop_name).trim() : '')
        
        let isHp = p.is_homepot !== undefined && p.is_homepot !== null ? Number(p.is_homepot) : undefined
        if (isHp === undefined) {
          if (dbMap.has(code)) {
            isHp = dbMap.get(code)
          } else if (dbMap.has(name)) {
            isHp = dbMap.get(name)
          } else {
            isHp = 1
          }
        }

        return {
          name: p.name || p.shop_name || `门店${idx + 1}`,
          shop_code: p.shop_code || '',
          dept_id: p.dept_id || '',
          district: p.district || '',
          warzone: p.warzone || '',
          lng: Number(p.lng !== undefined ? p.lng : (p.longitude !== undefined ? p.longitude : p.center_lng)),
          lat: Number(p.lat !== undefined ? p.lat : (p.latitude !== undefined ? p.latitude : p.center_lat)),
          avg_loads: Number(p.avg_loads || p.weight || 10),
          frequency: Number(p.frequency || 1),
          delivery_days_str: p.delivery_days_str || (Number(p.frequency || 1) >= 3 ? '周一,周三,周五' : '周一'),
          is_homepot: isHp,
          service_time: p.service_time || 0.65,
          available_truck: p.available_truck || '',
          address: p.address || '',
        }
      })
    }

    if (resData.depot_name || paramData.depot_name) depotName.value = resData.depot_name || paramData.depot_name
    if (resData.depot_lng || paramData.depot_lng) depotLng.value = Number(resData.depot_lng || paramData.depot_lng)
    if (resData.depot_lat || paramData.depot_lat) depotLat.value = Number(resData.depot_lat || paramData.depot_lat)
    if (resData.trucks && Array.isArray(resData.trucks)) trucks.value = resData.trucks

    if (row.task_type === 'ROUTING' && resData.routes && Array.isArray(resData.routes)) {
      const day = resData.day || paramData.day || selectedDay.value || '周一'
      if (day && day !== '全部') {
        selectedDay.value = day
      }

      const dayPts = points.value.filter(p => (p.delivery_days_str || '').includes(selectedDay.value) && !isStoreExpressOnDay(p, selectedDay.value))
      const hydratedRoutes = hydrateRoutePoints(resData.routes, dayPts.length ? dayPts : points.value, { defaultReturnToDepot: routeOptions.value?.return_to_depot })

      result.value = {
        algorithm: resData.algorithm || algorithm.value,
        routes: hydratedRoutes,
        total_distance: resData.total_distance || 0.0,
        total_stores: resData.total_stores || points.value.length,
        points: points.value
      }

      if (resData.daily_results && Object.keys(resData.daily_results).length) {
        const hydratedDaily = {}
        DAYS_LIST.forEach((d) => {
          if (resData.daily_results[d]?.routes) {
            const dPts = points.value.filter(p => (p.delivery_days_str || '').includes(d) && !isStoreExpressOnDay(p, d))
            hydratedDaily[d] = {
              ...resData.daily_results[d],
              day: d,
              routes: hydrateRoutePoints(resData.daily_results[d].routes, dPts.length ? dPts : points.value, { defaultReturnToDepot: routeOptions.value?.return_to_depot })
            }
          }
        })
        dailyResults.value = hydratedDaily
      } else {
        dailyResults.value = { [selectedDay.value]: result.value }
      }
      expandedRouteIndices.value = new Set(result.value.routes.map((_, i) => i))
    } else {
      result.value = null
      dailyResults.value = {}
    }

    renderRoute()
    if (points.value.length) {
      mapPanel.value?.fitView()
    }
    dataSourceLabel.value = `历史方案「${getPlanTitle(row)}」`
    saveToLocalStorage()
    historyDialogVisible.value = false
    const typeLabel = row.task_type === 'CLUSTER_SCHEDULE' ? '门店排班方案' : '路线规划方案'
    ElMessage.success(`已成功载入历史${typeLabel}（共 ${points.value.length} 家门店）！`)
  } catch (err) {
    ElMessage.error('载入方案失败: ' + err.message)
  }
}

function saveToLocalStorage() {
  function safeSet(key, val) {
    try {
      localStorage.setItem(key, typeof val === 'string' ? val : JSON.stringify(val))
    } catch (e) {
      console.warn(`[LocalStorage] 写入 ${key} 超出容量配额，尝试安全瘦身与降级存储:`, e)
      try {
        // 对全周/单日规划大对象进行坐标序列瘦身（剔除数万个经纬度点构成的 amap_path 等冗余字段）
        if (key === 'routing_daily_results' && typeof val === 'object' && val) {
          const slimDaily = {}
          Object.keys(val).forEach(day => {
            const d = val[day]
            if (!d) return
            slimDaily[day] = {
              algorithm: d.algorithm,
              total_distance: d.total_distance,
              total_stores: d.total_stores,
              routes: (d.routes || []).map(r => ({
                truck_name: r.truck_name,
                order: r.order,
                distance: r.distance,
                load: r.load,
                is_homepot: r.is_homepot,
                amap_distance: r.amap_distance,
                amap_duration: r.amap_duration,
                amap_tolls: r.amap_tolls
              }))
            }
          })
          localStorage.setItem(key, JSON.stringify(slimDaily))
          return
        } else if (key === 'routing_result' && typeof val === 'object' && val) {
          const slimRes = {
            algorithm: val.algorithm,
            total_distance: val.total_distance,
            total_stores: val.total_stores,
            routes: (val.routes || []).map(r => ({
              truck_name: r.truck_name,
              order: r.order,
              distance: r.distance,
              load: r.load,
              is_homepot: r.is_homepot,
              amap_distance: r.amap_distance,
              amap_duration: r.amap_duration,
              amap_tolls: r.amap_tolls
            }))
          }
          localStorage.setItem(key, JSON.stringify(slimRes))
          return
        }
      } catch (e2) {
        console.warn(`[LocalStorage] 瘦身写入 ${key} 仍然超限，安全移除旧缓存:`, e2)
        try {
          localStorage.removeItem(key)
        } catch(e3) {}
      }
    }
  }

  safeSet('routing_points', points.value)
  safeSet('routing_savedAt', new Date().toISOString())
  safeSet('routing_result', result.value)
  safeSet('routing_daily_results', dailyResults.value)
  safeSet('routing_algorithm', algorithm.value)
  safeSet('routing_selectedDay', selectedDay.value)
  safeSet('routing_trucks', trucks.value)
  safeSet('routing_depotName', depotName.value)
  safeSet('routing_depotLng', String(depotLng.value))
  safeSet('routing_depotLat', String(depotLat.value))
}

const fetchDepots = async () => {
  try {
    depotList.value = await depotApi.list()
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
    renderRoute()
    saveToLocalStorage()
  }
}

const onDepotCustomChange = () => {
  renderRoute()
  saveToLocalStorage()
}

async function loadRoutingData() {
  try {
    if (!amap.value && mapPanel.value) {
      amap.value = await (mapPanel.value.whenReady ? mapPanel.value.whenReady() : mapPanel.value.getAmap())
    }
  } catch (e) {}

  initMouseTool()

  // Restore last-edited points from localStorage
  const savedPts = localStorage.getItem('routing_points')
    if (savedPts) {
      try { points.value = JSON.parse(savedPts) } catch(e){}
    }
    const savedDay = localStorage.getItem('routing_selectedDay')
    if (savedDay) selectedDay.value = savedDay

    const savedDaily = localStorage.getItem('routing_daily_results')
    if (savedDaily) {
      try {
        const parsedDaily = JSON.parse(savedDaily)
        const hydratedDaily = {}
        DAYS_LIST.forEach((d) => {
          if (parsedDaily[d]?.routes) {
            const dPts = points.value.filter(p => (p.delivery_days_str || '').includes(d) && !isStoreExpressOnDay(p, d))
            hydratedDaily[d] = {
              ...parsedDaily[d],
              day: d,
              routes: hydrateRoutePoints(parsedDaily[d].routes, dPts.length ? dPts : points.value, { defaultReturnToDepot: routeOptions.value?.return_to_depot })
            }
          }
        })
        dailyResults.value = hydratedDaily
      } catch(e){}
    }

    const savedRes = localStorage.getItem('routing_result')
    if (dailyResults.value[selectedDay.value]) {
      result.value = dailyResults.value[selectedDay.value]
    } else if (savedRes) {
      try {
        const parsedRes = JSON.parse(savedRes)
        const dPts = points.value.filter(p => (p.delivery_days_str || '').includes(selectedDay.value) && !isStoreExpressOnDay(p, selectedDay.value))
        result.value = {
          ...parsedRes,
          routes: hydrateRoutePoints(parsedRes.routes || [], dPts.length ? dPts : points.value, { defaultReturnToDepot: routeOptions.value?.return_to_depot })
        }
      } catch(e){}
    } else {
      result.value = null
    }

    if (result.value?.routes) {
      expandedRouteIndices.value = new Set(result.value.routes.map((_, i) => i))
    }

    const savedAlg = localStorage.getItem('routing_algorithm')
    if (savedAlg) algorithm.value = savedAlg
    const savedTrucks = localStorage.getItem('routing_trucks')
    if (savedTrucks) {
      try { trucks.value = JSON.parse(savedTrucks) } catch(e){}
    }
    const savedName = localStorage.getItem('routing_depotName')
    if (savedName) depotName.value = savedName
    const savedLng = localStorage.getItem('routing_depotLng')
    if (savedLng) depotLng.value = Number(savedLng)
    const savedLat = localStorage.getItem('routing_depotLat')
    if (savedLat) depotLat.value = Number(savedLat)

    await fetchDepots()

  if (points.value.length) {
    const savedAt = localStorage.getItem('routing_savedAt')
    const dateStr = savedAt ? new Date(savedAt).toLocaleDateString() : ''
    dataSourceLabel.value = dateStr ? `上次编辑（${dateStr}）` : '上次编辑'
    ElMessage.info(`已恢复上次编辑的 ${points.value.length} 家门店${dateStr ? `（${dateStr}）` : ''}`)
  }

  // 3. Load default DC from backend if not set
  if (!depotLng.value) {
    try {
      const d = await depotApi.getDefault()
      if (d) {
        depotName.value = d.name
        depotLng.value = Number(d.lng || d.longitude)
        depotLat.value = Number(d.lat || d.latitude)
      }
    } catch(e){}
  }

  // 4. Auto-sync is_homepot with database stores if available
  if (points.value.length) {
    try {
      const dbList = await storeApi.list()
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
    } catch (e) {}
  }

  setTimeout(() => {
    renderRoute()
    if (points.value.length) {
      mapPanel.value?.fitView()
    }
  }, 300)
}

onMounted(async () => {
  await loadRoutingData()
})

watch(
  () => [route.path, route.query.t],
  ([newPath]) => {
    if (newPath === '/routing/plan') {
      loadRoutingData()
    }
  }
)

onBeforeUnmount(() => {
  delete window.updateStoreRoute
  delete window.updateStoreExpress
  delete window.updateStoreExpressDay
  delete window.updateStoreHomepot
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

.fleet-tag {
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.remove-tag-btn {
  color: #94a3b8;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
}
.remove-tag-btn:hover {
  color: #ef4444;
}

.summary-stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 12px;
}

.stat-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 8px;
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
}

.stat-val small {
  font-size: 11px;
  font-weight: normal;
  color: #64748b;
}

.route-card-item {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-left-width: 4px;
  border-radius: 6px;
  padding: 10px;
  transition: all 0.2s ease;
  cursor: pointer;
}

.route-card-item:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.route-card-item.is-highlighted {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border-color: #0284c7;
  background: #f0f9ff;
}

.route-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.route-color-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.route-title {
  font-weight: 700;
  font-size: 13px;
}

.truck-tag {
  background: #f1f5f9;
  color: #475569;
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
}

.route-metrics {
  font-size: 12px;
  color: #475569;
}

.route-metrics .divider {
  margin: 0 4px;
  color: #cbd5e1;
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
  background: transparent;
  border: none;
  color: #0284c7;
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
  padding: 0;
}

.route-stores-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
  border-top: 1px dashed #e2e8f0;
  padding-top: 6px;
}

.route-store-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8fafc;
  padding: 4px 6px;
  border-radius: 4px;
  border: 1px solid #f1f5f9;
  font-size: 11px;
}

.store-seq-info {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  max-width: 65%;
}

.seq-badge {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 700;
  flex-shrink: 0;
}

.store-name-text {
  font-weight: 600;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
}

.store-demand-text {
  color: #64748b;
  font-size: 10px;
}

.transfer-select {
  font-size: 10px;
  padding: 2px 4px;
  border-radius: 4px;
  border: 1px solid #cbd5e1;
  background: white;
  color: #475569;
  max-width: 95px;
}
</style>
