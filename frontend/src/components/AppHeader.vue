<template>
  <header class="app-header">
    <div class="brand">
      <span class="brand-mark">LP</span>
      <span class="brand-name">物流规划选址系统</span>
    </div>
    <nav class="nav">
      <router-link to="/location" class="nav-link">物流选址</router-link>
      <router-link to="/routing" class="nav-link">路线规划</router-link>
      <router-link to="/clustering" class="nav-link">店群规划</router-link>
    </nav>
  </header>
</template>

<script setup></script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  height: 64px;
  background: var(--hero-gradient);
  color: #fff;
  box-shadow: var(--shadow-md);
  position: relative;
  z-index: 10;
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(6px);
  font-family: var(--font-serif);
  font-weight: 700;
  letter-spacing: 0.02em;
}
.brand-name {
  font-family: var(--font-serif);
  font-size: 19px;
  font-weight: 600;
  letter-spacing: 0.04em;
}
.nav {
  display: flex;
  gap: 4px;
}
.nav-link {
  padding: 8px 18px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.85);
  transition: var(--transition);
}
.nav-link:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.12);
}
.nav-link.router-link-active {
  color: #fff;
  background: rgba(255, 255, 255, 0.22);
  font-weight: 600;
}
</style>
