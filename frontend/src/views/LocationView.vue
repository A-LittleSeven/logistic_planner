<template>
  <ViewLayout>
    <template #side>
      <h2 class="lp-section-title">物流选址</h2>
      <p class="desc">
        <span class="lp-tag">加权重心法</span>
        依据各需求点的需求量(权重)计算最优选址坐标，最小化总加权运输距离。在地图上点击可添加需求点。
      </p>

      <div class="lp-card">
        <PointTable
          v-model="points"
          :columns="columns"
          :default-row="defaultRow"
          @add="addPoint"
          @remove="removePoint"
        />
      </div>

      <div class="actions">
        <button class="lp-btn" :disabled="loading || !points.length" @click="solve">
          {{ loading ? '计算中…' : '计算选址' }}
        </button>
        <button class="lp-btn lp-btn--ghost" @click="loadSample">示例数据</button>
        <ExcelImportButton @import="onImport" />
        <button class="lp-btn lp-btn--danger" @click="clearAll">清空</button>
      </div>

      <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>

      <ResultCard title="选址结果" :visible="!!result">
        <div v-if="result" class="result-grid">
          <div class="kv">
            <span class="k">最优经度</span>
            <span class="v">{{ fmt(result.optimal.lng) }}</span>
          </div>
          <div class="kv">
            <span class="k">最优纬度</span>
            <span class="v">{{ fmt(result.optimal.lat) }}</span>
          </div>
          <div class="kv full">
            <span class="k">总加权距离</span>
            <span class="v">{{ result.total_weighted_distance.toFixed(2) }} km</span>
          </div>
        </div>
      </ResultCard>
    </template>

    <template #map>
      <MapPanel ref="mapPanel" :center="mapCenter" :zoom="11" />
    </template>
  </ViewLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import ViewLayout from '../components/ViewLayout.vue'
import PointTable from '../components/PointTable.vue'
import ResultCard from '../components/ResultCard.vue'
import MapPanel from '../components/MapPanel.vue'
import ExcelImportButton from '../components/ExcelImportButton.vue'
import { locationApi } from '../api/client.js'
import { dotHtml } from '../utils/mapMarkers.js'

const mapCenter = [121.4737, 31.2304] // 上海
const columns = [
  { key: 'name', label: '名称', type: 'text', width: '78px', placeholder: 'A' },
  { key: 'lng', label: '经度', type: 'number', width: '88px', placeholder: '121.47' },
  { key: 'lat', label: '纬度', type: 'number', width: '88px', placeholder: '31.23' },
  { key: 'weight', label: '权重', type: 'number', width: '62px', placeholder: '1' },
]
const defaultRow = { name: '', lng: '', lat: '', weight: 1 }

const mapPanel = ref(null)
const amap = ref(null)
const points = ref([])
const result = ref(null)
const loading = ref(false)
const errorMsg = ref('')

const fmt = (n) => Number(n).toFixed(5)
const round = (n) => Math.round(n * 1e5) / 1e5

function addPoint() {
  points.value.push({ ...defaultRow, name: `点${points.value.length + 1}` })
  result.value = null
}
function removePoint(idx) {
  points.value.splice(idx, 1)
  result.value = null
  renderDemand()
}
function clearAll() {
  points.value = []
  result.value = null
  errorMsg.value = ''
  mapPanel.value?.clearAll()
}
function onImport({ points: imported }) {
  points.value = imported.map((p, i) => ({
    name: p.name || `点${i + 1}`,
    lng: p.lng,
    lat: p.lat,
    weight: p.weight ?? 1,
  }))
  result.value = null
  errorMsg.value = ''
  renderDemand()
  mapPanel.value?.fitView()
}
function loadSample() {
  points.value = [
    { name: '静安', lng: 121.445, lat: 31.228, weight: 12 },
    { name: '浦东', lng: 121.544, lat: 31.222, weight: 20 },
    { name: '徐汇', lng: 121.437, lat: 31.183, weight: 15 },
    { name: '杨浦', lng: 121.526, lat: 31.28, weight: 8 },
    { name: '长宁', lng: 121.424, lat: 31.222, weight: 10 },
  ]
  result.value = null
  renderDemand()
  mapPanel.value?.fitView()
}

function onMapClick(e) {
  points.value.push({
    name: `点${points.value.length + 1}`,
    lng: round(e.lnglat.getLng()),
    lat: round(e.lnglat.getLat()),
    weight: 1,
  })
  renderDemand()
}

function drawOptimal(A) {
  const { lng, lat } = result.value.optimal
  const { content, offset } = dotHtml({
    text: '选',
    color: 'linear-gradient(135deg,#f43f5e,#be185d)',
    size: 30,
  })
  mapPanel.value.addOverlay(
    new A.Marker({
      position: [lng, lat],
      content,
      offset: new A.Pixel(offset[0], offset[1]),
    })
  )
}

function renderDemand() {
  if (!amap.value) return
  const A = amap.value
  mapPanel.value.clearAll()
  points.value.forEach((p, i) => {
    if (p.lng === '' || p.lat === '') return
    const { content, offset } = dotHtml({ text: String(i + 1), color: '#3b82f6', size: 22 })
    mapPanel.value.addOverlay(
      new A.Marker({
        position: [Number(p.lng), Number(p.lat)],
        content,
        offset: new A.Pixel(offset[0], offset[1]),
      })
    )
  })
  if (result.value) drawOptimal(A)
}

async function solve() {
  errorMsg.value = ''
  if (!points.value.length) {
    errorMsg.value = '请至少添加 1 个需求点'
    return
  }
  const invalid = points.value.some(
    (p) => p.lng === '' || p.lat === '' || Number(p.weight) <= 0
  )
  if (invalid) {
    errorMsg.value = '请确保所有点已填写经纬度且权重大于 0'
    return
  }
  loading.value = true
  try {
    const payload = {
      points: points.value.map((p) => ({
        name: p.name,
        lng: Number(p.lng),
        lat: Number(p.lat),
        weight: Number(p.weight),
      })),
      algorithm: 'center_of_gravity',
    }
    result.value = await locationApi.solve(payload)
    renderDemand()
    mapPanel.value?.fitView()
  } catch (e) {
    errorMsg.value = '选址计算失败: ' + e.message
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  amap.value = await mapPanel.value.whenReady()
  mapPanel.value.setClickHandler(onMapClick)
  
  const shared = sessionStorage.getItem('shared_points')
  if (shared) {
    try {
      const parsed = JSON.parse(shared)
      if (Array.isArray(parsed) && parsed.length) {
        points.value = parsed.map(p => ({
          name: p.name || '',
          lng: p.lng,
          lat: p.lat,
          weight: p.weight || p.avg_loads || 1
        }))
        renderDemand()
        mapPanel.value?.fitView()
      }
    } catch (e) {
      console.error('Failed to load shared points', e)
    }
  }
})
</script>

<style scoped>
.desc {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.7;
}
.desc .lp-tag {
  margin-right: 6px;
}
.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.error-msg {
  color: var(--accent-rose);
  font-size: 13px;
  padding: 8px 12px;
  background: #fff1f2;
  border-radius: var(--radius-sm);
}
.result-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.kv {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 10px;
  background: #f8fafc;
  border-radius: var(--radius-sm);
}
.kv.full {
  grid-column: 1 / -1;
}
.k {
  font-size: 12px;
  color: var(--text-muted);
}
.v {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
}
</style>
