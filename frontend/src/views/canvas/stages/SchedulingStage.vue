<template>
  <div class="stage-content-scroll">
    <div class="panel-section">
      <h3 class="section-title">📅 门店周作业日排班规划</h3>
      <p class="section-desc">
        在店群分组基础上，执行按周配送作业日（周一至周日）智能平滑排班。
      </p>
    </div>

    <!-- Status Banner -->
    <div class="panel-card" :style="{ background: hasScheduleComputed ? '#f0fdf4' : '#f0f9ff', borderColor: hasScheduleComputed ? '#bbf7d0' : '#bae6fd' }">
      <div style="display: flex; align-items: flex-start; gap: 8px; font-size: 12px; line-height: 1.5;">
        <span style="font-size: 16px;">{{ hasScheduleComputed ? '✅' : '📍' }}</span>
        <div>
          <strong :style="{ color: hasScheduleComputed ? '#14532d' : '#0369a1' }">
            {{ hasScheduleComputed ? '已完成全周排班规划' : (isScheduleOutdated ? '店群规划已更新 (请重新执行排班)' : '店群规划已完成 (默认展示店群分布)') }}
          </strong>
          <div :style="{ color: hasScheduleComputed ? '#15803d' : '#0284c7', fontSize: '11px', marginTop: '2px' }">
            {{ hasScheduleComputed 
              ? '地图已自动切换为周排班作业日色彩，可按星期筛选查看单日分布。' 
              : (isScheduleOutdated ? '店群划分发生变更，上一次排班方案已失效，请点击下方按钮重新求解全周均衡排班。' : `当前地图默认展示 ${clusteringResult?.clusters?.length || 0} 个店群。执行排班后将自动切换为排班色彩。`) }}
          </div>
        </div>
      </div>
    </div>

    <div class="panel-card">
      <div class="form-group">
        <label class="form-label">按配送作业日筛选查看</label>
        <el-select v-model="selectedScheduleDay" style="width: 100%;" @change="$emit('render-map')">
          <el-option label="周一配送门店" value="周一" />
          <el-option label="周二配送门店" value="周二" />
          <el-option label="周三配送门店" value="周三" />
          <el-option label="周四配送门店" value="周四" />
          <el-option label="周五配送门店" value="周五" />
          <el-option label="周六配送门店" value="周六" />
          <el-option label="周日配送门店" value="周日" />
          <el-option label="全部时间 (全周总览)" value="全部" />
        </el-select>
      </div>

      <div style="margin-top: 10px; font-size: 12px; color: #64748b; display: flex; justify-content: space-between;">
        <span>当前筛选门店: <strong>{{ activeScheduleStores.length }}</strong> / {{ stores.length }} 家</span>
        <span v-if="selectedScheduleDay !== '全部'" style="font-weight: 600; color: #0284c7;">
          {{ selectedScheduleDay }}货量: {{ activeDayLoad }} 箱
        </span>
      </div>
    </div>

    <div class="panel-card">
      <div style="display: flex; gap: 8px; margin-bottom: 8px;">
        <el-button
          type="primary"
          style="flex: 1;"
          :loading="schedulingLoading"
          @click="handleRunScheduling"
        >
          {{ schedulingLoading ? '排班求解中…' : '⚡ 执行智能全周均衡排班' }}
        </el-button>
        <el-button
          plain
          title="排班参数设置"
          @click="$emit('open-schedule-config')"
          style="padding: 0 12px; font-size: 14px;"
        >
          ⚙️
        </el-button>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
        <el-button
          :type="isSelecting ? 'danger' : 'default'"
          plain
          @click="$emit('toggle-box-select')"
        >
          {{ isSelecting ? '取消框选' : '📐 框选设配送日' }}
        </el-button>
        <el-button plain @click="activeStage = 'routing'; $emit('render-map', true);">
          进入路线规划 ➔
        </el-button>
      </div>
    </div>

    <!-- Box Select Batch Operation Card for Stage 2 -->
    <div
      v-if="selectedPointIndices.length"
      class="panel-card"
      style="border: 2px solid #0d9488; background: #f0fdfa;"
    >
      <div class="sub-header" style="color: #0d9488;">
        <span>已框选 {{ selectedPointIndices.length }} 家门店</span>
        <el-button link size="small" @click="selectedPointIndices = []; $emit('render-map');">×</el-button>
      </div>
      <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 6px;">
        <label style="font-size: 11px; font-weight: 600; color: #475569;">批量设置计划配送作业日：</label>
        <div style="display: flex; gap: 6px;">
          <el-select v-model="batchTargetDay" size="small" placeholder="选择作业日模式" style="flex: 1;">
            <el-option-group v-for="g in SCHEDULE_PATTERNS" :key="g.label" :label="g.label">
              <el-option v-for="opt in g.options" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-option-group>
          </el-select>
          <el-button type="primary" size="small" :disabled="!batchTargetDay" @click="applyBatchScheduleDay">
            应用排班
          </el-button>
        </div>
      </div>
    </div>

    <!-- Daily Schedule Distribution Stats -->
    <div class="panel-card">
      <ScheduleBalanceCard
        :stores="stores"
        :selected-day="selectedScheduleDay"
        @select-day="(d) => { selectedScheduleDay = d; $emit('render-map'); }"
      />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useCanvasState } from '../composables/useCanvasState.js'
import { clusteringApi } from '../../../api/client.js'
import ScheduleBalanceCard from '../../../components/planning/ScheduleBalanceCard.vue'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['render-map', 'toggle-box-select', 'open-schedule-config'])

