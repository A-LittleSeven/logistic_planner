<template>
  <el-dialog
    :model-value="visible"
    title="⚙️ 运筹调度算法参数设置 (TruckSchedule)"
    width="560px"
    destroy-on-close
    :append-to-body="true"
    @update:model-value="$emit('update:visible', $event)"
  >
    <el-form label-width="160px" label-position="left" style="padding: 4px 10px;">
      <el-form-item label="目标最大装载率">
        <div style="display: flex; align-items: center; gap: 12px; width: 100%;">
          <el-slider v-model="localOptions.max_truck_capacity_rate" :min="0.5" :max="1.0" :step="0.01" style="flex: 1;" />
          <span style="font-weight: 700; width: 45px; text-align: right; color: #0284c7;">
            {{ Math.round(localOptions.max_truck_capacity_rate * 100) }}%
          </span>
        </div>
        <div style="font-size: 11px; color: #94a3b8; line-height: 1.4;">(max_truck_capacity_rate) 单车装载货量上限目标比例，默认 96%</div>
      </el-form-item>

      <el-form-item label="局部搜索邻居簇数">
        <el-input-number v-model="localOptions.search_n_neighbor" :min="1" :max="10" />
        <div style="font-size: 11px; color: #94a3b8; line-height: 1.4; margin-top: 2px;">(search_n_neighbor) 搜索跨相邻店群串点优化时的邻居簇数量，默认 1</div>
      </el-form-item>

      <el-form-item label="最大允许绕路距离">
        <div style="display: flex; align-items: center; gap: 8px;">
          <el-input-number v-model="localOptions.detour_thres" :min="10" :max="2000" :step="50" />
          <span style="font-size: 12px; color: #64748b;">km</span>
        </div>
        <div style="font-size: 11px; color: #94a3b8; line-height: 1.4; margin-top: 2px;">(detour_thres) 串点规划时允许的最大折返绕路距离，默认 500 km</div>
      </el-form-item>

      <el-form-item label="临近店判定阈值">
        <el-input-number v-model="localOptions.dist_thres" :min="0.1" :max="5.0" :step="0.1" />
        <div style="font-size: 11px; color: #94a3b8; line-height: 1.4; margin-top: 2px;">(dist_thres) 判断门店是否同属紧密片区的相对距离系数，默认 0.9</div>
      </el-form-item>

      <el-form-item label="单程最大跨度">
        <div style="display: flex; align-items: center; gap: 8px;">
          <el-input-number v-model="localOptions.one_way_dist_max" :min="5" :max="300" :step="5" />
          <span style="font-size: 12px; color: #64748b;">km</span>
        </div>
        <div style="font-size: 11px; color: #94a3b8; line-height: 1.4; margin-top: 2px;">(one_way_dist_max) 同一路线上相邻两店最大允许直线距离，默认 40 km</div>
      </el-form-item>

      <el-form-item label="周作业排班天数">
        <el-select v-model="localOptions.work_days" style="width: 200px;">
          <el-option label="6 天 (周一 ~ 周六)" :value="6" />
          <el-option label="7 天 (周一 ~ 周日)" :value="7" />
          <el-option label="5 天 (周一 ~ 周五)" :value="5" />
        </el-select>
        <div style="font-size: 11px; color: #94a3b8; line-height: 1.4; margin-top: 2px;">(work_days) 均衡排班算法循环分配作业日的总周期天数</div>
      </el-form-item>
    </el-form>

    <template #footer>
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <el-button @click="resetDefaults">恢复默认值</el-button>
        <div>
          <el-button @click="$emit('update:visible', false)">取消</el-button>
          <el-button type="primary" @click="save">保存参数</el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  visible: { type: Boolean, default: false },
  options: { type: Object, default: () => ({}) },
  defaultOptions: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:visible', 'update:options'])

const localOptions = ref({ ...props.options })

watch(
  () => props.options,
  (val) => {
    localOptions.value = { ...val }
  },
  { deep: true }
)

const resetDefaults = () => {
  localOptions.value = { ...props.defaultOptions }
  localStorage.setItem('canvas_schedule_options', JSON.stringify(localOptions.value))
  ElMessage.info('排班参数已恢复默认值')
}

const save = () => {
  emit('update:options', { ...localOptions.value })
  localStorage.setItem('canvas_schedule_options', JSON.stringify(localOptions.value))
  emit('update:visible', false)
  ElMessage.success('排班算法参数已保存！')
}
</script>
