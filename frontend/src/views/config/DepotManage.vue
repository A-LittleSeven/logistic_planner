<template>
  <div class="depot-manage-page">
    <div class="page-header">
      <div>
        <h2 class="title">起点管理 (DC中心仓维护)</h2>
        <p class="subtitle">维护物流配送网络中的发货起点、配送中心 (DC) 与仓库经纬度信息，支持设为默认规划起点。</p>
      </div>
      <div class="actions">
        <el-button type="primary" :icon="Plus" @click="openAddDialog">新增起点 / DC</el-button>
        <el-button :icon="Refresh" @click="fetchDepots">刷新</el-button>
      </div>
    </div>

    <!-- Table -->
    <el-card shadow="never" class="table-card">
      <el-table :data="depots" v-loading="loading" style="width: 100%" stripe border>
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="dc_code" label="DC 编码" width="130">
          <template #default="{ row }">
            <span class="font-mono">{{ row.dc_code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="起点 / 中心仓名称" min-width="160">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 6px;">
              <span style="font-weight: 600;">{{ row.name }}</span>
              <el-tag v-if="row.is_default" type="danger" effect="dark" size="small">默认起点</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="longitude" label="经度" width="120" align="right">
          <template #default="{ row }">{{ Number(row.longitude).toFixed(6) }}</template>
        </el-table-column>
        <el-table-column prop="latitude" label="纬度" width="120" align="right">
          <template #default="{ row }">{{ Number(row.latitude).toFixed(6) }}</template>
        </el-table-column>
        <el-table-column prop="capacity" label="吞吐仓容 (吨/箱)" width="140" align="right">
          <template #default="{ row }">
            {{ row.capacity ? row.capacity.toLocaleString() : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="address" label="物理地址" min-width="200" show-overflow-tooltip />
        <el-table-column prop="contact_person" label="联系人" width="110" />
        <el-table-column prop="contact_phone" label="联系电话" width="130" />
        <el-table-column label="操作" width="200" fixed="right" align="center">
          <template #default="{ row }">
            <el-button v-if="!row.is_default" type="warning" link size="small" @click="handleSetDefault(row.id)">设为默认</el-button>
            <el-button type="primary" link size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-popconfirm title="确定要删除该起点吗？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button type="danger" link size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Dialog for Add / Edit -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑起点 / DC信息' : '新增起点 / DC'"
      width="640px"
      destroy-on-close
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="仓库编码" prop="dc_code">
              <el-input v-model="form.dc_code" placeholder="例如: DC_NN_01 / WH_001" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="中心仓名称" prop="name">
              <el-input v-model="form.name" placeholder="例如: 南宁中心仓" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="经度 (Lng)" prop="longitude">
              <el-input-number v-model="form.longitude" :precision="6" :step="0.001" style="width: 100%" @change="onCoordsChange" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="纬度 (Lat)" prop="latitude">
              <el-input-number v-model="form.latitude" :precision="6" :step="0.001" style="width: 100%" @change="onCoordsChange" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="物理地址" prop="address">
          <el-input v-model="form.address" placeholder="输入经纬度可自动反查识别，亦可手动输入">
            <template #append>
              <el-button :icon="Location" :loading="resolvingAddress" @click="handleAutoResolveAddress(false)">
                智能识别
              </el-button>
            </template>
          </el-input>
          <div style="font-size: 12px; color: #64748b; margin-top: 4px; display: flex; align-items: center; gap: 4px;">
            <span>📍 输入或调整经纬度后系统会自动通过高德地图逆地理编码识别物理地址。</span>
          </div>
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="吞吐仓容">
              <el-input-number v-model="form.capacity" :min="0" :step="1000" style="width: 100%" placeholder="吨/箱" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设为默认">
              <el-switch v-model="form.is_default" active-text="默认起点" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="联系人">
              <el-input v-model="form.contact_person" placeholder="仓库负责人" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="联系电话">
              <el-input v-model="form.contact_phone" placeholder="联系电话" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Plus, Refresh, Location } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getAddressByCoords } from '../../composables/useAMap.js'

const API_BASE = '/api/depot'

const depots = ref([])
const loading = ref(false)
const resolvingAddress = ref(false)

const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)

const form = ref({
  id: null,
  dc_code: '',
  name: '',
  longitude: 108.318344,
  latitude: 22.846367,
  address: '',
  capacity: 50000,
  contact_person: '',
  contact_phone: '',
  is_default: false,
  is_active: true
})

const rules = {
  dc_code: [{ required: true, message: '请输入DC编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入中心仓名称', trigger: 'blur' }],
  longitude: [{ required: true, message: '请输入经度', trigger: 'blur' }],
  latitude: [{ required: true, message: '请输入纬度', trigger: 'blur' }],
}

const fetchDepots = async () => {
  loading.value = true
  try {
    const res = await fetch(`${API_BASE}/`)
    if (!res.ok) throw new Error('获取起点数据失败')
    const data = await res.json()
    depots.value = data
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    loading.value = false
  }
}

let resolveTimer = null
const onCoordsChange = () => {
  if (resolveTimer) clearTimeout(resolveTimer)
  resolveTimer = setTimeout(() => {
    handleAutoResolveAddress(true)
  }, 600)
}

const handleAutoResolveAddress = async (silent = false) => {
  if (!form.value.longitude || !form.value.latitude) {
    if (!silent) ElMessage.warning('请先输入有效的经纬度数值')
    return
  }
  resolvingAddress.value = true
  try {
    const address = await getAddressByCoords(form.value.longitude, form.value.latitude)
    if (address) {
      form.value.address = address
      if (!silent) {
        ElMessage.success(`地址已识别: ${address}`)
      }
    } else if (!silent) {
      ElMessage.info('未匹配到精确地址，请手动输入')
    }
  } catch (err) {
    if (!silent) {
      ElMessage.warning('高德地图地址解析未成功，可手动输入物理地址')
    }
  } finally {
    resolvingAddress.value = false
  }
}

const openAddDialog = () => {
  isEdit.value = false
  form.value = {
    id: null,
    dc_code: 'DC_' + Math.floor(100 + Math.random() * 900),
    name: '',
    longitude: 108.318344,
    latitude: 22.846367,
    address: '',
    capacity: 30000,
    contact_person: '',
    contact_phone: '',
    is_default: false,
    is_active: true
  }
  dialogVisible.value = true
  // 自动根据默认经纬度填补地址
  setTimeout(() => {
    if (!form.value.address) {
      handleAutoResolveAddress(true)
    }
  }, 300)
}

const openEditDialog = (row) => {
  isEdit.value = true
  form.value = { ...row }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      if (isEdit.value) {
        const res = await fetch(`${API_BASE}/${form.value.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(form.value)
        })
        if (!res.ok) {
          const err = await res.json()
          throw new Error(err.detail || '更新失败')
        }
        ElMessage.success('起点/DC更新成功')
      } else {
        const res = await fetch(`${API_BASE}/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(form.value)
        })
        if (!res.ok) {
          const err = await res.json()
          throw new Error(err.detail || '新增失败')
        }
        ElMessage.success('起点/DC创建成功')
      }
      dialogVisible.value = false
      fetchDepots()
    } catch (err) {
      ElMessage.error(err.message)
    } finally {
      submitting.value = false
    }
  })
}

const handleSetDefault = async (id) => {
  try {
    const res = await fetch(`${API_BASE}/${id}/set_default`, { method: 'POST' })
    if (!res.ok) throw new Error('设置默认起点失败')
    ElMessage.success('已设为默认起点')
    fetchDepots()
  } catch (err) {
    ElMessage.error(err.message)
  }
}

const handleDelete = async (id) => {
  try {
    const res = await fetch(`${API_BASE}/${id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('删除失败')
    ElMessage.success('起点已删除')
    fetchDepots()
  } catch (err) {
    ElMessage.error(err.message)
  }
}

onMounted(() => {
  fetchDepots()
})
</script>

<style scoped>
.depot-manage-page {
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

.table-card {
  border-radius: 8px;
}

.font-mono {
  font-family: Monaco, Menlo, Consolas, monospace;
  font-size: 13px;
  color: #334155;
}
</style>
