const modelStatusTypes = {
  pending: 'info',
  uploading: 'warning',
  uploaded: 'success',
  building: 'warning',
  built: 'success',
  pushing: 'warning',
  ready: 'success',
  failed: 'danger'
}

const modelStatusTexts = {
  pending: '待处理',
  uploading: '上传中',
  uploaded: '已上传',
  building: '构建中',
  built: '已构建',
  pushing: '分发中',
  ready: '就绪',
  failed: '失败'
}

const deploymentStatusTypes = {
  pending: 'info',
  deploying: 'warning',
  running: 'success',
  failed: 'danger',
  stopped: 'info'
}

const deploymentStatusTexts = {
  pending: '待部署',
  deploying: '部署中',
  running: '运行中',
  failed: '失败',
  stopped: '已停止'
}

export const getModelStatusType = (status) => modelStatusTypes[status] || 'info'

export const getModelStatusText = (status) => modelStatusTexts[status] || status

export const getDeploymentStatusType = (status) => deploymentStatusTypes[status] || 'info'

export const getDeploymentStatusText = (status) => deploymentStatusTexts[status] || status

export const formatDate = (date) => {
  if (!date) return '-'

  const value = typeof date === 'string' ? date : String(date)
  const hasTimezone = /(?:z|[+-]\d{2}:?\d{2})$/i.test(value)
  const normalizedValue = typeof date === 'string' && !hasTimezone ? `${value}Z` : date

  return new Date(normalizedValue).toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    hour12: false
  })
}

export const formatImageRef = (image, tag = '') => {
  if (!image) return '-'

  const imageWithoutRegistry = image.replace(/^[^/]+\/(.+)$/, '$1')
  return tag ? `${imageWithoutRegistry}:${tag}` : imageWithoutRegistry
}
