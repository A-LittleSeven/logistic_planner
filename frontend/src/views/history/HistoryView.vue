<template>
  <div class="history-page">
    <div class="page-header">
      <div>
        <h2 class="title">历史执行结果</h2>
        <p class="subtitle">追溯与对比过往执行的路线规划、店群排班与店群聚类任务，支持查看详细输入参数与输出结果。</p>
      </div>
      <div class="actions">
        <el-button :icon="Refresh" @click="fetchHistories">刷新记录</el-button>
        <el-popconfirm title="确定要清空全部历史记录吗？" @confirm="handleClearAll">
          <template #reference>
            <el-button type="danger" :icon="Delete" plain>清空历史</el-button>
          </template>
        </el-popconfirm>
      </div>
    </div>

    <!-- Filter bar -->
    <el-card shadow="never" class="filter-card">
      <div style="display: flex; gap: 20px; align-items: center; flex-wrap: wrap;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 13px; font-weight: 600; color: #475569;">记录来源:</span>
          <el-radio-group v-model="filterSaveType" @change="fetchHistories">
            <el-radio-button label="">全部记录</el-radio-button>
            <el-radio-button label="MANUAL">💾 用户手动保存</el-radio-button>
            <el-radio-button label="AUTO">⚡ 算法自动运行</el-radio-button>
          </el-radio-group>
        </div>

        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 13px; font-weight: 600; color: #475569;">业务类型:</span>
          <el-radio-group v-model="filterType" @change="fetchHistories">
            <el-radio-button label="">全部类型</el-radio-button>
            <el-radio-button label="ROUTING">路线规划</el-radio-button>
            <el-radio-button label="CLUSTER_SCHEDULE">店群排班</el-radio-button>
            <el-radio-button label="CLUSTERING">店群聚类</el-radio-button>
          </el-radio-group>
        </div>
      </div>
    </el-card>

    <!-- Table -->
    <el-card shadow="never" class="table-card">
      <el-table :data="histories" v-loading="loading" style="width: 100%" stripe border>
        <el-table-column prop="id" label="序号" width="70" align="center" />
        <el-table-column prop="task_id" label="方案名称 / 任务编号" min-width="240">
          <template #default="{ row }">
            <div style="font-weight: 600; color: #0f172a; margin-bottom: 2px;">
              {{ getPlanTitle(row) }}
            </div>
            <div class="mono" style="font-size: 11px; color: #94a3b8;">{{ row.task_id }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="save_type" label="记录来源" width="130" align="center">
          <template #default="{ row }">
            <el-tag :type="row.save_type === 'MANUAL' ? 'success' : 'info'" effect="light" style="font-weight: 600;">
              {{ row.save_type === 'MANUAL' ? '💾 手动保存' : '⚡ 自动运行' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="task_type" label="任务类型" width="140">
          <template #default="{ row }">
            <el-tag :type="getTypeTag(row.task_type)">{{ formatTaskType(row.task_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="执行状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="记录时间" width="170">
          <template #default="{ row }">
            {{ row.created_at ? new Date(row.created_at).toLocaleString() : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="viewDetails(row)">查看结果</el-button>
            <el-button type="success" link size="small" :icon="Download" @click="handleExport(row)">下载数据</el-button>
            <el-popconfirm title="确定要删除此条记录？" @confirm="handleDelete(row.task_id)">
              <template #reference>
                <el-button type="danger" link size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="histories.length === 0 && !loading" class="empty-tip">
        暂无符合条件的历史记录，去发起一次规划或保存方案吧！
      </div>
    </el-card>

    <!-- Details Dialog -->
    <el-dialog v-model="dialogVisible" title="算法任务详情" width="780px" destroy-on-close>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%; padding-right: 20px;">
          <span style="font-weight: 700; font-size: 16px; color: #0f172a;">算法任务与规划方案详情</span>
          <el-button v-if="currentTask && currentTask.status === 'SUCCESS'" type="success" size="small" :icon="Download" @click="handleExport(currentTask)">
            导出 Excel 表格
          </el-button>
        </div>
      </template>
      <div v-if="currentTask" class="dialog-body">
        <el-descriptions :column="2" border style="margin-bottom: 16px;">
          <el-descriptions-item label="方案名称">{{ getPlanTitle(currentTask) }}</el-descriptions-item>
          <el-descriptions-item label="记录来源">
            <el-tag :type="currentTask.save_type === 'MANUAL' ? 'success' : 'info'">
              {{ currentTask.save_type === 'MANUAL' ? '💾 用户手动保存' : '⚡ 算法自动运行' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="任务 ID">{{ currentTask.task_id }}</el-descriptions-item>
          <el-descriptions-item label="业务类型">{{ formatTaskType(currentTask.task_type) }}</el-descriptions-item>
          <el-descriptions-item label="执行状态">
            <el-tag :type="getStatusType(currentTask.status)">{{ currentTask.status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="记录时间">
            {{ currentTask.created_at ? new Date(currentTask.created_at).toLocaleString() : '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="currentTask.error_message" class="error-box">
          <strong>错误信息:</strong>
          <pre>{{ currentTask.error_message }}</pre>
        </div>

        <el-tabs v-model="activeTab">
          <el-tab-pane label="计算结果 (Result)" name="result">
            <pre class="json-code">{{ formatJson(currentTask.result) }}</pre>
          </el-tab-pane>
          <el-tab-pane label="输入参数 (Parameters)" name="params">
            <pre class="json-code">{{ formatJson(currentTask.parameters) }}</pre>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Refresh, Delete, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { exportHistoryTaskToExcel } from '../../utils/historyExport.js'

const API_BASE = '/api/history'

const histories = ref([])
const loading = ref(false)
const filterType = ref('')
const filterSaveType = ref('')

const dialogVisible = ref(false)
const currentTask = ref(null)
const activeTab = ref('result')

const fetchHistories = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (filterType.value) params.append('task_type', filterType.value)
    if (filterSaveType.value) params.append('save_type', filterSaveType.value)
    
    const queryString = params.toString()
    const url = queryString ? `${API_BASE}/?${queryString}` : `${API_BASE}/`
    const res = await fetch(url)
    if (!res.ok) throw new Error('获取历史数据失败')
    const data = await res.json()
    histories.value = data
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    loading.value = false
  }
}

const getPlanTitle = (row) => {
  if (!row) return '-'
  try {
    if (row.parameters) {
      const p = typeof row.parameters === 'string' ? JSON.parse(row.parameters) : row.parameters
      if (p.title) return p.title
      if (p.algorithm) {
        const count = p.points_count || (Array.isArray(p.points) ? p.points.length : '')
        return `店群分组方案 (${p.algorithm}${count ? `, ${count}家门店` : ''})`
      }
    }
  } catch (e) {}
  return `${formatTaskType(row.task_type)}记录`
}

const viewDetails = (task) => {
  currentTask.value = task
  activeTab.value = 'result'
  dialogVisible.value = true
}

const handleExport = (task) => {
  if (!task) return
  if (task.status !== 'SUCCESS') {
    ElMessage.warning('该任务未成功执行，暂无有效结果可供下载')
    return
  }
  try {
    const filename = exportHistoryTaskToExcel(task)
    ElMessage.success(`方案数据已成功导出为【${filename}】！`)
  } catch (err) {
    console.error('Export error:', err)
    ElMessage.error(`数据导出失败: ${err.message || err}`)
  }
}

const handleDelete = async (taskId) => {
  try {
    const res = await fetch(`${API_BASE}/${taskId}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('删除失败')
    ElMessage.success('记录已删除')
    fetchHistories()
  } catch (err) {
    ElMessage.error(err.message)
  }
}

const handleClearAll = async () => {
  try {
    const res = await fetch(`${API_BASE}/clear/all`, { method: 'DELETE' })
    if (!res.ok) throw new Error('清空失败')
    ElMessage.success('所有记录已清空')
    fetchHistories()
  } catch (err) {
    ElMessage.error(err.message)
  }
}

const formatTaskType = (type) => {
  const map = {
    'ROUTING': '路线规划',
    'GLOBAL_ROUTING': '全局排班规划',
    'CLUSTERING': '店群聚类',
    'CLUSTER_SCHEDULE': '店群排班'
  }
  return map[type] || type
}

const getTypeTag = (type) => {
  if (type === 'ROUTING' || type === 'GLOBAL_ROUTING') return 'primary'
  if (type === 'CLUSTERING' || type === 'CLUSTER_SCHEDULE') return 'success'
  return 'info'
}

const getStatusType = (status) => {
  switch (status) {
    case 'SUCCESS': return 'success'
    case 'RUNNING': return 'warning'
    case 'FAILED': return 'danger'
    default: return 'info'
  }
}

const formatJson = (str) => {
  if (!str) return '暂无数据'
  try {
    const obj = typeof str === 'string' ? JSON.parse(str) : str
    return JSON.stringify(obj, null, 2)
  } catch (e) {
    return str
  }
}

onMounted(() => {
  fetchHistories()
})
</script>

<style scoped>
.history-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 4px 0;
}

.subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

.filter-card {
  border-radius: 8px;
}

.table-card {
  border-radius: 8px;
}

.mono {
  font-family: monospace;
  font-size: 12px;
  color: #475569;
}

.empty-tip {
  text-align: center;
  padding: 30px 0;
  color: #94a3b8;
  font-size: 14px;
}

.json-code {
  background-color: #0f172a;
  color: #38bdf8;
  padding: 12px 16px;
  border-radius: 6px;
  font-family: Monaco, Menlo, Consolas, monospace;
  font-size: 12px;
  line-height: 1.5;
  max-height: 420px;
  overflow-y: auto;
}

.error-box {
  background-color: #fef2f2;
  color: #b91c1c;
  padding: 10px 14px;
  border-radius: 6px;
  margin-bottom: 14px;
  font-size: 13px;
}
</style>
