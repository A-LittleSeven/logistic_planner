<template>
  <div v-if="clusters && clusters.length" class="cluster-result-container">
    <div class="sub-header" style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
      <span style="font-size: 13px; font-weight: 700; color: #334155;">
        店群汇总 (共 {{ clusters.length }} 个店群)
      </span>
      <span style="font-size: 11px; color: #64748b;">
        总门店: {{ totalStoresCount }} 家
      </span>
    </div>

    <div class="cluster-summary-list">
      <div
        v-for="c in clusters"
        :key="c.cluster_id"
        class="cluster-card-item"
        :class="{ 'is-highlighted': Number(highlightedClusterId) === Number(c.cluster_id) }"
        :style="{ borderLeftColor: getColor(c.cluster_id) }"
        @click="$emit('toggle-highlight', c.cluster_id)"
      >
        <div class="cluster-card-header">
          <div style="display: flex; align-items: center; gap: 6px;">
            <span class="legend-dot" :style="{ background: getColor(c.cluster_id) }"></span>
            <span class="cluster-title" :style="{ color: getColor(c.cluster_id) }">
              店群 {{ Number(c.cluster_id) + 1 }}
            </span>
          </div>
          <span class="cluster-size-tag">{{ c.size }} 家门店</span>
        </div>

        <div class="cluster-card-body">
          <span>总装载: <strong>{{ getClusterLoad(c.cluster_id) }}</strong> 箱</span>
          <span v-if="c.cdist_warehouse !== undefined && c.cdist_warehouse !== null">
            距仓: <strong>{{ Number(c.cdist_warehouse).toFixed(1) }}</strong> km
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  clusters: {
    type: Array,
    default: () => [],
  },
  stores: {
    type: Array,
    default: () => [],
  },
  highlightedClusterId: {
    type: [Number, String],
    default: null,
  },
  getClusterColor: {
    type: Function,
    default: null,
  },
})

defineEmits(['toggle-highlight'])

const DEFAULT_COLORS = [
  '#0284c7', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4',
  '#84cc16', '#d97706', '#6366f1', '#14b8a6', '#f43f5e', '#a855f7',
]

const getColor = (clusterId) => {
  if (props.getClusterColor) {
    return props.getClusterColor(clusterId)
  }
  return DEFAULT_COLORS[Number(clusterId) % DEFAULT_COLORS.length]
}

const totalStoresCount = computed(() => {
  return props.clusters.reduce((acc, c) => acc + (Number(c.size) || 0), 0)
})

const getClusterLoad = (clusterId) => {
  if (!props.stores || !props.stores.length) return 0
  const cStores = props.stores.filter((s) => Number(s.cluster_id) === Number(clusterId))
  const sum = cStores.reduce((acc, s) => {
    const avg = Number(s.avg_loads || s.weight || s.demand || 10)
    return acc + avg
  }, 0)
  return Math.round(sum)
}
</script>

<style scoped>
.cluster-result-container {
  display: flex;
  flex-direction: column;
}

.cluster-summary-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 340px;
  overflow-y: auto;
  padding-right: 2px;
}

.cluster-card-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-left-width: 4px;
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

.cluster-title {
  font-weight: 700;
  font-size: 13px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.cluster-size-tag {
  font-size: 11px;
  background: #e2e8f0;
  color: #334155;
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
</style>
