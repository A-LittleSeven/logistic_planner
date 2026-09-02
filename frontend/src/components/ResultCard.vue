<template>
  <transition name="fade">
    <div v-if="visible" class="lp-card result-card">
      <h3 class="result-title">
        <span class="dot"></span>{{ title }}
      </h3>
      <slot />
    </div>
  </transition>
</template>

<script setup>
defineProps({
  title: { type: String, default: '结果' },
  visible: { type: Boolean, default: true },
})
</script>

<style scoped>
.result-card {
  border-left: 3px solid var(--primary);
}
.result-title {
  font-size: 15px;
  margin-bottom: 12px;
  color: var(--primary-dark);
  display: flex;
  align-items: center;
  gap: 8px;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--hero-gradient);
}
.fade-enter-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
.fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
</style>
