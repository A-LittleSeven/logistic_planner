<template>
  <div class="view-layout" ref="layoutRef" :class="{ 'is-resizing': isResizing }">
    <!-- Left Sidebar Panel -->
    <aside 
      class="side-panel" 
      :class="{ 'is-collapsed': isCollapsed }"
      :style="{ width: isCollapsed ? '0px' : sideWidth + 'px' }"
    >
      <div class="side-panel-inner" :style="{ width: sideWidth + 'px' }">
        <slot name="side" />
      </div>
    </aside>

    <!-- Resizer Handle & Quick Collapse Toggle -->
    <div class="resize-handle-wrapper">
      <div 
        class="resize-handle" 
        @mousedown="startResize" 
        title="拖拽调整侧边栏宽度"
      ></div>
      
      <!-- Collapse / Expand Toggle Button -->
      <button 
        class="collapse-toggle-btn" 
        @click="toggleCollapse"
        :title="isCollapsed ? '展开面板' : '收起面板 (全屏地图)'"
      >
        <svg 
          viewBox="0 0 24 24" 
          width="12" 
          height="12" 
          stroke="currentColor" 
          stroke-width="2.5" 
          fill="none" 
          stroke-linecap="round" 
          stroke-linejoin="round"
          :class="{ 'icon-rotated': isCollapsed }"
        >
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
      </button>
    </div>

    <!-- Main Map Workspace Area -->
    <section class="map-area">
      <slot name="map" />
    </section>

    <slot />
  </div>
</template>

<script setup>
import { ref } from 'vue'

const sideWidth = ref(440)
const lastWidth = ref(440)
const isCollapsed = ref(false)
const isResizing = ref(false)
const layoutRef = ref(null)

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
  if (!isCollapsed.value && sideWidth.value < 300) {
    sideWidth.value = lastWidth.value || 440
  }
  
  // Smoothly dispatch resize events during transition
  const interval = setInterval(() => {
    window.dispatchEvent(new Event('resize'))
  }, 50)
  setTimeout(() => {
    clearInterval(interval)
    window.dispatchEvent(new Event('resize'))
  }, 320)
}

function startResize(e) {
  if (isCollapsed.value) {
    isCollapsed.value = false
  }
  
  e.preventDefault()
  isResizing.value = true
  
  const initialWidth = sideWidth.value
  const startX = e.clientX

  function onMouseMove(moveEvent) {
    const deltaX = moveEvent.clientX - startX
    const newWidth = initialWidth + deltaX
    // Limit side width between 300px and 850px
    if (newWidth >= 300 && newWidth <= 850) {
      sideWidth.value = newWidth
      lastWidth.value = newWidth
      window.dispatchEvent(new Event('resize'))
    }
  }

  function onMouseUp() {
    isResizing.value = false
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
    window.dispatchEvent(new Event('resize'))
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}
</script>

<style scoped>
.view-layout {
  display: flex;
  height: 100%;
  max-height: 100%;
  width: 100%;
  padding: 12px;
  gap: 0;
  box-sizing: border-box;
  overflow: hidden;
  position: relative;
  background-color: #f1f5f9;
}

.side-panel {
  flex-shrink: 0;
  height: 100%;
  max-height: 100%;
  overflow: hidden;
  box-sizing: border-box;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  z-index: 5;
}

.view-layout.is-resizing .side-panel {
  transition: none; /* Disable transition during drag for smoothness */
}

.side-panel-inner {
  height: 100%;
  max-height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 8px;
  box-sizing: border-box;
}

.side-panel.is-collapsed {
  width: 0 !important;
  padding-right: 0 !important;
}

.side-panel-inner::-webkit-scrollbar {
  width: 5px;
}
.side-panel-inner::-webkit-scrollbar-track {
  background: transparent;
}
.side-panel-inner::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 3px;
}
.side-panel-inner::-webkit-scrollbar-thumb:hover {
  background-color: #94a3b8;
}

/* Resize Handle & Collapse Toggle Wrapper */
.resize-handle-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 12px;
  flex-shrink: 0;
  z-index: 10;
}

.resize-handle {
  width: 4px;
  height: 100%;
  cursor: col-resize;
  background: #cbd5e1;
  border-radius: 2px;
  transition: background 0.2s, width 0.2s;
}

.resize-handle:hover,
.view-layout.is-resizing .resize-handle {
  background: var(--primary, #0284c7);
  width: 6px;
}

.collapse-toggle-btn {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 18px;
  height: 38px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
  color: #64748b;
  transition: all 0.2s ease;
  padding: 0;
}

.collapse-toggle-btn:hover {
  background: #0284c7;
  color: #ffffff;
  border-color: #0284c7;
  width: 20px;
}

.icon-rotated {
  transform: rotate(180deg);
}

.map-area {
  flex: 1;
  min-width: 0;
  height: 100%;
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
</style>
