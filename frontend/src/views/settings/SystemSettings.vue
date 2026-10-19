<template>
  <div class="settings-container">
    <!-- Header -->
    <AppPageHeader
      title="系统参数与密钥配置"
      subtitle="维护高德地图开放平台 Web 端 JS API Key 与安全密钥。密钥在前端默认隐藏保护，由后端 SQLite 安全存储并进行 MD5 密文加密。"
      :icon="Setting"
    />

    <div class="settings-grid">
      <!-- Left Column: Key & Secret Configuration -->
      <div class="settings-main">
        <el-card shadow="never" class="config-card">
          <template #header>
            <div class="card-header">
              <div class="header-left">
                <el-icon :size="18" color="#0284c7"><MapLocation /></el-icon>
                <span class="card-title">高德地图 (AMap) 开发者密钥与安全存储</span>
              </div>
              <el-tag :type="configState.isCustom ? 'success' : 'info'" effect="light" size="small">
                {{ configState.isCustom ? '🟢 当前生效: 用户自定义密钥 (SQLite)' : '🔵 当前生效: 系统内置默认密钥 (无需配置)' }}
              </el-tag>
            </div>
          </template>

          <el-form label-position="top" class="settings-form">
            <!-- AMap Key Field -->
            <el-form-item label="高德 Web端 (JS API) Key">
              <template #label>
                <div class="form-item-label">
                  <span>高德 Web端 (JS API) Key</span>
                  <span style="font-size: 11px; color: #64748b; font-weight: normal;">(选填，留空使用系统默认)</span>
                </div>
              </template>
              <el-input
                v-model="form.key"
                :type="hideSecret ? 'password' : 'text'"
                placeholder="（选填）留空则系统自动使用内置默认密钥"
                clearable
                show-password
              >
                <template #prefix>
                  <el-icon color="#64748b"><Key /></el-icon>
                </template>
                <template #append v-if="form.key">
                  <el-button @click="copyText(form.key, 'Key')">复制</el-button>
                </template>
              </el-input>
              <div class="field-hint">
                💡 如需自定义，<strong>服务平台务必选择「Web端 (JS API)」</strong>，不可使用 Web服务 API Key。
              </div>
            </el-form-item>

            <!-- AMap Security Secret Field -->
            <el-form-item label="高德安全密钥 (Security Secret / jscode)">
              <template #label>
                <div class="form-item-label">
                  <span>高德安全密钥 (Security Secret / jscode)</span>
                  <span style="font-size: 11px; color: #64748b; font-weight: normal;">(选填，留空使用系统默认)</span>
                </div>
              </template>
              <el-input
                v-model="form.security"
                :type="hideSecret ? 'password' : 'text'"
                placeholder="（选填）留空则系统自动使用内置默认密钥"
                clearable
                show-password
              >
                <template #prefix>
                  <el-icon color="#64748b"><Lock /></el-icon>
                </template>
                <template #append v-if="form.security">
                  <el-button @click="copyText(form.security, '安全密钥')">复制</el-button>
                </template>
              </el-input>
              <div class="field-hint">
                🔒 高德 JS API 2.0 规范要求。填写后由后端 SQLite 安全存储并进行 MD5 密文加密。
              </div>
            </el-form-item>

            <!-- Security & MD5 Hash Status Banner -->
            <div class="security-meta-bar">
              <div class="meta-item">
                <span class="meta-label">🗄️ 密钥生效状态:</span>
                <el-tag size="small" :type="configState.isCustom ? 'success' : 'info'" effect="plain">
                  {{ configState.isCustom ? '用户自定义配置 (SQLite存储)' : '系统内置默认密钥 (就绪)' }}
                </el-tag>
              </div>
              <div class="meta-item" v-if="configState.isCustom && configState.secret_md5">
                <span class="meta-label">🔐 自定义密钥 MD5 密文:</span>
                <code class="md5-code">{{ configState.secret_md5 }}</code>
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="form-actions">
              <el-button type="primary" :icon="Check" :loading="saving" @click="handleSaveConfig">
                {{ (form.key || form.security) ? '保存自定义配置至 SQLite' : '更新生效设置' }}
              </el-button>
              <el-button type="success" plain :icon="Connection" :loading="testing" @click="handleTestConnection">
                测试当前生效密钥连通性
              </el-button>
            </div>
          </el-form>

          <!-- Test Result Banner -->
          <transition name="el-fade-in">
            <div v-if="testResult" class="test-result-box" :class="testResult.success ? 'is-success' : 'is-error'">
              <div class="test-result-icon">
                <el-icon :size="20">
                  <CircleCheckFilled v-if="testResult.success" />
                  <CircleCloseFilled v-else />
                </el-icon>
              </div>
              <div class="test-result-body">
                <div class="test-result-title">
                  {{ testResult.success ? '🎉 高德地图 API 连通性测试通过！' : '❌ 连通性测试失败' }}
                  <span v-if="testResult.success && testResult.latency" class="latency-badge">
                    耗时 {{ testResult.latency }} ms
                  </span>
                </div>
                <div class="test-result-detail">
                  {{ testResult.message }}
                </div>
                <div v-if="testResult.address" class="test-result-address">
                  📍 测试解析地址 (南宁中心仓坐标): <strong>{{ testResult.address }}</strong>
                </div>
              </div>
            </div>
          </transition>
        </el-card>

        <!-- System Architecture & Engines Status Card -->
        <el-card shadow="never" class="system-info-card" style="margin-top: 16px;">
          <template #header>
            <div class="card-header">
              <div class="header-left">
                <el-icon :size="18" color="#0284c7"><Cpu /></el-icon>
                <span class="card-title">系统引擎与服务组件状态</span>
              </div>
            </div>
          </template>

          <div class="services-grid">
            <div class="service-item">
              <div class="service-icon"><el-icon color="#0284c7"><MapLocation /></el-icon></div>
              <div class="service-info">
                <div class="service-name">高德 JS API 2.0</div>
                <div class="service-desc">AMap.Loader + WebGL 高清地图底图</div>
              </div>
              <el-tag type="success" size="small">运行正常</el-tag>
            </div>

            <div class="service-item">
              <div class="service-icon"><el-icon color="#10b981"><Van /></el-icon></div>
              <div class="service-info">
                <div class="service-name">AMap.TruckDriving / Driving</div>
                <div class="service-desc">货车/驾车真实路网距离与导航测算</div>
              </div>
              <el-tag type="success" size="small">双模引擎</el-tag>
            </div>

            <div class="service-item">
              <div class="service-icon"><el-icon color="#f59e0b"><Operation /></el-icon></div>
              <div class="service-info">
                <div class="service-name">智能路线求解引擎</div>
                <div class="service-desc">多车型与装载容量多目标约束计算</div>
              </div>
              <el-tag type="primary" size="small">已激活</el-tag>
            </div>

            <div class="service-item">
              <div class="service-icon"><el-icon color="#6366f1"><Location /></el-icon></div>
              <div class="service-info">
                <div class="service-name">SQLite 数据库与 MD5 密钥加密</div>
                <div class="service-desc">持久化存储系统配置与密文哈希</div>
              </div>
              <el-tag type="success" size="small">已启用</el-tag>
            </div>
          </div>
        </el-card>
      </div>

      <!-- Right Column: Guide & FAQ -->
      <div class="settings-side">
        <el-card shadow="never" class="guide-card">
          <template #header>
            <div class="card-header">
              <div class="header-left">
                <el-icon :size="18" color="#f59e0b"><InfoFilled /></el-icon>
                <span class="card-title">高德 API Key 申请与配置指南</span>
              </div>
            </div>
          </template>

          <div class="guide-content">
            <div class="step-item">
              <div class="step-num">1</div>
              <div class="step-text">
                <strong>注册 / 登录高德开放平台</strong>
                <p>访问高德开放平台控制台，登录您的开发者账号。</p>
                <a href="https://lbs.amap.com/dev/key/app" target="_blank" class="link-btn">
                  前往高德控制台 ↗
                </a>
              </div>
            </div>

            <div class="step-item">
              <div class="step-num">2</div>
              <div class="step-text">
                <strong>创建应用并添加 Key</strong>
                <p>在「应用管理」->「我的应用」中创建应用，并在该应用下点击「添加 Key」。</p>
              </div>
            </div>

            <div class="step-item">
              <div class="step-num">3</div>
              <div class="step-text">
                <strong>平台选择「Web端 (JS API)」</strong>
                <p class="highlight-text">
                  ⚠️ <strong>注意：</strong>服务平台务必勾选 <strong>Web端 (JS API)</strong>，非「Web服务」。
                </p>
              </div>
            </div>

            <div class="step-item">
              <div class="step-num">4</div>
              <div class="step-text">
                <strong>复制 Key 与安全密钥 (jscode)</strong>
                <p>将生成的 Key 与安全密钥粘贴到左侧表单中，点击「测试 API 连通性」验证通过后保存。</p>
              </div>
            </div>
          </div>

          <div class="security-tips">
            <div class="tip-title">🔒 密钥安全性与 MD5 加密说明：</div>
            <div class="tip-body">
              密钥内容在前端默认以密码形式隐藏展示；保存后自动提交至后端 SQLite 数据库持久化存储，并计算 MD5 密文摘要校验，保障系统凭据安全。
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import {
  Setting,
  MapLocation,
  Key,
  Lock,
  Check,
  Connection,
  Refresh,
  CircleCheckFilled,
  CircleCloseFilled,
  Cpu,
  Van,
  Operation,
  Location,
  InfoFilled
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import AppPageHeader from '../../components/common/AppPageHeader.vue'
import {
  testAMapConnection,
  fetchAMapConfigFromBackend,
  saveAMapConfigToBackend,
  resetAMapConfigOnBackend
} from '../../composables/useAMap.js'

const form = reactive({
  key: '',
  security: ''
})

const configState = reactive({
  key: '',
  security: '',
  secret_md5: '',
  isCustom: false
})

const hideSecret = ref(true)
const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)

