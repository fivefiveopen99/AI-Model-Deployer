<template>
  <div class="deployment-inference-page">
    <el-page-header @back="goBack" title="命令推理" />

    <el-card v-if="deployment" class="detail-card">
      <template #header>
        <div class="card-header">
          <div>
            <div class="page-title">{{ deployment.name }}</div>
            <div class="page-subtitle">{{ deployment.image || '镜像部署' }}</div>
          </div>
          <el-tag :type="getDeploymentStatusType(deployment.status)">
            {{ getDeploymentStatusText(deployment.status) }}
          </el-tag>
        </div>
      </template>

      <el-alert
        v-if="deployment.source_type !== 'image'"
        title="只有镜像部署支持命令推理"
        type="info"
        :closable="false"
        show-icon
      />
      <el-alert
        v-else-if="!inferenceEnabled"
        title="该部署未配置推理命令"
        type="warning"
        :closable="false"
        show-icon
      />
      <template v-else>
        <div class="section-subtitle">推理命令模板</div>
        <pre class="config-code">{{ inferenceConfig.command_template }}</pre>

        <el-descriptions :column="2" border class="meta-table">
          <el-descriptions-item label="K8s Deployment">
            {{ deployment.k8s_deployment_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="结果目录">
            {{ inferenceConfig.result_path || '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="inferenceVariableNames.length" class="variable-form">
          <div class="section-subtitle">变量输入</div>
          <div class="variable-grid">
            <div v-for="name in inferenceVariableNames" :key="name" class="variable-field">
              <label>{{ name }}</label>
              <el-input v-model="inferenceVariables[name]" :placeholder="`请输入 ${name}`" />
            </div>
          </div>
        </div>

        <div class="actions-row">
          <el-button
            type="primary"
            @click="runInference"
            :loading="inferenceRunning"
            :disabled="!deployment.k8s_deployment_name"
          >
            <el-icon><Promotion /></el-icon>
            开始推理
          </el-button>
          <el-button @click="refreshInferenceResult" :loading="inferenceResultLoading">
            <el-icon><Refresh /></el-icon>
            刷新结果
          </el-button>
          <el-button @click="router.push(`/deployments/${deployment.id}`)">
            返回详情
          </el-button>
        </div>

        <div v-if="currentInferenceTaskId" class="progress-block">
          <el-progress :percentage="inferenceProgress" :status="inferenceProgress === 100 && !inferenceError ? 'success' : ''" />
          <div class="progress-message">{{ inferenceProgressMessage || '等待推理开始...' }}</div>
          <el-alert
            v-if="inferenceError"
            :title="inferenceError"
            type="error"
            show-icon
            :closable="false"
          />
        </div>

        <div v-if="inferenceResult" class="result-block">
          <div class="section-subtitle">最近一次推理结果</div>
          <el-descriptions :column="2" border class="meta-table">
            <el-descriptions-item label="开始时间">{{ inferenceResult.started_at || '-' }}</el-descriptions-item>
            <el-descriptions-item label="结束时间">{{ inferenceResult.finished_at || '-' }}</el-descriptions-item>
            <el-descriptions-item label="退出码">{{ inferenceResult.exit_code ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="结果文件数">{{ inferenceFiles.length }}</el-descriptions-item>
          </el-descriptions>

          <div>
            <div class="section-subtitle">实时输出</div>
            <div ref="logOutputRef" class="logs-content logs-stream">
              <template v-if="outputLines.length">
                <div
                  v-for="(line, index) in outputLines"
                  :key="`${index}-${line}`"
                  class="log-line"
                >
                  <span class="log-line-number">{{ index + 1 }}</span>
                  <code class="log-line-text">{{ line || ' ' }}</code>
                </div>
              </template>
              <div v-else class="log-empty">无输出</div>
            </div>
          </div>

          <div class="result-files">
            <div class="section-subtitle">结果</div>
            <el-table v-if="inferenceFiles.length" :data="inferenceFiles" size="small" stripe>
              <el-table-column label="预览" width="100">
                <template #default="{ row }">
                  <img
                    v-if="row.kind === 'image' && imagePreviewCache[row.file_key]"
                    :src="imagePreviewCache[row.file_key]"
                    :alt="row.name"
                    class="result-thumbnail"
                    @click="openImagePreview(row)"
                  />
                  <el-button
                    v-else-if="row.kind === 'image'"
                    size="small"
                    text
                    :loading="isImagePreviewLoading(row.file_key)"
                    @click="loadImagePreview(row, { force: true })"
                  >
                    {{ getImagePreviewActionText(row.file_key) }}
                  </el-button>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column prop="name" label="文件名" min-width="240" />
              <el-table-column prop="kind" label="类型" width="100" />
              <el-table-column label="大小" width="120">
                <template #default="{ row }">{{ formatFileSize(row.size) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="180">
                <template #default="{ row }">
                  <el-button size="small" @click="previewFile(row)" :disabled="!row.previewable">预览</el-button>
                  <el-button
                    size="small"
                    type="primary"
                    :loading="Boolean(downloadLoading[row.file_key])"
                    @click="downloadFile(row)"
                  >
                    下载
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-else description="暂无结果文件" />
          </div>
        </div>
      </template>
    </el-card>

    <el-skeleton v-else :rows="8" animated />

    <el-dialog v-model="textPreviewVisible" title="文档预览" width="800px">
      <pre class="document-preview">{{ textPreviewContent || '无可预览内容' }}</pre>
    </el-dialog>

    <el-dialog v-model="pdfPreviewVisible" title="PDF预览" width="900px">
      <iframe v-if="pdfPreviewUrl" :src="pdfPreviewUrl" class="pdf-frame" />
    </el-dialog>

    <el-dialog v-model="imagePreviewVisible" title="图片预览" width="900px">
      <div class="image-preview-dialog">
        <img v-if="imagePreviewDialogUrl" :src="imagePreviewDialogUrl" alt="结果预览" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useDeploymentsStore } from '@/stores/deployments'
import { getDeploymentStatusText, getDeploymentStatusType } from '@/utils/formatters'
import { useWebSocket } from '@/composables/useWebSocket'

const PREVIEW_CONCURRENCY = 4

const route = useRoute()
const router = useRouter()
const deploymentsStore = useDeploymentsStore()
const { lastMessage, subscribe, unsubscribe } = useWebSocket()

const deployment = ref(null)
const inferenceResult = ref(null)
const inferenceResultLoading = ref(false)
const currentInferenceTaskId = ref('')
const inferenceProgress = ref(0)
const inferenceProgressMessage = ref('')
const inferenceRunning = ref(false)
const inferenceError = ref('')
const streamedOutput = ref('')
const inferenceVariables = reactive({})
const logOutputRef = ref(null)

const textPreviewVisible = ref(false)
const textPreviewContent = ref('')
const pdfPreviewVisible = ref(false)
const pdfPreviewUrl = ref('')
const imagePreviewVisible = ref(false)
const imagePreviewDialogUrl = ref('')
const imagePreviewCache = reactive({})
const imagePreviewStatus = reactive({})
const imagePreviewErrors = reactive({})
const downloadLoading = reactive({})
const previewBatchToken = ref(0)
const imagePreviewRequests = new Map()

const inferenceConfig = computed(() => deployment.value?.inference_config || {})
const inferenceEnabled = computed(() => Boolean(inferenceConfig.value?.enabled))
const inferenceVariableNames = computed(() => inferenceConfig.value?.variable_names || [])
const inferenceFiles = computed(() => inferenceResult.value?.files || [])
const imageFiles = computed(() => inferenceFiles.value.filter((file) => file.kind === 'image'))

const normalizeOutputText = (text) => {
  return (text || '')
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .trim()
}

const outputText = computed(() => {
  if (streamedOutput.value.trim()) {
    return streamedOutput.value
  }
  const parts = []
  if (inferenceResult.value?.stdout?.trim()) {
    parts.push(inferenceResult.value.stdout.trim())
  }
  if (inferenceResult.value?.stderr?.trim()) {
    parts.push(inferenceResult.value.stderr.trim())
  }
  return parts.join('\n')
})

const outputLines = computed(() => {
  const normalized = normalizeOutputText(outputText.value)
  if (!normalized) {
    return []
  }
  return normalized.split('\n')
})

const getPreviewUrl = (file) => imagePreviewCache[file.file_key] || `/api/v1/deployments/${deployment.value.id}/inference-files/${file.file_key}/preview`

const scrollLogOutputToBottom = async () => {
  await nextTick()
  if (!logOutputRef.value) return
  logOutputRef.value.scrollTop = logOutputRef.value.scrollHeight
}

const clearImagePreviewState = () => {
  previewBatchToken.value += 1
  imagePreviewRequests.clear()
  Object.values(imagePreviewCache).forEach((url) => {
    window.URL.revokeObjectURL(url)
  })
  Object.keys(imagePreviewCache).forEach((key) => {
    delete imagePreviewCache[key]
  })
  Object.keys(imagePreviewStatus).forEach((key) => {
    delete imagePreviewStatus[key]
  })
  Object.keys(imagePreviewErrors).forEach((key) => {
    delete imagePreviewErrors[key]
  })
  imagePreviewVisible.value = false
  imagePreviewDialogUrl.value = ''
}

const getBlobContentType = (response) => {
  return response?.data?.type
    || response?.headers?.['content-type']
    || response?.headers?.['Content-Type']
    || 'application/octet-stream'
}

const createBlobFromResponse = (response) => {
  if (response?.data instanceof Blob) {
    return response.data
  }
  return new Blob([response?.data], { type: getBlobContentType(response) })
}

const extractResponseErrorMessage = async (error, fallbackMessage) => {
  const responseData = error?.response?.data
  if (responseData instanceof Blob) {
    try {
      const text = await responseData.text()
      if (text) {
        try {
          const parsed = JSON.parse(text)
          return parsed?.detail || parsed?.message || text || fallbackMessage
        } catch {
          return text || fallbackMessage
        }
      }
    } catch {
      return fallbackMessage
    }
  }
  return error?.response?.data?.detail || error?.message || fallbackMessage
}

const initInferenceVariables = () => {
  const activeNames = new Set(inferenceVariableNames.value)
  Object.keys(inferenceVariables).forEach((key) => {
    if (!activeNames.has(key)) {
      delete inferenceVariables[key]
    }
  })
  inferenceVariableNames.value.forEach((name) => {
    if (!(name in inferenceVariables)) {
      inferenceVariables[name] = ''
    }
  })
}

const isImagePreviewLoading = (fileKey) => {
  return imagePreviewStatus[fileKey] === 'loading' || imagePreviewStatus[fileKey] === 'retrying'
}

const getImagePreviewActionText = (fileKey) => {
  if (imagePreviewStatus[fileKey] === 'retrying') {
    return '重试中'
  }
  if (imagePreviewErrors[fileKey]) {
    return '重试预览'
  }
  if (imagePreviewStatus[fileKey] === 'loading') {
    return '加载中'
  }
  return '加载预览'
}

const refreshInferenceResult = async () => {
  if (!deployment.value) return
  inferenceResultLoading.value = true
  try {
    clearImagePreviewState()
    inferenceResult.value = await deploymentsStore.fetchInferenceResult(deployment.value.id)
  } catch (error) {
    ElMessage.error('获取推理结果失败')
  } finally {
    inferenceResultLoading.value = false
  }

  try {
    await preloadImagePreviews()
  } catch (error) {
    console.error('Failed to preload inference previews:', error)
  }
}

const runInference = async () => {
  if (!deployment.value) return
  inferenceRunning.value = true
  inferenceError.value = ''
  inferenceProgress.value = 0
  inferenceProgressMessage.value = ''
  streamedOutput.value = ''
  try {
    const variables = {}
    inferenceVariableNames.value.forEach((name) => {
      variables[name] = inferenceVariables[name] || ''
    })
    const task = await deploymentsStore.runInference(deployment.value.id, variables)
    currentInferenceTaskId.value = task.task_id
    subscribe(task.task_id)
  } catch (error) {
    inferenceRunning.value = false
    inferenceError.value = error.response?.data?.detail || error.message
    ElMessage.error(`启动推理失败: ${inferenceError.value}`)
  }
}

const previewDocument = async (file) => {
  if (!deployment.value || !file.previewable) return
  if (file.kind === 'pdf') {
    pdfPreviewUrl.value = `${getPreviewUrl(file)}?ts=${Date.now()}`
    pdfPreviewVisible.value = true
    return
  }
  try {
    const response = await deploymentsStore.previewInferenceFile(deployment.value.id, file.file_key, 'text')
    textPreviewContent.value = response.data || ''
    textPreviewVisible.value = true
  } catch (error) {
    ElMessage.error(await extractResponseErrorMessage(error, '文档预览失败'))
  }
}

const previewFile = (file) => {
  if (file.kind === 'image') {
    openImagePreview(file)
    return
  }
  previewDocument(file)
}

const loadImagePreview = async (file, { force = false } = {}) => {
  if (!deployment.value || file.kind !== 'image') return
  if (!force && imagePreviewCache[file.file_key]) {
    return true
  }
  if (imagePreviewRequests.has(file.file_key)) {
    return imagePreviewRequests.get(file.file_key)
  }

  const batchToken = previewBatchToken.value
  const currentStatus = imagePreviewStatus[file.file_key]
  imagePreviewStatus[file.file_key] = force && (imagePreviewErrors[file.file_key] || currentStatus === 'failed')
    ? 'retrying'
    : 'loading'
  delete imagePreviewErrors[file.file_key]

  let requestPromise = null
  requestPromise = (async () => {
    try {
      const response = await deploymentsStore.previewInferenceFile(deployment.value.id, file.file_key, 'blob')
      const blob = createBlobFromResponse(response)
      const objectUrl = window.URL.createObjectURL(blob)

      if (batchToken !== previewBatchToken.value) {
        window.URL.revokeObjectURL(objectUrl)
        return false
      }

      if (imagePreviewCache[file.file_key]) {
        window.URL.revokeObjectURL(imagePreviewCache[file.file_key])
      }
      imagePreviewCache[file.file_key] = objectUrl
      imagePreviewStatus[file.file_key] = 'loaded'
      delete imagePreviewErrors[file.file_key]
      return true
    } catch (error) {
      if (batchToken === previewBatchToken.value) {
        imagePreviewErrors[file.file_key] = await extractResponseErrorMessage(error, '图片预览失败')
        imagePreviewStatus[file.file_key] = 'failed'
      }
      return false
    } finally {
      imagePreviewRequests.delete(file.file_key)
    }
  })()

  imagePreviewRequests.set(file.file_key, requestPromise)
  return requestPromise
}

const openImagePreview = async (file) => {
  if (!imagePreviewCache[file.file_key]) {
    await loadImagePreview(file, { force: true })
  }
  if (!imagePreviewCache[file.file_key]) {
    ElMessage.error(imagePreviewErrors[file.file_key] || '图片预览失败')
    return
  }
  imagePreviewDialogUrl.value = imagePreviewCache[file.file_key]
  imagePreviewVisible.value = true
}

const downloadFile = async (file) => {
  if (!deployment.value) return
  downloadLoading[file.file_key] = true
  try {
    const response = await deploymentsStore.downloadInferenceFile(deployment.value.id, file.file_key)
    const blob = createBlobFromResponse(response)
    const objectUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = file.name
    link.rel = 'noopener'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.setTimeout(() => {
      window.URL.revokeObjectURL(objectUrl)
    }, 1000)
  } catch (error) {
    ElMessage.error(await extractResponseErrorMessage(error, '文件下载失败'))
  } finally {
    downloadLoading[file.file_key] = false
  }
}

const preloadImagePreviews = async () => {
  if (!deployment.value) return
  const files = imageFiles.value.filter((file) => !imagePreviewCache[file.file_key])
  if (!files.length) return

  const batchToken = previewBatchToken.value
  let cursor = 0
  const workerCount = Math.min(PREVIEW_CONCURRENCY, files.length)

  await Promise.all(Array.from({ length: workerCount }, async () => {
    while (cursor < files.length) {
      if (batchToken !== previewBatchToken.value) {
        return
      }
      const nextFile = files[cursor]
      cursor += 1
      await loadImagePreview(nextFile)
    }
  }))
}

const resetDownloadState = () => {
  Object.keys(downloadLoading).forEach((key) => {
    delete downloadLoading[key]
  })
}

watch(inferenceFiles, () => {
  resetDownloadState()
  if (!inferenceFiles.value.length) {
    clearImagePreviewState()
  }
})

const formatFileSize = (size) => {
  if (!size && size !== 0) return '-'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

const goBack = () => {
  if (deployment.value) {
    router.push(`/deployments/${deployment.value.id}`)
    return
  }
  router.back()
}

watch(inferenceVariableNames, () => {
  initInferenceVariables()
}, { immediate: true })

watch(outputLines, () => {
  scrollLogOutputToBottom()
})

watch(lastMessage, async (message) => {
  if (!message || message.task_id !== currentInferenceTaskId.value) {
    return
  }

  if (message.type === 'log_history') {
    streamedOutput.value = (message.logs || []).join('')
    return
  }

  if (message.type !== 'progress') {
    return
  }

  inferenceProgress.value = message.progress || 0
  inferenceProgressMessage.value = message.message || ''
  if (message.data?.log) {
    streamedOutput.value += message.data.log
  }

  if (message.data?.error) {
    inferenceRunning.value = false
    inferenceError.value = message.message || '推理失败'
    currentInferenceTaskId.value = ''
    await refreshInferenceResult()
    return
  }

  if (message.progress === 100) {
    inferenceRunning.value = false
    inferenceError.value = ''
    currentInferenceTaskId.value = ''
    await refreshInferenceResult()
    ElMessage.success('推理完成')
  }
})

onMounted(async () => {
  try {
    deployment.value = await deploymentsStore.fetchDeploymentDetail(route.params.id)
    inferenceResult.value = deployment.value?.last_inference_result || null
    initInferenceVariables()
    if (deployment.value?.source_type === 'image' && deployment.value?.inference_config?.enabled) {
      await refreshInferenceResult()
    }
  } catch (error) {
    ElMessage.error('获取推理页面失败')
  }
})

onUnmounted(() => {
  if (currentInferenceTaskId.value) {
    unsubscribe(currentInferenceTaskId.value)
  }
  resetDownloadState()
  clearImagePreviewState()
})
</script>

<style scoped>
.deployment-inference-page {
  padding: 0;
}

.detail-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
}

.page-subtitle {
  margin-top: 4px;
  font-family: monospace;
  font-size: 12px;
  color: #909399;
  word-break: break-all;
}

.section-subtitle {
  margin: 0 0 12px;
  font-size: 15px;
  font-weight: 600;
}

.config-code,
.logs-content,
.document-preview {
  background: #0f172a;
  color: #e2e8f0;
  padding: 16px;
  border-radius: 8px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: monospace;
}

.logs-stream {
  max-height: 420px;
  overflow-y: auto;
}

.log-line {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}

.log-line + .log-line {
  margin-top: 6px;
}

.log-line-number {
  color: #94a3b8;
  text-align: right;
  user-select: none;
}

.log-line-text {
  color: inherit;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
}

.log-empty {
  color: #94a3b8;
}

.meta-table,
.variable-form,
.progress-block,
.result-block {
  margin-top: 16px;
}

.variable-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.variable-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.actions-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 16px;
}

.progress-message {
  color: #606266;
  font-size: 13px;
  margin-top: 8px;
}

.result-files {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-thumbnail {
  width: 56px;
  height: 56px;
  object-fit: cover;
  border-radius: 6px;
  cursor: pointer;
  display: block;
  background: #f8fafc;
}

.pdf-frame {
  width: 100%;
  height: 70vh;
  border: 0;
}

.image-preview-dialog {
  display: flex;
  justify-content: center;
}

.image-preview-dialog img {
  max-width: 100%;
  max-height: 70vh;
}

@media (max-width: 900px) {
  .variable-grid {
    grid-template-columns: 1fr;
  }
}
</style>
