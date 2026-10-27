import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE || ''

const http = axios.create({ baseURL, timeout: 600000 })

// 统一解包: 成功返回 res.data, 失败抛 Error(detail)
http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const detail = err.response?.data?.detail || err.message
    return Promise.reject(new Error(detail))
  }
)


export const routingApi = {
  solve: (data) => http.post('/api/routing/solve', data),
}

export const clusteringApi = {
  solve: (data) => http.post('/api/clustering/solve', data),
  solveSchedule: (data) => http.post('/api/clustering/solve_schedule', data),
  saveSchedule: (data) => http.post('/api/clustering/save_schedule', data),
  scheduleAlgorithms: () => http.get('/api/clustering/schedule/algorithms'),
}

export const canvasApi = {
  list: (params) => http.get('/api/canvas', { params }),
  get: (canvasId) => http.get(`/api/canvas/${canvasId}`),
  create: (data) => http.post('/api/canvas', data),
  update: (canvasId, data) => http.put(`/api/canvas/${canvasId}`, data),
  delete: (canvasId) => http.delete(`/api/canvas/${canvasId}`),
  getVersions: (canvasId) => http.get(`/api/canvas/${canvasId}/versions`),
  getVersion: (canvasId, versionId) => http.get(`/api/canvas/${canvasId}/versions/${versionId}`),
  createVersion: (canvasId, data) => http.post(`/api/canvas/${canvasId}/versions`, data),
  rollbackVersion: (canvasId, versionId) => http.post(`/api/canvas/${canvasId}/rollback/${versionId}`),
  clone: (canvasId, params) => http.post(`/api/canvas/${canvasId}/clone`, null, { params }),
}

export const depotApi = {
  list: () => http.get('/api/depot/'),
  get: (id) => http.get(`/api/depot/${id}`),
  create: (data) => http.post('/api/depot/', data),
  update: (id, data) => http.put(`/api/depot/${id}`, data),
  delete: (id) => http.delete(`/api/depot/${id}`),
  setDefault: (id) => http.post(`/api/depot/${id}/set_default`),
}

export const vehicleApi = {
  list: () => http.get('/api/vehicle/'),
  create: (data) => http.post('/api/vehicle/', data),
  update: (id, data) => http.put(`/api/vehicle/${id}`, data),
  delete: (id) => http.delete(`/api/vehicle/${id}`),
}

export const storeApi = {
  list: (params) => http.get('/api/store/', { params: { limit: 5000, ...params } }),
  create: (data) => http.post('/api/store/', data),
  update: (id, data) => http.put(`/api/store/${id}`, data),
  delete: (id) => http.delete(`/api/store/${id}`),
  clearAll: () => http.delete('/api/store/clear/all'),
  batchCreate: (data) => http.post('/api/store/batch', data),
}

export const historyApi = {
  list: (params) => http.get('/api/history/', { params }),
  delete: (taskId) => http.delete(`/api/history/${taskId}`),
  clearAll: () => http.delete('/api/history/clear/all'),
}

export const systemApi = {
  getAmapConfig: () => http.get('/api/system/amap-config'),
  saveAmapConfig: (data) => http.post('/api/system/amap-config', data),
  resetAmapConfig: () => http.post('/api/system/amap-config/reset'),
}

export default http