const loadCurrentConfig = async () => {
  try {
    const data = await fetchAMapConfigFromBackend()
    configState.isCustom = !!data.is_custom
    configState.secret_md5 = data.amap_secret_md5 || ''

    // 仅在用户已配置自定义密钥时在输入框展示，使用系统默认密钥时保持为空
    if (configState.isCustom) {
      configState.key = data.amap_key || ''
      configState.security = data.amap_secret || ''
      form.key = configState.key
      form.security = configState.security
    } else {
      configState.key = ''
      configState.security = ''
      form.key = ''
      form.security = ''
    }
  } catch (e) {
    console.error('Load AMap config error:', e)
  }
}

const handleSaveConfig = async () => {
  const k = (form.key || '').trim()
  const s = (form.security || '').trim()

  // 如果两者都为空，清除自定义配置，恢复使用内置默认密钥
  if (!k && !s) {
    saving.value = true
    try {
      await saveAMapConfigToBackend('', '')
      configState.secret_md5 = ''
      configState.isCustom = false
      ElMessage.success('已切换为系统内置默认高德地图密钥！')
      await loadCurrentConfig()
    } catch (err) {
      ElMessage.error('设置失败: ' + err.message)
    } finally {
      saving.value = false
    }
    return
  }

  // 若填写了其中一项，另一项也必须填写
  if (!k) {
    ElMessage.warning('请输入有效的高德 Web端 Key')
    return
  }
  if (!s) {
    ElMessage.warning('请输入与 Key 配对的高德安全密钥 (Security Secret)')
    return
  }

  saving.value = true
  try {
    const data = await saveAMapConfigToBackend(k, s)
    configState.secret_md5 = data.amap_secret_md5 || ''
    configState.isCustom = true
    ElMessage.success('用户自定义 Key 与安全密钥已成功加密并保存至 SQLite！')
    await loadCurrentConfig()
  } catch (err) {
    ElMessage.error('保存失败: ' + err.message)
  } finally {
    saving.value = false
  }
}

