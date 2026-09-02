<template>
  <el-dialog
    :model-value="visible"
    title="⚙️ 求解器参数设置 (OR-Tools CVRP)"
    width="520px"
    destroy-on-close
    :append-to-body="true"
    @update:model-value="$emit('update:visible', $event)"
  >
    <el-form label-width="160px" label-position="left" style="padding: 4px 10px;">
      <el-form-item label="单车装载率上限">
        <div style="display: flex; align-items: center; gap: 12px; width: 100%;">
          <el-slider v-model="localOptions.max_capacity_rate" :min="0.5" :max="1.2" :step="0.01" style="flex: 1;" />
          <span style="font-weight: 700; width: 45px; text-align: right; color: #0284c7;">
            {{ Math.round(localOptions.max_capacity_rate * 100) }}%
          </span>
        </div>
        <div style="font-size: 11px; color: #94a3b8; line-height: 1.4;">(max_capacity_rate) 车辆满载率目标上限，默认 110%</div>
      </el-form-item>

      <el-form-item label="求解器耗时上限">
        <div style="display: flex; align-items: center; gap: 8px;">
          <el-input-number v-model="localOptions.time_limit_seconds" :min="1" :max="300" :step="1" />
          <span style="font-size: 12px; color: #64748b;">秒</span>
        </div>
        <div style="font-size: 11px; color: #94a3b8; line-height: 1.4; margin-top: 2px;">(time_limit_seconds) 求解器最大允许计算时间，默认 60 秒</div>
      </el-form-item>

      <el-form-item label="配送完成返回中心仓">
        <el-switch
          v-model="localOptions.return_to_depot"
          active-text="返回中心仓 (闭环配送)"
          inactive-text="不返回 (以末站为终点)"
        />
        <div style="font-size: 11px; color: #94a3b8; line-height: 1.4; margin-top: 2px;">
          (return_to_depot) 设为否时，路线以最后一家配送门店为终点，不计算返回仓库的里程
        </div>
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
  localStorage.setItem('canvas_route_options', JSON.stringify(localOptions.value))
  ElMessage.info('路线求解器参数已恢复默认值')
}

const save = () => {
  emit('update:options', { ...localOptions.value })
  localStorage.setItem('canvas_route_options', JSON.stringify(localOptions.value))
  emit('update:visible', false)
  ElMessage.success('路线求解器参数已保存！')
}
</script>
