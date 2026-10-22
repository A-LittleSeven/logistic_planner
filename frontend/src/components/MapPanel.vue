<template>
  <div class="map-panel">
    <div ref="container" class="map-container"></div>
    <div v-if="error" class="map-error">
      <div>
        <strong>地图加载失败</strong>
        <p>{{ error }}</p>
        <p class="hint">请在 frontend/.env 配置 VITE_AMAP_KEY 与 VITE_AMAP_SECURITY 后重启 dev。</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { loadAMap } from '../composables/useAMap.js'

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

const emit = defineEmits(['map-ready'])

onMounted(async () => {
  try {
    AMap = await loadAMap()
    map = new AMap.Map(container.value, {
      center: props.center,
      zoom: props.zoom,
      viewMode: '2D',
    })
    map.addControl(new AMap.Scale())
    map.addControl(new AMap.ToolBar({ position: 'RB' }))
    readyResolvers.forEach((r) => r(AMap))
    readyResolvers.length = 0
    emit('map-ready', { map, AMap })
  } catch (e) {
    error.value = e?.message || String(e)
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
  return new Promise((resolve) => {
    if (AMap) resolve(AMap)
    else readyResolvers.push(resolve)
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

defineExpose({ whenReady, getAmap, addOverlay, clearAll, fitView, getMap })
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