const {
  canvas,
  activeStage,
  stores,
  clusteringResult,
  scheduleResult,
  selectedScheduleDay,
  isScheduleOutdated,
  scheduleOptions,
  isSelecting,
  selectedPointIndices,
  hasScheduleComputed,
  activeScheduleStores,
  activeDayLoad,
  invalidateDownstreamStagesFromScheduling,
} = useCanvasState()

const schedulingLoading = ref(false)
const batchTargetDay = ref('')

const SCHEDULE_PATTERNS = [
  {
    label: '1 次/周 配送',
    options: [
      { label: '周一配送', value: '周一' },
      { label: '周二配送', value: '周二' },
      { label: '周三配送', value: '周三' },
      { label: '周四配送', value: '周四' },
      { label: '周五配送', value: '周五' },
      { label: '周六配送', value: '周六' },
      { label: '周日配送', value: '周日' },
    ],
  },
  {
    label: '2 次/周 配送',
    options: [
      { label: '周一, 周四', value: '周一,周四' },
      { label: '周二, 周五', value: '周二,周五' },
      { label: '周三, 周六', value: '周三,周六' },
    ],
  },
  {
    label: '3 次/周 配送',
    options: [
      { label: '周一, 周三, 周五', value: '周一,周三,周五' },
      { label: '周二, 周四, 周六', value: '周二,周四,周六' },
    ],
  },
  {
    label: '6 次/周 配送',
    options: [
      { label: '周一至周六全部配送', value: '周一,周二,周三,周四,周五,周六' },
    ],
  },
]

const handleRunScheduling = async () => {
  if (stores.value.length < 2) {
    ElMessage.warning('规划门店数量不足')
    return
  }
  schedulingLoading.value = true
  try {
    const formattedPoints = stores.value.map((s, idx) => {
      const clusterInfo = clusteringResult.value?.clusters?.find((c) => c.cluster_id === s.cluster_id)
      return {
        ...s,
        name: s.name || `门店${idx + 1}`,
        shop_code: s.shop_code || '',
        dept_id: s.dept_id || '',
        district: s.district || '',
        warzone: s.warzone || '',
        address: s.address || '',
        service_time: s.service_time || 0.65,
        available_truck: s.available_truck || '',
        lng: Number(s.lng),
        lat: Number(s.lat),
        avg_loads: Number(s.avg_loads || 10),
        frequency: Number(s.frequency || 1),
        is_homepot: s.is_homepot !== undefined ? Number(s.is_homepot) : 0,
        cluster_id: s.cluster_id !== undefined && s.cluster_id !== null ? Number(s.cluster_id) : 0,
        cluster_center_id: s.cluster_id !== undefined && s.cluster_id !== null ? Number(s.cluster_id) : 0,
        center_lng: clusterInfo?.center?.lng ? Number(clusterInfo.center.lng) : Number(s.lng),
        center_lat: clusterInfo?.center?.lat ? Number(clusterInfo.center.lat) : Number(s.lat),
        cdist_warehouse: clusterInfo?.cdist_warehouse ? Number(clusterInfo.cdist_warehouse) : 0.0,
        sdist_warehouse: s.sdist_warehouse ? Number(s.sdist_warehouse) : 0.0,
        delivery_days_str: s.delivery_days_str || s.schedule_day || '',
      }
    })

    const payload = {
      points: formattedPoints,
      depot_lng: Number(canvas.depot_lng || 108.36654),
      depot_lat: Number(canvas.depot_lat || 22.81700),
      algorithm: 'cluster_balanced',
      options: scheduleOptions.value,
    }

    const res = await clusteringApi.solveSchedule(payload)
    scheduleResult.value = res

    if (res.points) {
      res.points.forEach((p, idx) => {
        if (stores.value[idx]) {
          const daysStr = p.delivery_days_str || p.schedule_day || p.delivery_day || '周一'
          stores.value[idx].delivery_days_str = daysStr
          stores.value[idx].schedule_day = daysStr
          stores.value[idx].frequency = Number(p.frequency || daysStr.split(',').length || 1)
        }
      })
    }

    invalidateDownstreamStagesFromScheduling('全周排班重新求解')
    ElMessage.success('🎉 全周智能排班求解完成，下游路线规划数据已刷新为待规划状态！')
    emit('render-map')
  } catch (err) {
    ElMessage.error(`排班求解失败: ${err.message}`)
  } finally {
    schedulingLoading.value = false
  }
}

const applyBatchScheduleDay = () => {
  if (!batchTargetDay.value || !selectedPointIndices.value.length) return
  const targetFreq = batchTargetDay.value.split(',').filter(Boolean).length
  let updatedCount = 0
  let skippedCount = 0

  selectedPointIndices.value.forEach((idx) => {
    const s = stores.value[idx]
    if (!s) return
    const storeFreq = Math.round(Number(s.frequency || 1))
    if (storeFreq === targetFreq) {
      s.delivery_days_str = batchTargetDay.value
      s.schedule_day = batchTargetDay.value
      updatedCount++
    } else {
      skippedCount++
    }
  })

  if (updatedCount > 0) {
    invalidateDownstreamStagesFromScheduling('批量设置排班')
  }
  if (updatedCount > 0 && skippedCount === 0) {
    ElMessage.success(`已为选中的 ${updatedCount} 家门店批量应用排班: ${batchTargetDay.value}，下游路线规划数据已同步刷新！`)
  } else if (updatedCount > 0 && skippedCount > 0) {
    ElMessage.warning(`已为 ${updatedCount} 家频次为 ${targetFreq} 次的门店应用排班，跳过了 ${skippedCount} 家频次不一致的门店`)
  } else {
    ElMessage.error(`未匹配到频次为 ${targetFreq} 次/周 的门店（框选门店的频次属性与所选模式不匹配）`)
  }
  selectedPointIndices.value = []
  batchTargetDay.value = ''
  emit('render-map')
}
</script>

