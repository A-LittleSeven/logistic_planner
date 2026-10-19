<template>
  <div class="stat-card" :class="[`layout-${layout}`, `theme-${theme}`]">
    <!-- Horizontal Icon (if horizontal layout) -->
    <div v-if="layout === 'horizontal' && (icon || $slots.icon)" class="stat-icon" :style="iconStyle">
      <slot name="icon">
        <el-icon :size="20">
          <component :is="icon" />
        </el-icon>
      </slot>
    </div>

    <!-- Info Block -->
    <div class="stat-info">
      <div class="stat-label">
        <slot name="label">{{ label }}</slot>
      </div>
      <div class="stat-value" :style="valueStyle">
        <slot name="value">
          {{ value }}
          <span v-if="unit" class="stat-unit">{{ unit }}</span>
        </slot>
      </div>
      <div v-if="subText || $slots.sub" class="stat-sub">
        <slot name="sub">{{ subText }}</slot>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, default: '' },
  value: { type: [String, Number], default: '' },
  unit: { type: String, default: '' },
  subText: { type: String, default: '' },
  layout: { type: String, default: 'horizontal' }, // 'horizontal' | 'vertical'
  icon: { type: [Object, Function, String], default: null },
  iconBg: { type: String, default: '' },
  iconColor: { type: String, default: '' },
  valueColor: { type: String, default: '' },
  valueSize: { type: String, default: '' },
  theme: { type: String, default: 'default' }, // default, blue, green, amber, purple
})

const iconStyle = computed(() => {
  const styles = {}
  if (props.iconBg) styles.backgroundColor = props.iconBg
  if (props.iconColor) styles.color = props.iconColor
  return styles
})

const valueStyle = computed(() => {
  const styles = {}
  if (props.valueColor) styles.color = props.valueColor
  if (props.valueSize) styles.fontSize = props.valueSize
  return styles
})
</script>

<style scoped>
.stat-card {
  background: var(--card-bg);
  border-radius: var(--radius);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
  transition: var(--transition-fast);
}

.stat-card:hover {
  border-color: var(--border-strong);
}

/* Horizontal Layout (Default for CanvasListView etc.) */
.stat-card.layout-horizontal {
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
}

.stat-card.layout-horizontal .stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.stat-card.layout-horizontal .stat-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.stat-card.layout-horizontal .stat-label {
  font-size: 12px;
  color: var(--text-muted);
}

.stat-card.layout-horizontal .stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  margin-top: 2px;
  line-height: 1.2;
}

/* Vertical Layout (For StoreManage etc.) */
.stat-card.layout-vertical {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
}

.stat-card.layout-vertical .stat-label {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.stat-card.layout-vertical .stat-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}

.stat-unit {
  font-size: 13px;
  font-weight: 400;
  color: var(--text-light);
  margin-left: 2px;
}

.stat-sub {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

/* Presets for theme colors */
.theme-blue.layout-horizontal .stat-icon { background: #e0f2fe; color: #0284c7; }
.theme-blue.layout-vertical .stat-value { color: #0284c7; }

.theme-green.layout-horizontal .stat-icon { background: #f0fdf4; color: #16a34a; }
.theme-green.layout-vertical .stat-value { color: #16a34a; }

.theme-amber.layout-horizontal .stat-icon { background: #fef3c7; color: #d97706; }
.theme-amber.layout-vertical .stat-value { color: #d97706; }

.theme-purple.layout-horizontal .stat-icon { background: #f3e8ff; color: #9333ea; }
.theme-purple.layout-vertical .stat-value { color: #7c3aed; }
</style>
