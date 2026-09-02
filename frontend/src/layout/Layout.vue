<template>
  <el-container class="layout-container">
    <el-header class="header">
      <div class="logo">
        <el-icon style="margin-right: 10px; font-size: 22px; vertical-align: middle; color: #38bdf8;"><Van /></el-icon>
        <span class="logo-text">智能物流调度系统</span>
        <span class="system-tag">Enterprise</span>
      </div>
      <div class="header-right">
        <span class="status-indicator"></span>
        <span class="status-text">系统正常运行</span>
      </div>
    </el-header>
    
    <el-container class="main-container">
      <el-aside width="220px" class="aside">
        <el-menu
          :default-active="activeMenu"
          router
          class="side-menu"
          background-color="#ffffff"
          text-color="#334155"
          active-text-color="#0284c7"
        >
          <!-- 0. 核心规划画布 -->
          <div class="menu-group-header">
            <el-icon><DataAnalysis /></el-icon>
            <span>规划画布</span>
          </div>
          <el-menu-item index="/canvas">
            <el-icon><Collection /></el-icon>
            <span>画布工作台</span>
          </el-menu-item>
          <el-menu-item index="/history">
            <el-icon><Timer /></el-icon>
            <span>历史记录</span>
          </el-menu-item>

          <div class="menu-divider"></div>

          <!-- 1. 高级工具 (单步独立规划, 与画布三步流水线功能重叠, 默认收起) -->
          <div class="menu-group-header menu-group-toggle" @click="advancedOpen = !advancedOpen">
            <el-icon><Connection /></el-icon>
            <span>高级工具</span>
            <el-icon class="toggle-arrow" :class="{ 'is-open': advancedOpen }"><ArrowDown /></el-icon>
          </div>
          <template v-if="advancedOpen">
            <el-menu-item index="/clustering/plan">
              <el-icon><Location /></el-icon>
              <span>门店分组</span>
            </el-menu-item>
            <el-menu-item index="/clustering/schedule">
              <el-icon><Calendar /></el-icon>
              <span>门店排班</span>
            </el-menu-item>
            <el-menu-item index="/routing/plan">
              <el-icon><Compass /></el-icon>
              <span>路线规划</span>
            </el-menu-item>
          </template>

          <div class="menu-divider"></div>

          <!-- 3. 用户配置 (已移动至系统管理上方) -->
          <div class="menu-group-header">
            <el-icon><Setting /></el-icon>
            <span>用户配置</span>
          </div>
          <el-menu-item index="/config/store">
            <el-icon><Shop /></el-icon>
            <span>门店维护</span>
          </el-menu-item>
          <el-menu-item index="/config/vehicle">
            <el-icon><Van /></el-icon>
            <span>车型维护</span>
          </el-menu-item>
          <el-menu-item index="/config/depot">
            <el-icon><OfficeBuilding /></el-icon>
            <span>起点管理</span>
          </el-menu-item>

          <div class="menu-divider"></div>

          <!-- 4. 系统管理 -->
          <div class="menu-group-header">
            <el-icon><Tools /></el-icon>
            <span>系统管理</span>
          </div>
          <el-menu-item index="/settings">
            <el-icon><Setting /></el-icon>
            <span>系统设置</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      
      <el-main class="main-content" :class="{ 'is-map-view': isMapView }">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = ref('')

// 高级工具分组默认收起; 当前页面在该分组内时自动展开
const ADVANCED_PATHS = ['/clustering/plan', '/clustering/schedule', '/routing/plan']
const advancedOpen = ref(false)

const isMapView = computed(() => {
  return [
    '/clustering/plan',
    '/clustering/schedule',
    '/routing/plan',
  ].includes(route.path) || route.path.startsWith('/canvas/workspace')
})

watch(
  () => route.path,
  (newPath) => {
    if (newPath.startsWith('/canvas/workspace')) {
      activeMenu.value = '/canvas'
    } else {
      activeMenu.value = newPath
    }
    if (ADVANCED_PATHS.some((p) => newPath.startsWith(p))) {
      advancedOpen.value = true
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.layout-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #f8fafc;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: #0f172a;
  color: white;
  padding: 0 24px;
  height: 52px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  -webkit-app-region: drag; /* 允许在 macOS 隐藏标题栏时拖动窗口 */
}

.logo {
  font-size: 17px;
  font-weight: 700;
  color: #f8fafc;
  display: flex;
  align-items: center;
  letter-spacing: 0.5px;
}

.logo-text {
  background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.system-tag {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  background: rgba(56, 189, 248, 0.15);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.3);
  padding: 1px 6px;
  border-radius: 4px;
  margin-left: 10px;
  letter-spacing: 0.5px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #94a3b8;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.6);
}

.main-container {
  flex: 1;
  overflow: hidden;
}

.aside {
  background-color: #ffffff;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.aside::-webkit-scrollbar {
  width: 4px;
}
.aside::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 2px;
}

.side-menu {
  border-right: none;
  flex: 1;
  padding: 8px 0;
}

.menu-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px 4px;
  font-size: 11px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.menu-group-toggle {
  cursor: pointer;
  user-select: none;
  padding-bottom: 4px;
}

.menu-group-toggle:hover {
  color: #64748b;
}

.toggle-arrow {
  margin-left: auto;
  font-size: 12px;
  transition: transform 0.2s ease;
  transform: rotate(-90deg);
}

.toggle-arrow.is-open {
  transform: rotate(0deg);
}

.menu-divider {
  height: 1px;
  background: #f1f5f9;
  margin: 8px 12px;
}

.side-menu :deep(.el-menu-item) {
  font-weight: 500;
  border-radius: 6px;
  margin: 2px 8px;
  height: 40px;
  line-height: 40px;
  font-size: 13px;
}

.side-menu :deep(.el-menu-item.is-active) {
  background-color: #e0f2fe !important;
  color: #0284c7 !important;
  font-weight: 600;
}

.main-content {
  background-color: #f8fafc;
  padding: 20px;
  overflow-y: auto;
}

.main-content.is-map-view {
  padding: 0 !important;
  overflow: hidden !important;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
