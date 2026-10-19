<template>
  <div class="app-page-header">
    <div class="header-left">
      <div v-if="icon || $slots.icon" class="header-icon-box">
        <slot name="icon">
          <el-icon v-if="icon" :size="22">
            <component :is="icon" />
          </el-icon>
        </slot>
      </div>
      <div class="header-text">
        <h2 class="app-page-title">
          {{ title }}
          <slot name="title-extra" />
        </h2>
        <p v-if="subtitle || $slots.subtitle" class="app-page-subtitle">
          <slot name="subtitle">{{ subtitle }}</slot>
        </p>
      </div>
    </div>
    <div v-if="$slots.actions || $slots.default" class="header-actions">
      <slot name="actions">
        <slot />
      </slot>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    default: '',
  },
  icon: {
    type: [Object, Function, String],
    default: null,
  },
})
</script>

<style scoped>
.app-page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-width: 0;
}

.header-icon-box {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-lg);
  background: var(--primary-soft);
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.header-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.app-page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 4px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.app-page-subtitle {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
  line-height: 1.5;
  max-width: 900px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  flex-wrap: wrap;
}
</style>
