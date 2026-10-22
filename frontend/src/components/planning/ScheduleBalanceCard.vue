<template>
  <div class="schedule-balance-container">
    <div class="sub-header" style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
      <span style="font-size: 13px; font-weight: 700; color: #334155;">
        全周每日配送运量分布
      </span>
      <span style="font-size: 11px; color: #64748b;">
        全周总装载: <strong style="color: #10b981;">{{ totalWeeklyLoads }}</strong> 箱
      </span>
    </div>

    <div v-if="!hasScheduledStores" class="empty-schedule-hint">
      <div style="font-size: 22px; margin-bottom: 4px;">📅</div>
      <div style="font-size: 12px; font-weight: 600; color: #475569;">暂无有效排班数据</div>
      <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">店群规划已更新，请点击上方按钮求解全周均衡排班</div>
    </div>

    <div v-else class="daily-stat-bars">
      <div
        v-for="d in DAYS"
        :key="d"
        class="daily-stat-row"
        :class="{ active: selectedDay === d }"
        @click="$emit('select-day', selectedDay === d ? '全部' : d)"
      >
        <div class="day-info-left">
          <span class="day-dot" :style="{ background: DAY_COLORS[d] }"></span>
          <span class="day-label">{{ d }}</span>
        </div>

        <div class="bar-track">
          <div
            class="bar-fill"
            :style="{ width: getDayLoadPercent(d) + '%', background: DAY_COLORS[d] }"
          ></div>
        </div>

        <div class="day-val">
          <strong>{{ getDayStoreCount(d) }}</strong>店 / <strong style="color: #0284c7;">{{ getDayTotalLoad(d) }}</strong>箱
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { DAYS, DAY_COLORS } from '../../utils/mapMarkers.js'

const props = defineProps({
  stores: {
    type: Array,
    default: () => [],
  },
  selectedDay: {
    type: String,
    default: '全部',
  },
})

defineEmits(['select-day'])

const getDayStoreCount = (day) => {
  return props.stores.filter((s) => {
    const dStr = s.schedule_day || s.delivery_days_str || ''
    return dStr.includes(day)
  }).length
}

const getDayTotalLoad = (day) => {
  const dayStores = props.stores.filter((s) => {
    const dStr = s.schedule_day || s.delivery_days_str || ''
    return dStr.includes(day)
  })
  const sum = dayStores.reduce((acc, s) => {
    const avg = Number(s.avg_loads || s.weight || s.demand || 10)
    return acc + avg
  }, 0)
  return Math.round(sum)
}

const maxDayLoad = computed(() => {
  let maxVal = 1
  DAYS.forEach((d) => {
    const l = getDayTotalLoad(d)
    if (l > maxVal) maxVal = l
  })
  return maxVal
})

const getDayLoadPercent = (day) => {
  const l = getDayTotalLoad(day)
  return Math.min(100, Math.round((l / (maxDayLoad.value || 1)) * 100))
}

const hasScheduledStores = computed(() => {
  return Array.isArray(props.stores) && props.stores.some((s) => Boolean(s.schedule_day || s.delivery_days_str))
})

const totalWeeklyLoads = computed(() => {
  if (!hasScheduledStores.value) return 0
  return props.stores.reduce((acc, s) => {
    const avg = Number(s.avg_loads || s.weight || s.demand || 10)
    const freq = Math.max(1, Number(s.frequency || 1))
    return acc + avg * freq
  }, 0)
})
</script>

<style scoped>
.schedule-balance-container {
  display: flex;
  flex-direction: column;
}

.empty-schedule-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 18px 12px;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 6px;
  text-align: center;
}

.daily-stat-bars {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.daily-stat-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  font-size: 12px;
}

.daily-stat-row:hover {
  background: #f0f9ff;
  border-color: #bae6fd;
}

.daily-stat-row.active {
  background: #e0f2fe;
  border-color: #0284c7;
  box-shadow: 0 0 0 1px #0284c7;
}

.day-info-left {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 50px;
}

.day-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.day-label {
  font-weight: 700;
  color: #1e293b;
  font-size: 12px;
}

.bar-track {
  flex: 1;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.day-val {
  font-size: 11px;
  color: #475569;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  text-align: right;
  min-width: 100px;
}
</style>
