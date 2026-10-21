<template>
  <el-dialog
    :model-value="visible"
    :title="dialogTitle"
    width="860px"
    destroy-on-close
    :append-to-body="true"
    @update:model-value="$emit('update:visible', $event)"
  >
    <!-- Day Context Notice -->
    <div
      v-if="currentDay !== '全部'"
      style="margin-bottom: 12px; padding: 8px 12px; background: #faf5ff; border: 1px solid #d8b4fe; border-radius: 6px; font-size: 12px; color: #6b21a8; display: flex; align-items: center; justify-content: space-between;"
    >
      <div style="display: flex; align-items: center; gap: 6px;">
        <span style="font-size: 16px;">💡</span>
        <span>当前生效作业日: <strong style="color: #7c3aed; font-size: 13px;">【{{ currentDay }}】</strong>。此处的快递切换<strong>仅对 {{ currentDay }} 生效</strong>，门店在其他作业日依然正常走货车！</span>
      </div>
      <el-tag size="small" type="purple" effect="dark" style="background: #7c3aed; border-color: #6d28d9;">
        单日精细化调度模式
      </el-tag>
    </div>

    <!-- Filter & Search Toolbar -->
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; gap: 8px; flex-wrap: wrap;">
      <el-input
        v-model="searchText"
        placeholder="搜索门店名称、编号或行政区划..."
        style="width: 260px;"
        clearable
        size="small"
      />

      <div style="display: flex; gap: 6px; align-items: center;">
        <el-radio-group v-model="filterStatus" size="small">
          <el-radio-button label="ALL">全部 ({{ stores.length }})</el-radio-button>
          <el-radio-button label="TRUCK">🚛 常规货车 ({{ truckStoresCount }})</el-radio-button>
          <el-radio-button label="EXPRESS">📦 快递直发 ({{ expressStoresCount }})</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- Batch Action Summary Banner -->
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; background: #f8fafc; padding: 6px 10px; border-radius: 4px; font-size: 11px; color: #64748b;">
      <span>匹配到 <strong>{{ filteredStores.length }}</strong> 家门店</span>
      <div style="display: flex; gap: 6px;">
        <el-button size="small" type="primary" plain @click="handleBatchSet(1)">
          📦 将筛选结果在{{ currentDay === '全部' ? '全部作业日' : currentDay }}设为快递
        </el-button>
        <el-button size="small" type="success" plain @click="handleBatchSet(0)">
          🚛 将筛选结果在{{ currentDay === '全部' ? '全部作业日' : currentDay }}设为货车
        </el-button>
      </div>
    </div>

    <!-- Store Table -->
    <el-table :data="filteredStores" border stripe max-height="400px" size="small">
      <el-table-column type="index" label="序号" width="50" align="center" />
      <el-table-column prop="name" label="门店名称" min-width="150">
        <template #default="{ row }">
          <div style="font-weight: 600; color: #1e293b;">{{ row.name }}</div>
          <div style="font-size: 10px; color: #94a3b8;">{{ row.shop_code || '-' }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="district" label="行政区划" width="90" />
      <el-table-column label="周作业日配送安排" min-width="210">
        <template #default="{ row }">
          <div v-if="getStoreDays(row).length" style="display: flex; flex-wrap: wrap; gap: 4px;">
            <el-tag
              v-for="d in getStoreDays(row)"
              :key="d"
              size="small"
              :type="isDayExpress(row, d) ? 'purple' : 'info'"
              :effect="isDayExpress(row, d) ? 'dark' : 'plain'"
              style="cursor: pointer; font-size: 11px;"
              :style="isDayExpress(row, d) ? 'background: #7c3aed; border-color: #6d28d9;' : ''"
              title="点击切换该日期的配送方式"
              @click="toggleSingleDayExpress(row, d)"
            >
              {{ d }}: {{ isDayExpress(row, d) ? '📦 快递' : '🚛 货车' }}
            </el-tag>
          </div>
          <span v-else style="color: #94a3b8; font-size: 11px;">未排班</span>
        </template>
      </el-table-column>
      <el-table-column label="日均箱数" width="80" align="center">
        <template #default="{ row }">
          <strong>{{ row.avg_loads || row.weight || row.demand || 10 }}</strong> 箱
        </template>
      </el-table-column>
      <el-table-column :label="currentDay === '全部' ? '全周配送方式' : `${currentDay}配送方式`" width="160" align="center">
        <template #default="{ row }">
          <el-switch
            :model-value="isDayExpress(row, currentDay) ? 1 : 0"
            :active-value="1"
            :inactive-value="0"
            active-text="📦 快递"
            inactive-text="🚛 货车"
            inline-prompt
            style="--el-switch-on-color: #8b5cf6; --el-switch-off-color: #0284c7;"
            @change="handleToggle(row, $event)"
          />
        </template>
      </el-table-column>
    </el-table>

    <template #footer>
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 11px; color: #94a3b8;">
          💡 可直接点击表格中具体作业日标签（如 [周二: 📦快递]）进行精细单日切换
        </span>
        <el-button type="primary" @click="$emit('update:visible', false)">完成</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouteOptimizer } from '../../composables/useRouteOptimizer.js'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  stores: {
    type: Array,
    default: () => [],
  },
  currentDay: {
    type: String,
    default: '全部',
  },
})

const emit = defineEmits(['update:visible', 'toggle-express', 'batch-set-express'])

const { getStoreScheduleDays, isStoreExpressOnDay } = useRouteOptimizer()

const searchText = ref('')
const filterStatus = ref('ALL')

const dialogTitle = computed(() => {
  if (props.currentDay !== '全部') {
    return `📦 门店配送方式管理 (当前作业日: ${props.currentDay})`
  }
  return '📦 门店配送方式管理 (全周作业日 / 常规货车 / 快递直发)'
})

const getStoreDays = (store) => {
  return getStoreScheduleDays(store)
}

const isDayExpress = (store, day) => {
  return isStoreExpressOnDay(store, day)
}

const truckStoresCount = computed(() => {
  return props.stores.filter((s) => !isStoreExpressOnDay(s, props.currentDay)).length
})

const expressStoresCount = computed(() => {
  return props.stores.filter((s) => isStoreExpressOnDay(s, props.currentDay)).length
})

const filteredStores = computed(() => {
  let list = props.stores
  if (filterStatus.value === 'TRUCK') {
    list = list.filter((p) => !isStoreExpressOnDay(p, props.currentDay))
  } else if (filterStatus.value === 'EXPRESS') {
    list = list.filter((p) => isStoreExpressOnDay(p, props.currentDay))
  }
  if (searchText.value.trim()) {
    const q = searchText.value.trim().toLowerCase()
    list = list.filter((p) => {
      const name = (p.name || '').toLowerCase()
      const code = (p.shop_code || '').toLowerCase()
      const dist = (p.district || '').toLowerCase()
      return name.includes(q) || code.includes(q) || dist.includes(q)
    })
  }
  return list
})

const handleToggle = (store, val) => {
  emit('toggle-express', { store, day: props.currentDay, isExpress: Number(val) })
}

const toggleSingleDayExpress = (store, day) => {
  const currentExp = isStoreExpressOnDay(store, day)
  emit('toggle-express', { store, day, isExpress: currentExp ? 0 : 1 })
}

const handleBatchSet = (val) => {
  emit('batch-set-express', { targets: filteredStores.value, day: props.currentDay, isExpress: Number(val) })
}
</script>
