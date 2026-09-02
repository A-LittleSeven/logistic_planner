<template>
  <div class="stage-content-scroll">
    <div class="panel-section">
      <h3 class="section-title">📍 门店店群分组规划</h3>
      <p class="section-desc">
        根据地理位置与运量属性进行算法分群。可在地图上点击门店直接调区或微调属性。
      </p>
    </div>

    <div class="panel-card">
      <div class="form-group">
        <label class="form-label">分组规划策略</label>
        <el-select v-model="clusteringAlgorithm" style="width: 100%;">
          <el-option label="智能约束分组求解 (容量与距离约束)" value="kmeans" />
          <el-option label="行政区划归属分组 (纯行政区归属)" value="district" />
          <el-option label="行政区扩展拆分分组 (行政区合并与拆分)" value="district_extension" />
        </el-select>
      </div>

      <div v-if="clusteringAlgorithm === 'kmeans'" class="form-group" style="margin-top: 10px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <label class="form-label">目标店群数 K</label>
          <el-input-number v-model="clusteringK" :min="1" :max="50" size="small" />
        </div>
      </div>

      <div v-if="clusteringAlgorithm === 'district_extension'" style="margin-top: 10px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
        <div class="form-group">
          <label class="form-label">最小规模</label>
          <el-input-number v-model="minZoneSize" :min="1" size="small" style="width: 100%;" />
        </div>
        <div class="form-group">
          <label class="form-label">最大规模</label>
          <el-input-number v-model="maxZoneSize" :min="1" size="small" style="width: 100%;" />
        </div>
      </div>
    </div>

    <div class="panel-card">
      <el-button
        type="primary"
        style="width: 100%; margin-bottom: 8px;"
        :loading="clusteringLoading"
        @click="handleRunClustering"
      >
        {{ clusteringLoading ? '店群计算中…' : '⚡ 执行智能店群聚类' }}
      </el-button>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
        <el-button
          :type="isSelecting ? 'danger' : 'default'"
          plain
          @click="$emit('toggle-box-select')"
        >
          {{ isSelecting ? '取消框选' : '📐 框选批量调区' }}
        </el-button>
        <el-button plain @click="activeStage = 'scheduling'; $emit('render-map', true);">
          进入周排班 ➔
        </el-button>
      </div>
    </div>

    <!-- Box Select Batch Operation Card for Stage 1 -->
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
        <label style="font-size: 11px; font-weight: 600; color: #475569;">批量调区到目标店群：</label>
        <div style="display: flex; gap: 6px;">
          <el-select v-model="batchTargetCluster" size="small" placeholder="选择目标店群" style="flex: 1;">
            <el-option
              v-for="c in clusteringResult?.clusters || []"
              :key="c.cluster_id"
              :label="`店群 ${c.cluster_id + 1} (${c.size} 家)`"
              :value="c.cluster_id"
            />
            <el-option label="+ 新建并加入新店群" value="new" />
          </el-select>
          <el-button type="primary" size="small" :disabled="batchTargetCluster === ''" @click="applyBatchMoveCluster">
            应用调区
          </el-button>
        </div>
      </div>
    </div>

    <!-- Clustering Results Overview -->
    <div v-if="clusteringResult?.clusters?.length" class="panel-card">
      <ClusterResultList
        :clusters="clusteringResult.clusters"
        :stores="stores"
        :get-cluster-color="getClusterColor"
      />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useCanvasState } from '../composables/useCanvasState.js'
import { clusteringApi } from '../../../api/client.js'
import ClusterResultList from '../../../components/planning/ClusterResultList.vue'
import { CLUSTER_COLORS } from '../../../utils/mapMarkers.js'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['render-map', 'toggle-box-select'])

const {
  canvas,
  activeStage,
  stores,
  clusteringResult,
  clusteringAlgorithm,
  clusteringK,
  minZoneSize,
  maxZoneSize,
  isSelecting,
  selectedPointIndices,
  recalculateClusterMetrics,
  invalidateDownstreamStagesFromClustering,
} = useCanvasState()

const clusteringLoading = ref(false)
const batchTargetCluster = ref('')

