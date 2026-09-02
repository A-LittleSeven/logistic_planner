<template>
  <div class="import-wrap">
    <button class="lp-btn lp-btn--ghost" :disabled="disabled" @click="trigger">
      导入数据 (Excel/CSV)
    </button>
    <input
      ref="input"
      type="file"
      accept=".xlsx,.xls,.csv"
      hidden
      @change="onChange"
    />
    <div v-if="status" class="import-status" :class="statusType">{{ status }}</div>
  </div>
</template>

<script setup>
import { ref, onBeforeUnmount } from 'vue'
import { parseExcelFile, parseCSVFile } from '../utils/excelImport.js'

defineProps({ disabled: Boolean })
const emit = defineEmits(['import'])

const input = ref(null)
const status = ref('')
const statusType = ref('success')
let timer = null

function setStatus(text, type) {
  status.value = text
  statusType.value = type
  clearTimeout(timer)
  timer = setTimeout(() => {
    status.value = ''
  }, 5000)
}

function trigger() {
  input.value?.click()
}

async function onChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  try {
    let result;
    if (file.name.endsWith('.csv')) {
      result = await parseCSVFile(file)
    } else {
      result = await parseExcelFile(file)
    }
    const { points, warnings } = result
    if (!points.length) {
      setStatus(warnings[0] || '未导入任何点', 'error')
      return
    }
    emit('import', { points, warnings })
    const warn = warnings.length ? `（${warnings.join('；')}）` : ''
    setStatus(`已导入 ${points.length} 条${warn}`, warnings.length ? 'warn' : 'success')
  } catch (err) {
    setStatus('导入失败: ' + (err.message || err), 'error')
  } finally {
    e.target.value = '' // 允许重复选择同一文件
  }
}

onBeforeUnmount(() => clearTimeout(timer))
</script>

<style scoped>
.import-wrap {
  display: inline-flex;
  flex-direction: column;
  gap: 4px;
}
.import-status {
  font-size: 12px;
  line-height: 1.4;
  max-width: 260px;
}
.import-status.success {
  color: var(--accent-teal);
}
.import-status.warn {
  color: var(--accent-amber);
}
.import-status.error {
  color: var(--accent-rose);
}
</style>
