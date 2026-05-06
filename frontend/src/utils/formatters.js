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
  return new Date(date).toLocaleString('zh-CN')
}