const getClusterColor = (cId) => CLUSTER_COLORS[(cId || 0) % CLUSTER_COLORS.length]

const handleRunClustering = async () => {
  if (stores.value.length < 2) {
    ElMessage.warning('规划门店数量不足 2 家')
    return
  }
  clusteringLoading.value = true
  try {
    const formattedPoints = stores.value.map((s, idx) => ({
      name: s.name || `门店${idx + 1}`,
      shop_code: s.shop_code || '',
      district: s.district || '',
      lng: Number(s.lng),
      lat: Number(s.lat),
      avg_loads: Number(s.avg_loads || s.weight || 10),
      frequency: Number(s.frequency || 1),
      is_homepot: s.is_homepot !== undefined ? Number(s.is_homepot) : 0,
      cluster_id: s.cluster_id,
      schedule_day: s.schedule_day,
    }))

    const payload = {
      points: formattedPoints,
      k: Math.max(1, Number(clusteringK.value || 1)),
      algorithm: clusteringAlgorithm.value || 'kmeans',
      depot_lng: Number(canvas.depot_lng || 108.36654),
      depot_lat: Number(canvas.depot_lat || 22.81700),
      options: {
        min_zone_size: Number(minZoneSize.value || 5),
        max_zone_size: Number(maxZoneSize.value || 30),
      },
    }

    const res = await clusteringApi.solve(payload)
    clusteringResult.value = res

    if (res.points && res.points.length === stores.value.length) {
      res.points.forEach((p, idx) => {
        stores.value[idx].cluster_id = p.cluster_id
        stores.value[idx].sdist_warehouse = p.sdist_warehouse
        stores.value[idx].cdist_warehouse = p.cdist_warehouse
      })
    } else if (res.assignments) {
      stores.value.forEach((s, idx) => {
        s.cluster_id = res.assignments[idx]
      })
    }

    invalidateDownstreamStagesFromClustering('店群聚类已重新计算')
    ElMessage.success(`🎉 智能店群聚类成功（共 ${res.clusters?.length || 0} 个店群），下游周排班与路线规划数据已刷新为初始待规划状态！`)
    emit('render-map')
  } catch (err) {
    ElMessage.error(`聚类计算失败: ${err.message}`)
  } finally {
    clusteringLoading.value = false
  }
}

const applyBatchMoveCluster = () => {
  if (batchTargetCluster.value === '' || !selectedPointIndices.value.length) return
  const targetVal = batchTargetCluster.value
  let targetClusterId

  if (targetVal === 'new') {
    const existingClusters = clusteringResult.value?.clusters || []
    targetClusterId = existingClusters.length
  } else {
    targetClusterId = Number(targetVal)
  }

  selectedPointIndices.value.forEach((idx) => {
    if (stores.value[idx]) {
      stores.value[idx].cluster_id = targetClusterId
    }
  })

  const clustersFound = new Set(stores.value.map((s) => s.cluster_id).filter((c) => c !== undefined && c !== null))
  const clusterList = Array.from(clustersFound)
    .sort((a, b) => Number(a) - Number(b))
    .map((cId) => {
      const cStores = stores.value.filter((s) => s.cluster_id === cId)
      return {
        cluster_id: cId,
        name: `店群 ${Number(cId) + 1}`,
        size: cStores.length,
      }
    })

  clusteringResult.value = {
    clusters: clusterList,
    total_stores: stores.value.length,
    k: clusterList.length,
  }

  recalculateClusterMetrics()
  invalidateDownstreamStagesFromClustering('店群批量调区')
  ElMessage.success(`已成功将 ${selectedPointIndices.value.length} 家门店调至店群 ${targetClusterId + 1}，下游周排班与路线数据已同步刷新！`)
  selectedPointIndices.value = []
  batchTargetCluster.value = ''
  emit('render-map')
}
</script>

<style scoped>
.stage-content-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.panel-section {
  margin-bottom: 2px;
}

.section-title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 4px 0;
}

.section-desc {
  font-size: 11px;
  color: #64748b;
  margin: 0;
  line-height: 1.4;
}

.panel-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 11px;
  font-weight: 600;
  color: #475569;
}

.sub-header {
  font-size: 12px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