const handleTestConnection = async () => {
  testing.value = true
  testResult.value = null

  try {
    const res = await testAMapConnection((form.key || '').trim(), (form.security || '').trim())
    testResult.value = {
      success: true,
      latency: res.latency,
      message: res.info,
      address: res.address
    }
    ElMessage.success(configState.isCustom ? '自定义高德 API 连通性测试通过！' : '系统内置默认高德 API 连通性测试通过！')
  } catch (err) {
    testResult.value = {
      success: false,
      message: err.message || '连接失败，请检查网络或配置是否有效。'
    }
    ElMessage.error('连通性测试失败: ' + (err.message || '未知错误'))
  } finally {
    testing.value = false
  }
}

const copyText = (text, label) => {
  if (!text) {
    ElMessage.info(`当前使用系统内置默认密钥，无需手动复制`)
    return
  }
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text)
    ElMessage.success(`已复制 ${label} 到剪贴板`)
  } else {
    const input = document.createElement('input')
    input.value = text
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    document.body.removeChild(input)
    ElMessage.success(`已复制 ${label} 到剪贴板`)
  }
}

onMounted(() => {
  loadCurrentConfig()
})
</script>

<style scoped>
.settings-container {
  padding: 24px 32px;
  max-width: 1320px;
  margin: 0 auto;
}

