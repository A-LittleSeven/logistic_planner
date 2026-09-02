<template>
  <el-dialog
    :model-value="visible"
    title="重命名画布"
    width="400px"
    @update:model-value="$emit('update:visible', $event)"
  >
    <el-input
      :model-value="name"
      placeholder="请输入画布名称"
      @update:model-value="$emit('update:name', $event)"
    />
    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" @click="$emit('submit')">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
defineProps({
  visible: { type: Boolean, default: false },
  name: { type: String, default: '' },
})

defineEmits(['update:visible', 'update:name', 'submit'])
</script>
