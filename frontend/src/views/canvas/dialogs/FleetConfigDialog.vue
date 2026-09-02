<template>
  <el-dialog
    :model-value="visible"
    title="配置规划车型与运力池 (系统维护车型)"
    width="680px"
    destroy-on-close
    :append-to-body="true"
    @update:model-value="$emit('update:visible', $event)"
  >
    <div style="font-size: 12px; color: #64748b; margin-bottom: 12px; background: #f8fafc; padding: 8px 12px; border-radius: 6px;">
      💡 运力池车型统一来源于「车型维护」基础数据，请在下方勾选本次规划可用的车型并配置出动台数。
    </div>

    <el-table :data="systemVehicles" v-loading="loading" border stripe size="small" max-height="340px">
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
            :max="row.available_count || 100"
            :disabled="!row.selected"
            size="small"
            style="width: 100px;"
          />
        </template>
      </el-table-column>
    </el-table>

    <template #footer>
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 12px; color: #64748b;">
          已勾选 <strong>{{ selectedCount }}</strong> 种系统车型
        </span>
        <div>
          <el-button @click="$emit('update:visible', false)">取消</el-button>
          <el-button type="primary" @click="handleConfirm">确认选用并应用</el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { vehicleApi } from '../../../api/client.js'
import { ElMessage } from 'element-plus'

const props = defineProps({
  visible: { type: Boolean, default: false },
  trucks: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:visible', 'update:trucks'])

const systemVehicles = ref([])
const loading = ref(false)

const selectedCount = computed(() => systemVehicles.value.filter((v) => v.selected).length)

const fetchVehicles = async () => {
  loading.value = true
  try {
    const list = await vehicleApi.list()
    systemVehicles.value = list.map((v) => {
      const match = props.trucks.find((t) => t.vehicle_code === v.vehicle_code || t.name === v.name)
      return {
        ...v,
        selected: !!match,
        count: match ? match.count : (v.name?.includes('4.2') ? 20 : Math.min(v.available_count || 5, 20)),
      }
    })
  } catch (err) {
    ElMessage.error(err.message || '获取系统车型失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => props.visible,
  (val) => {
    if (val) {
      fetchVehicles()
    }
  }
)

const handleConfirm = () => {
  const selected = systemVehicles.value.filter((v) => v.selected)
  if (!selected.length) {
    ElMessage.warning('请至少勾选一种系统已维护的车型')
    return
  }

  const updatedTrucks = selected.map((v) => ({
    vehicle_code: v.vehicle_code,
    name: v.name,
    capacity: Number(v.capacity_weight),
    count: Number(v.count || 1),
    cost_per_km: Number(v.cost_per_km || 0),
  }))

  emit('update:trucks', updatedTrucks)
  emit('update:visible', false)
  ElMessage.success(`已选用 ${updatedTrucks.length} 种系统维护车型！`)
}
</script>
