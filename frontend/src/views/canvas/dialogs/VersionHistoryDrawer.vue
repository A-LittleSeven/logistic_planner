<template>
  <el-drawer
    :model-value="visible"
    title="⏱️ 画布演进版本历史 (Version Timeline)"
    size="450px"
    @update:model-value="$emit('update:visible', $event)"
  >
    <div class="version-timeline-container">
      <div class="timeline-intro">
        在同一个画布中，所有的增删改都在前一版本基础上递进。点击可随时载入历史快照。
      </div>

      <el-timeline style="margin-top: 16px;">
        <el-timeline-item
          v-for="v in versionList"
          :key="v.id"
          :type="v.id === currentVersion?.id ? 'primary' : ''"
          :hollow="v.id !== currentVersion?.id"
          :timestamp="formatTime(v.created_at)"
          placement="top"
        >
          <div class="timeline-version-card" :class="{ 'is-current': v.id === currentVersion?.id }">
            <div class="tv-header">
              <span class="tv-tag">V{{ v.version_number }}</span>
              <span class="tv-name">{{ v.version_name }}</span>
              <el-tag v-if="v.id === currentVersion?.id" size="small" type="success">当前激活</el-tag>
            </div>
            <p class="tv-desc">{{ v.change_summary || '无详细说明' }}</p>
            <div class="tv-actions">
              <el-button
                size="small"
                type="primary"
                plain
                :disabled="v.id === currentVersion?.id"
                @click="$emit('rollback', v)"
              >
                {{ v.id === currentVersion?.id ? '正在使用' : '载入/切换此版本' }}
              </el-button>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>
    </div>
  </el-drawer>
</template>

<script setup>
defineProps({
  visible: { type: Boolean, default: false },
  versionList: { type: Array, default: () => [] },
  currentVersion: { type: Object, default: null },
})

defineEmits(['update:visible', 'rollback'])

const formatTime = (timeStr) => {
  if (!timeStr) return '--'
  const d = new Date(timeStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.version-timeline-container {
  padding: 4px;
}

.timeline-intro {
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
  background: #f8fafc;
  padding: 10px;
  border-radius: 6px;
}

.timeline-version-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.timeline-version-card.is-current {
  border-color: #38bdf8;
  background: #f0f9ff;
}

.tv-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.tv-tag {
  font-size: 13px;
  font-weight: 700;
  color: #0284c7;
}

.tv-name {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
  flex: 1;
}

.tv-desc {
  font-size: 12px;
  color: #64748b;
  margin: 0 0 10px 0;
  line-height: 1.4;
}

.tv-actions {
  display: flex;
  justify-content: flex-end;
}
</style>
