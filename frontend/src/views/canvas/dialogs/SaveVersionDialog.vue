<template>
  <el-dialog
    :model-value="visible"
    title="💾 保存为新版本 (Version Snapshot)"
    width="520px"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:visible', $event)"
  >
    <el-form label-position="top">
      <el-form-item label="版本名称 / 标识" required>
        <el-input
          :model-value="versionName"
          :placeholder="`例如：V${(currentVersionNumber || 1) + 1} - 优化南宁核心区排班与路径`"
          @update:model-value="$emit('update:versionName', $event)"
        />
      </el-form-item>
      <el-form-item label="变更摘要说明 / 操作日志" required>
        <el-input
          :model-value="changeSummary"
          type="textarea"
          :rows="3"
          placeholder="简述本次增删改内容（如：执行了KMeans聚类划分为6个店群，微调了2号店群门店，全周排班负载已平滑）"
          @update:model-value="$emit('update:changeSummary', $event)"
        />
      </el-form-item>
    </el-form>
    <div style="font-size: 12px; color: #64748b; background: #f8fafc; padding: 8px 12px; border-radius: 6px;">
      💡 保存后将在数据库中生成全新的不可变版本快照，随时可回溯或对比。
    </div>
    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="$emit('submit')">
        确认保存新版本
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
defineProps({
  visible: { type: Boolean, default: false },
  versionName: { type: String, default: '' },
  changeSummary: { type: String, default: '' },
  currentVersionNumber: { type: Number, default: 1 },
  loading: { type: Boolean, default: false },
})

defineEmits(['update:visible', 'update:versionName', 'update:changeSummary', 'submit'])
</script>
