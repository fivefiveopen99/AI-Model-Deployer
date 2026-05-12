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
  runInference: (id, data) => api.post(`/deployments/${id}/run-inference`, data, {
    timeout: 3600000
  }),
  getInferenceResult: (id) => api.get(`/deployments/${id}/inference-result`),
  getInferencePreviews: (id) => api.get(`/deployments/${id}/inference-previews`),
  previewInferenceFile: (id, fileKey, responseType = 'text') => api.get(
    `/deployments/${id}/inference-files/${fileKey}/preview`,
    { responseType }
  ),
  downloadAllInferenceFiles: (id) => api.get(
    `/deployments/${id}/inference-files/download-all`,
    { responseType: 'blob' }
  ),
  downloadInferenceFile: (id, fileKey) => api.get(
    `/deployments/${id}/inference-files/${fileKey}/download`,
    { responseType: 'blob' }
  ),
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
  healthCheck: () => api.get('/system/health'),
  getNfsDirectories: (path = '') => api.get('/system/nfs/directories', {
    params: { path }
  }),
  getRegistryImages: () => api.get('/system/registry-images'),
  buildRegistryImage: (formData) => api.post('/system/registry-images/build', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 3600000
  }),
  stopRegistryBuild: (taskId) => api.post(`/system/registry-images/build/${taskId}/stop`),
  getLocalRegistryImagePackages: (path = '') => api.get('/system/registry-images/local-packages', {
    params: { path }
  }),
  deleteRegistryImage: (repository, tag) => api.delete('/system/registry-images', {
    params: { repository, tag }
  }),
  uploadRegistryImage: (formData, onProgress) => api.post('/system/registry-images/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 3600000,
    onUploadProgress: onProgress
  }),
  uploadLocalRegistryImage: (formData) => api.post('/system/registry-images/upload-local', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 3600000
  })
}

export default api
