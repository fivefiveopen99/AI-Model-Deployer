<template>
  <div class="page-shell deployment-inference-page">
    <PageHero
      eyebrow="命令工作台"
      :title="deployment?.name || '命令工作台'"
      description="面向镜像部署的命令执行工作台，统一查看变量输入、实时输出和结果文件。"
    >
      <template #meta v-if="deployment">
        <span class="badge-pill">状态 {{ getDeploymentStatusText(deployment.status) }}</span>
        <span class="badge-pill">{{ deployment.image || '镜像命令工作台' }}</span>
      </template>
      <template #actions>
        <el-button @click="goBack">返回</el-button>
        <el-button v-if="deployment" @click="router.push(`/deployments/${deployment.id}`)">部署详情</el-button>
      </template>
    </PageHero>

    <template v-if="deployment">
      <el-alert
        v-if="deployment.source_type !== 'image'"
        title="只有镜像部署支持命令工作台"
        type="info"
        :closable="false"
        show-icon
      />
      <el-alert
        v-else-if="!inferenceEnabled"
        title="该部署未配置命令运行参数"
        type="warning"
        :closable="false"
        show-icon
      />
      <template v-else>
        <PanelCard
          eyebrow="命令配置"
          title="命令模板与运行配置"
          description="先检查命令模板、结果目录和部署运行态，再执行任务。"
        >
          <el-alert
            v-if="!deploymentReady"
            title="工作台已创建，但该镜像部署尚未部署到 Kubernetes。请先完成部署，再运行命令。"
            type="warning"
            :closable="false"
            show-icon
            class="workbench-alert"
          />

          <div class="section-subtitle">命令模板</div>
          <CodeBlock :content="inferenceConfig.command_template" />

            <el-descriptions :column="2" border class="meta-table">
              <el-descriptions-item label="访问模式">
                平台命令工作台
              </el-descriptions-item>
            <el-descriptions-item label="K8s 部署">
              {{ deployment.k8s_deployment_name || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="结果目录">
              {{ inferenceConfig.result_path || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="最近运行">
              {{ lastRunStatus }}
            </el-descriptions-item>
          </el-descriptions>

          <div v-if="inferenceVariableNames.length" class="variable-form">
            <div class="section-subtitle">输入参数</div>
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
              :disabled="!deploymentReady"
            >
              <el-icon><Promotion /></el-icon>
              开始运行
            </el-button>
            <el-button @click="refreshInferenceResult" :loading="inferenceResultLoading">
              <el-icon><Refresh /></el-icon>
              刷新结果
            </el-button>
          </div>

          <div v-if="currentInferenceTaskId" class="progress-block">
            <el-progress :percentage="inferenceProgress" :status="inferenceProgress === 100 && !inferenceError ? 'success' : ''" />
            <div class="progress-message">{{ inferenceProgressMessage || '等待命令开始...' }}</div>
            <el-alert
              v-if="inferenceError"
              :title="inferenceError"
              type="error"
              show-icon
              :closable="false"
            />
          </div>
        </PanelCard>

        <PanelCard
          v-if="inferenceResult"
          eyebrow="运行结果"
          title="最近一次运行结果"
          description="结果摘要、实时输出与文件浏览放在同一个工作台中。"
        >
          <template #actions>
            <span v-if="imageFiles.length" class="badge-pill">图片 {{ loadedImageCount }}/{{ imageFiles.length }}</span>
            <el-button
              type="primary"
              plain
              :loading="downloadAllLoading"
              :disabled="!inferenceFiles.length"
              @click="downloadAllResultFiles"
            >
              下载全部结果
            </el-button>
          </template>

          <el-descriptions :column="2" border class="meta-table">
            <el-descriptions-item label="开始时间">{{ inferenceResult.started_at || '-' }}</el-descriptions-item>
            <el-descriptions-item label="结束时间">{{ inferenceResult.finished_at || '-' }}</el-descriptions-item>
            <el-descriptions-item label="退出码">{{ inferenceResult.exit_code ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="结果文件数">{{ inferenceFiles.length }}</el-descriptions-item>
          </el-descriptions>

          <el-alert
            v-if="resultAssetsLoading"
            :title="resultAssetsMessage || '正在加载结果图片...'"
            type="info"
            show-icon
            :closable="false"
            class="workbench-alert"
          />
          <el-alert
            v-else-if="imageFailureCount"
            :title="`有 ${imageFailureCount} 张结果图片未能自动加载，可点击图片或预览按钮重试。`"
            type="warning"
            show-icon
            :closable="false"
            class="workbench-alert"
          />

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

          <div v-if="imageFiles.length" class="result-gallery">
            <div class="section-subtitle">结果图片</div>
            <div class="result-gallery-grid">
              <button
                v-for="file in imageFiles"
                :key="file.file_key"
                type="button"
                class="result-gallery-card"
                @click="openImagePreview(file)"
              >
                <img
                  v-if="imagePreviewCache[file.file_key]"
                  :src="imagePreviewCache[file.file_key]"
                  :alt="file.name"
                  class="result-gallery-image"
                />
                <div v-else class="result-gallery-placeholder">
                  {{ imagePreviewErrors[file.file_key] || (resultAssetsLoading ? '图片加载中' : '点击查看') }}
                </div>
                <div class="result-gallery-meta">
                  <strong>{{ file.name }}</strong>
                  <span>{{ formatFileSize(file.size) }}</span>
                </div>
              </button>
            </div>
          </div>

          <div class="result-files">
            <div class="section-subtitle">结果文件</div>
            <el-table v-if="documentFiles.length" :data="documentFiles" size="small" stripe>
              <el-table-column label="预览" width="100">
                <template #default="{ row }">
                  <span>-</span>
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
            <el-empty v-else description="除图片外暂无其他结果文件" />
          </div>
        </PanelCard>
      </template>
    </template>

    <el-skeleton v-else :rows="8" animated />

    <el-dialog v-model="textPreviewVisible" title="文档预览" width="800px">
      <CodeBlock :content="textPreviewContent || '无可预览内容'" terminal />
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
import PageHero from '@/components/ui/PageHero.vue'
import PanelCard from '@/components/ui/PanelCard.vue'
import CodeBlock from '@/components/ui/CodeBlock.vue'
import { useDeploymentsStore } from '@/stores/deployments'
import { getDeploymentStatusText } from '@/utils/formatters'
import { useWebSocket } from '@/composables/useWebSocket'

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
const downloadAllLoading = ref(false)
const resultAssetsLoading = ref(false)
const resultAssetsMessage = ref('')
const loadedPreviewDigest = ref('')
const previewBatchToken = ref(0)
const imagePreviewRequests = new Map()

const inferenceConfig = computed(() => deployment.value?.inference_config || {})
const inferenceEnabled = computed(() => Boolean(inferenceConfig.value?.enabled))
const inferenceVariableNames = computed(() => inferenceConfig.value?.variable_names || [])
const inferenceFiles = computed(() => inferenceResult.value?.files || [])
const imageFiles = computed(() => inferenceFiles.value.filter((file) => file.kind === 'image'))
const documentFiles = computed(() => inferenceFiles.value.filter((file) => file.kind !== 'image'))
const loadedImageCount = computed(() => imageFiles.value.filter((file) => Boolean(imagePreviewCache[file.file_key])).length)
const imageFailureCount = computed(() => imageFiles.value.filter((file) => Boolean(imagePreviewErrors[file.file_key])).length)
const deploymentReady = computed(() => deployment.value?.status === 'running' && Boolean(deployment.value?.k8s_deployment_name))
const lastRunStatus = computed(() => {
  if (!inferenceResult.value?.finished_at) {
    return '尚未运行'
  }
  if ((inferenceResult.value?.exit_code ?? 1) === 0) {
    return '最近一次运行成功'
  }
  return '最近一次运行失败'
})

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
    if (typeof url === 'string' && url.startsWith('blob:')) {
      window.URL.revokeObjectURL(url)
    }
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
  loadedPreviewDigest.value = ''
  resultAssetsMessage.value = ''
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

const getDownloadFilename = (response, fallbackName) => {
  const disposition = response?.headers?.['content-disposition'] || response?.headers?.['Content-Disposition'] || ''
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1])
  }
  const fallbackMatch = disposition.match(/filename="?([^"]+)"?/i)
  if (fallbackMatch?.[1]) {
    return fallbackMatch[1]
  }
  return fallbackName
}

const restoreInferenceRuntime = (result) => {
  const runtime = result?.runtime || deployment.value?.inference_runtime || {}
  const nextTaskId = runtime.active && runtime.task_id ? runtime.task_id : ''

  if (currentInferenceTaskId.value && currentInferenceTaskId.value !== nextTaskId) {
    unsubscribe(currentInferenceTaskId.value)
  }

  if (!nextTaskId) {
    currentInferenceTaskId.value = ''
    inferenceRunning.value = false
    if (!inferenceError.value) {
      inferenceProgressMessage.value = ''
    }
    return
  }

  currentInferenceTaskId.value = nextTaskId
  inferenceRunning.value = true
  inferenceError.value = ''
  inferenceProgress.value = Number(runtime.progress || 0)
  inferenceProgressMessage.value = runtime.message || '命令运行中'
  streamedOutput.value = Array.isArray(runtime.logs) ? runtime.logs.join('') : ''
  subscribe(nextTaskId)
}

const loadInferenceAssets = async (result, { force = false } = {}) => {
  if (!deployment.value) return

  const resources = result?.resources || {}
  const resultDigest = resources.result_digest || result?.result_digest || ''

  if (!resources.ready || !imageFiles.value.length) {
    resultAssetsLoading.value = false
    resultAssetsMessage.value = ''
    if (!imageFiles.value.length) {
      loadedPreviewDigest.value = resultDigest
    }
    return
  }

  if (!force && resultDigest && loadedPreviewDigest.value === resultDigest && loadedImageCount.value === imageFiles.value.length) {
    return
  }

  resultAssetsLoading.value = true
  resultAssetsMessage.value = `正在加载结果图片（0/${imageFiles.value.length}）`

  try {
    const payload = await deploymentsStore.fetchInferencePreviews(deployment.value.id)
    const nextDigest = payload?.result_digest || resultDigest

    Object.keys(imagePreviewErrors).forEach((key) => {
      delete imagePreviewErrors[key]
    })

    ;(payload?.items || []).forEach((item) => {
      imagePreviewCache[item.file_key] = `data:${item.media_type || 'application/octet-stream'};base64,${item.content_base64}`
      imagePreviewStatus[item.file_key] = 'loaded'
    })

    ;(payload?.failures || []).forEach((item) => {
      imagePreviewErrors[item.file_key] = item.detail || '图片预览失败'
      imagePreviewStatus[item.file_key] = 'failed'
    })

    loadedPreviewDigest.value = nextDigest
    resultAssetsMessage.value = payload?.failures?.length
      ? `已加载 ${payload.loaded}/${payload.total} 张图片，部分文件加载失败`
      : `已加载 ${payload.loaded}/${payload.total} 张图片`
  } catch (error) {
    resultAssetsMessage.value = ''
    ElMessage.error(await extractResponseErrorMessage(error, '批量加载结果图片失败'))
  } finally {
    resultAssetsLoading.value = false
  }
}

const refreshInferenceResult = async () => {
  if (!deployment.value) return
  inferenceResultLoading.value = true
  try {
    clearImagePreviewState()
    inferenceResult.value = await deploymentsStore.fetchInferenceResult(deployment.value.id)
    restoreInferenceRuntime(inferenceResult.value)
  } catch (error) {
    ElMessage.error('获取运行结果失败')
  } finally {
    inferenceResultLoading.value = false
  }

  try {
    await loadInferenceAssets(inferenceResult.value, { force: true })
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
    if (error.response?.status === 409) {
      inferenceRunning.value = false
      await refreshInferenceResult()
      ElMessage.warning('已有任务正在运行，已恢复当前任务状态')
      return
    }
    inferenceRunning.value = false
    inferenceError.value = error.response?.data?.detail || error.message
    ElMessage.error(`启动运行失败: ${inferenceError.value}`)
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

const downloadAllResultFiles = async () => {
  if (!deployment.value || !inferenceFiles.value.length) return
  downloadAllLoading.value = true
  try {
    const response = await deploymentsStore.downloadAllInferenceFiles(deployment.value.id)
    const blob = createBlobFromResponse(response)
    const objectUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = getDownloadFilename(response, `${deployment.value.name || 'results'}.zip`)
    link.rel = 'noopener'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.setTimeout(() => {
      window.URL.revokeObjectURL(objectUrl)
    }, 1000)
  } catch (error) {
    ElMessage.error(await extractResponseErrorMessage(error, '下载全部结果失败'))
  } finally {
    downloadAllLoading.value = false
  }
}

const resetDownloadState = () => {
  Object.keys(downloadLoading).forEach((key) => {
    delete downloadLoading[key]
  })
}

watch(inferenceFiles, () => {
  resetDownloadState()
  if (!inferenceFiles.value.length) {
    resultAssetsLoading.value = false
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
    inferenceError.value = message.message || '命令运行失败'
    currentInferenceTaskId.value = ''
    await refreshInferenceResult()
    return
  }

  if (message.progress === 100) {
    inferenceRunning.value = false
    inferenceError.value = ''
    currentInferenceTaskId.value = ''
    await refreshInferenceResult()
    ElMessage.success('命令运行完成')
  }
})

onMounted(async () => {
  try {
    deployment.value = await deploymentsStore.fetchDeploymentDetail(route.params.id)
    inferenceResult.value = deployment.value?.last_inference_result || null
    restoreInferenceRuntime(inferenceResult.value)
    initInferenceVariables()
    if (deployment.value?.source_type === 'image' && deployment.value?.inference_config?.enabled) {
      await refreshInferenceResult()
    }
  } catch (error) {
    ElMessage.error('获取命令工作台失败')
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
  padding: 2px 0 10px;
}

.section-subtitle {
  margin: 18px 0 12px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ui-text-faint);
}

.logs-content,
.document-preview {
  background: #172028;
  color: #dce8f0;
  padding: 16px;
  border-radius: 18px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: var(--ui-font-mono);
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

.result-gallery {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
}

.result-gallery-card {
  border: 1px solid var(--ui-border);
  background: #fff;
  border-radius: 14px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease;
}

.result-gallery-card:hover {
  border-color: var(--ui-accent);
  transform: translateY(-1px);
}

.result-gallery-image,
.result-gallery-placeholder {
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 10px;
  background: #f4f7f8;
}

.result-gallery-image {
  object-fit: cover;
  display: block;
}

.result-gallery-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  color: var(--ui-text-faint);
  font-size: 12px;
  line-height: 1.5;
}

.result-gallery-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-gallery-meta strong {
  font-size: 13px;
  color: var(--ui-text);
  word-break: break-word;
}

.result-gallery-meta span,
.table-preview-text {
  font-size: 12px;
  color: var(--ui-text-faint);
}

.result-thumbnail {
  width: 56px;
  height: 56px;
  object-fit: cover;
  border-radius: 12px;
  cursor: pointer;
  display: block;
  background: rgba(248, 249, 245, 0.92);
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

.workbench-alert {
  margin-bottom: 14px;
}

@media (max-width: 900px) {
  .variable-grid {
    grid-template-columns: 1fr;
  }
}
</style>