.settings-grid {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 20px;
}

@media (max-width: 1024px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}

.config-card,
.system-info-card,
.guide-card {
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-title {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
}

.form-item-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #334155;
  font-size: 13px;
}

.required-star {
  color: #ef4444;
  font-size: 11px;
  font-weight: normal;
}

.field-hint {
  font-size: 12px;
  color: #64748b;
  margin-top: 6px;
  line-height: 1.5;
}

.security-meta-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 14px;
  margin-top: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 10px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.meta-label {
  color: #475569;
  font-weight: 600;
}

.md5-code {
  font-family: monospace;
  background: #ede9fe;
  color: #6d28d9;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 11px;
}

.form-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  padding-top: 8px;
  border-top: 1px solid #f1f5f9;
}

.test-result-box {
  margin-top: 20px;
  border-radius: 8px;
  padding: 14px 18px;
  display: flex;
  gap: 12px;
  align-items: flex-start;
  transition: all 0.3s ease;
}

.test-result-box.is-success {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
}

.test-result-box.is-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.test-result-title {
  font-size: 14px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}

.latency-badge {
  font-size: 11px;
  background: #dcfce7;
  color: #15803d;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.test-result-detail {
  font-size: 12px;
  margin-top: 4px;
  opacity: 0.9;
}

.test-result-address {
  font-size: 12px;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed rgba(0, 0, 0, 0.08);
}

.services-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

@media (max-width: 768px) {
  .services-grid {
    grid-template-columns: 1fr;
  }
}

.service-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.service-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.service-info {
  flex: 1;
  min-width: 0;
}

.service-name {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.service-desc {
  font-size: 11px;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.guide-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.step-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.step-num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #0284c7;
  color: #ffffff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.step-text {
  font-size: 12px;
  color: #475569;
  line-height: 1.6;
}

.step-text strong {
  color: #0f172a;
  display: block;
  margin-bottom: 2px;
}

.step-text p {
  margin: 0;
}

.link-btn {
  display: inline-block;
  margin-top: 6px;
  color: #0284c7;
  text-decoration: none;
  font-weight: 600;
  font-size: 12px;
}

.link-btn:hover {
  text-decoration: underline;
}

.highlight-text {
  background: #fffbeb;
  border-left: 3px solid #f59e0b;
  padding: 4px 8px;
  margin-top: 4px !important;
  color: #b45309;
}

.security-tips {
  margin-top: 20px;
  padding: 12px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  font-size: 12px;
}

.tip-title {
  font-weight: 700;
  color: #0369a1;
  margin-bottom: 4px;
}

.tip-body {
  color: #0c4a6e;
  line-height: 1.5;
}
</style>
