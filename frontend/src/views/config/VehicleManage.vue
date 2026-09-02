<template>
  <div class="vehicle-manage-page">
    <div class="page-header">
      <div>
        <h2 class="title">车型维护</h2>
        <p class="subtitle">管理物流车队运力参数，包括载重上限、体积、每公里行驶成本以及最大续航里程。</p>
      </div>
      <div class="actions">
        <el-button type="primary" :icon="Plus" @click="openAddDialog">新增车型</el-button>
        <el-button :icon="Refresh" @click="fetchVehicles">刷新</el-button>
      </div>
    </div>

    <!-- Table -->
    <el-card shadow="never" class="table-card">
      <el-table :data="vehicles" v-loading="loading" style="width: 100%" stripe border>
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="vehicle_code" label="车型代码" width="120" />
        <el-table-column prop="name" label="车型名称" min-width="180" />
        <el-table-column prop="capacity_weight" label="最大载重 (箱/t)" width="140" align="right">
          <template #default="{ row }">
            <strong>{{ row.capacity_weight }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="capacity_volume" label="最大容积 (m³)" width="130" align="right">
          <template #default="{ row }">
            {{ row.capacity_volume }} m³
          </template>
        </el-table-column>
        <el-table-column prop="cost_per_km" label="每公里成本 (元)" width="140" align="right">
          <template #default="{ row }">
            <el-tag type="warning" size="small">¥ {{ row.cost_per_km }}/km</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="max_distance" label="最大续航里程" width="130" align="right">
          <template #default="{ row }">
            {{ row.max_distance }} km
          </template>
        </el-table-column>
        <el-table-column prop="available_count" label="可用车数" width="100" align="center">
          <template #default="{ row }">
            <el-tag type="success" size="small">{{ row.available_count }} 辆</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-popconfirm title="确定要删除该车型吗？" @confirm="handleDelete(row.id)">
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
      :title="isEdit ? '编辑车型' : '新增车型'"
      width="550px"
      destroy-on-close
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="110px">
        <el-form-item label="车型代码" prop="vehicle_code">
          <el-input v-model="form.vehicle_code" :disabled="isEdit" placeholder="例如: V420" />
        </el-form-item>
        <el-form-item label="车型名称" prop="name">
          <el-input v-model="form.name" placeholder="例如: 新能源4.2米箱式货车" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="最大载重" prop="capacity_weight">
              <el-input-number v-model="form.capacity_weight" :min="1" :step="10" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最大容积" prop="capacity_volume">
              <el-input-number v-model="form.capacity_volume" :min="1" :step="5" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="公里成本(元)" prop="cost_per_km">
              <el-input-number v-model="form.cost_per_km" :precision="2" :step="0.5" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="续航里程(km)" prop="max_distance">
              <el-input-number v-model="form.max_distance" :min="50" :step="50" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="可用数量" prop="available_count">
          <el-input-number v-model="form.available_count" :min="1" :max="100" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const API_BASE = '/api/vehicle'

const vehicles = ref([])
const loading = ref(false)

const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)

const form = ref({
  id: null,
  vehicle_code: '',
  name: '',
  capacity_weight: 200,
  capacity_volume: 18,
  cost_per_km: 3.5,
  max_distance: 400,
  available_count: 5,
  is_active: true
})

const rules = {
  vehicle_code: [{ required: true, message: '请输入车型代码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入车型名称', trigger: 'blur' }],
  capacity_weight: [{ required: true, message: '请输入最大载重', trigger: 'blur' }],
}

const fetchVehicles = async () => {
  loading.value = true
  try {
    const res = await fetch(`${API_BASE}/`)
    if (!res.ok) throw new Error('获取车型数据失败')
    const data = await res.json()
    vehicles.value = data
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    loading.value = false
  }
}

const openAddDialog = () => {
  isEdit.value = false
  form.value = {
    id: null,
    vehicle_code: 'TRUCK_' + Math.floor(100 + Math.random() * 900),
    name: '',
    capacity_weight: 200,
    capacity_volume: 18,
    cost_per_km: 3.5,
    max_distance: 400,
    available_count: 5,
    is_active: true
  }
  dialogVisible.value = true
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
          const errorData = await res.json()
          throw new Error(errorData.detail || '更新失败')
        }
        ElMessage.success('车型更新成功')
      } else {
        const res = await fetch(`${API_BASE}/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(form.value)
        })
        if (!res.ok) {
          const errorData = await res.json()
          throw new Error(errorData.detail || '新增失败')
        }
        ElMessage.success('车型添加成功')
      }
      dialogVisible.value = false
      fetchVehicles()
    } catch (err) {
      ElMessage.error(err.message)
    } finally {
      submitting.value = false
    }
  })
}

const handleDelete = async (id) => {
  try {
    const res = await fetch(`${API_BASE}/${id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('删除失败')
    ElMessage.success('车型删除成功')
    fetchVehicles()
  } catch (err) {
    ElMessage.error(err.message)
  }
}

onMounted(() => {
  fetchVehicles()
})
</script>

<style scoped>
.vehicle-manage-page {
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
</style>
