<template>
  <div class="map-panel">
    <div ref="container" class="map-container"></div>
    <div v-if="error" class="map-error">
      <div style="text-align: center;">
        <strong style="display: block; font-size: 16px; margin-bottom: 6px;">地图加载失败</strong>
        <p style="color: #ef4444; margin-bottom: 8px;">{{ error }}</p>
        <p class="hint">请检查高德 Key 配置或网络环境</p>
        <el-button type="primary" size="small" style="margin-top: 12px;" @click="initMap">
          重试加载地图
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { loadAMap, aMapKeyVersion } from '../composables/useAMap.js'

const props = defineProps({
  center: { type: Array, default: () => [116.397428, 39.90923] }, // 北京
  zoom: { type: Number, default: 11 },
})

const container = ref(null)
const error = ref('')

let map = null
let AMap = null
const overlays = []
const readyResolvers = []

const emit = defineEmits(['map-ready', 'map-error'])

const initMap = async () => {
  if (map) {
    try {
      map.destroy()
    } catch (e) {}
    map = null
  }
  error.value = ''

  try {
    AMap = await loadAMap()
    if (!container.value) return
    map = new AMap.Map(container.value, {
      center: props.center,
      zoom: props.zoom,
      viewMode: '2D',
    })
    map.addControl(new AMap.Scale())
    map.addControl(new AMap.ToolBar({ position: 'RB' }))
    readyResolvers.forEach(({ resolve }) => resolve && resolve(AMap))
    readyResolvers.length = 0
    emit('map-ready', { map, AMap })
  } catch (e) {
    const err = e instanceof Error ? e : new Error(String(e))
    error.value = err.message || String(err)
    readyResolvers.forEach(({ reject }) => reject && reject(err))
    readyResolvers.length = 0
    emit('map-error', err)
    ElMessage.error(`高德地图加载失败: ${error.value}`)
  }
}

onMounted(() => {
  initMap()
})

// 监听高德 Key 版本变化，当密钥更新后自动刷新地图实例
watch(aMapKeyVersion, (newVer, oldVer) => {
  if (oldVer !== undefined && oldVer !== 0) {
    initMap()
  }
})

onBeforeUnmount(() => {
  if (map) {
    map.destroy()
    map = null
  }
})

/** 父组件调用, 返回 AMap 命名空间 (用于构造 Marker / Polyline 等)。 */
function whenReady() {
  return new Promise((resolve, reject) => {
    if (AMap && map) resolve(AMap)
    else if (error.value) reject(new Error(error.value))
    else readyResolvers.push({ resolve, reject })
  })
}

function addOverlay(o) {
  if (map) {
    map.add(o)
    overlays.push(o)
  }
  return o
}

function clearAll() {
  if (map) {
    try {
      if (typeof map.clearInfoWindow === 'function') map.clearInfoWindow()
    } catch (e) {}
    if (overlays.length) {
      overlays.forEach((o) => {
        try {
          if (o.clear) o.clear()
          map.remove(o)
        } catch (e) {}
      })
    }
  }
  overlays.length = 0
}

function fitView(padding = [60, 60, 60, 60]) {
  if (map && overlays.length) map.setFitView(overlays, false, padding)
}

const getMap = () => map
const getAmap = () => whenReady()

defineExpose({ whenReady, getAmap, addOverlay, clearAll, fitView, getMap, reload: initMap })
</script>

<style scoped>
.map-panel {
  position: relative;
  height: 100%;
  width: 100%;
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}
.map-container {
  height: 100%;
  width: 100%;
}
.map-error {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: #fff5f5;
}
.map-error strong {
  color: var(--accent-rose);
  font-size: 16px;
}
.map-error p {
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 13px;
}
.map-error .hint {
  color: var(--text-light);
}
</style>
