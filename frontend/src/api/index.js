import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Models API
export const modelsApi = {
  getList: (params) => api.get('/models', { params }),
  getDetail: (id) => api.get(`/models/${id}`),
  create: (data) => api.post('/models', data),
  createFinetune: (formData, onProgress) => api.post('/models/finetune', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 3600000,
    onUploadProgress: onProgress
  }),
  update: (id, data) => api.put(`/models/${id}`, data),
  delete: (id) => api.delete(`/models/${id}`),
  upload: (formData, onProgress) => api.post('/models/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 3600000,  // 1小时超时
    onUploadProgress: onProgress
  }),
  createFromUrl: (formData, onProgress) => api.post('/models/from-url', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 3600000,
    onUploadProgress: onProgress
  }),
  build: (id, data) => api.post(`/models/${id}/build`, data, {
    timeout: 3600000  // 1小时超时，因为构建镜像可能需要很长时间
  }),
  stopBuild: (id) => api.post(`/models/${id}/stop-build`),
  resetStatus: (id) => api.post(`/models/${id}/reset-status`),
  getStatus: (id) => api.get(`/models/${id}/status`)
}

// Deployments API
export const deploymentsApi = {
  getList: (params) => api.get('/deployments', { params }),
  getDetail: (id) => api.get(`/deployments/${id}`),
  create: (data) => api.post('/deployments', data),
  deploy: (id) => api.post(`/deployments/${id}/deploy`),
  update: (id, data) => api.put(`/deployments/${id}`, data),
  delete: (id) => api.delete(`/deployments/${id}`),
  scale: (id, replicas) => api.put(`/deployments/${id}/scale?replicas=${replicas}`),
  getStatus: (id) => api.get(`/deployments/${id}/status`),
  getLogs: (id, tailLines = 100) => api.get(`/deployments/${id}/logs?tail_lines=${tailLines}`),
  getK8sList: (namespace) => api.get('/deployments/k8s/list', { params: { namespace } })
}

// System API
export const systemApi = {
  getStatus: () => api.get('/system/status'),
  healthCheck: () => api.get('/system/health')
}

export default api
