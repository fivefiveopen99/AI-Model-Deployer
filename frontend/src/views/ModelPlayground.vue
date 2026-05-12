<template>
  <div class="page-shell model-playground-page">
    <PageHero
      eyebrow="Interactive Playground"
      :title="deployment?.name || '模型交互测试'"
      description="统一测试模型服务端点、请求参数和返回结果，避免在外部工具和平台页面之间来回切换。"
    >
      <template #meta v-if="deployment">
        <span class="badge-pill">Status {{ getDeploymentStatusText(deployment.status) }}</span>
        <span class="badge-pill">{{ modelProfile.label }}</span>
        <span class="badge-pill">{{ deployment.endpoint ? 'Endpoint Ready' : 'Pending Deploy' }}</span>
      </template>
      <template #actions>
        <el-button @click="$router.back()">返回</el-button>
        <el-button type="primary" @click="showApiDocs" v-if="deployment?.endpoint">
          <el-icon><Document /></el-icon>
          API 文档
        </el-button>
      </template>
    </PageHero>

    <template v-if="deployment">
      <PanelCard
        eyebrow="Service"
        title="端点与健康检查"
        description="先确认部署服务已经可访问，再进入具体请求。"
      >
        <el-alert
          v-if="!deployment.endpoint"
          title="模型尚未部署，无法进行交互测试"
          type="warning"
          show-icon
          :closable="false"
        />

        <div v-else class="content-stack">
          <div class="endpoint-row">
            <span class="section-label">服务端点</span>
            <el-input v-model="baseUrl" readonly>
              <template #append>
                <el-button @click="copyEndpoint">
                  <el-icon><CopyDocument /></el-icon>
                </el-button>
              </template>
            </el-input>
            <el-button @click="checkHealth" :loading="loading">
              <el-icon><Refresh /></el-icon>
              健康检查
            </el-button>
          </div>

          <div v-if="healthResult" class="health-line">
            <el-tag :type="healthResult.status === 'ok' ? 'success' : 'danger'">
              {{ healthResult.status === 'ok' ? '服务正常' : '服务异常' }}
            </el-tag>
            <span>{{ healthResult.responseTime }}ms</span>
            <span v-if="healthResult.data?.model_type">模型服务类型：{{ healthResult.data.model_type }}</span>
          </div>
        </div>
      </PanelCard>

      <PanelCard
        v-if="deployment.endpoint"
        eyebrow="Request"
        :title="modelProfile.title"
        :description="modelProfile.description"
      >
        <el-form label-position="top">
          <template v-if="modelProfile.kind === 'image'">
            <div class="image-workbench">
              <div class="upload-panel">
                <el-form-item label="输入图片">
                  <el-upload
                    ref="uploadRef"
                    :auto-upload="false"
                    :on-change="handleFileChange"
                    :on-remove="handleFileRemove"
                    :limit="1"
                    drag
                    accept="image/*"
                  >
                    <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                    <div class="el-upload__text">
                      拖拽图片到此处或 <em>点击上传</em>
                    </div>
                  </el-upload>
                </el-form-item>

                <div class="params-grid">
                  <el-form-item label="置信度">
                    <el-slider v-model="imageParams.conf" :min="0.05" :max="0.95" :step="0.05" show-input />
                  </el-form-item>
                  <el-form-item label="IoU">
                    <el-slider v-model="imageParams.iou" :min="0.1" :max="0.9" :step="0.05" show-input />
                  </el-form-item>
                  <el-form-item label="结果图">
                    <el-switch v-model="imageParams.returnImage" active-text="返回标注图" />
                  </el-form-item>
                </div>

                <div class="actions-row">
                  <el-button type="primary" @click="sendPredict" :loading="loading">
                    <el-icon><Promotion /></el-icon>
                    开始预测
                  </el-button>
                  <el-button @click="clearResult">
                    <el-icon><Delete /></el-icon>
                    清空
                  </el-button>
                </div>
              </div>

              <div class="preview-panel">
                <div class="preview-box">
                  <img v-if="imagePreviewUrl" :src="imagePreviewUrl" alt="输入图片预览" />
                  <span v-else>等待上传图片</span>
                </div>
              </div>
            </div>
          </template>

          <template v-else-if="modelProfile.kind === 'text'">
            <el-form-item label="文本输入">
              <el-input v-model="textInput" type="textarea" :rows="8" placeholder="输入要测试的文本" />
            </el-form-item>
            <el-form-item label="参数 JSON">
              <el-input v-model="parametersInput" type="textarea" :rows="4" />
            </el-form-item>
            <div class="actions-row">
              <el-button type="primary" @click="sendPredict" :loading="loading">
                <el-icon><Promotion /></el-icon>
                开始预测
              </el-button>
              <el-button @click="clearResult">
                <el-icon><Delete /></el-icon>
                清空
              </el-button>
            </div>
          </template>

          <template v-else>
            <el-form-item label="请求数据 JSON">
              <el-input v-model="jsonInput" type="textarea" :rows="10" />
            </el-form-item>
            <div class="actions-row">
              <el-button type="primary" @click="sendPredict" :loading="loading">
                <el-icon><Promotion /></el-icon>
                发送请求
              </el-button>
              <el-button @click="clearResult">
                <el-icon><Delete /></el-icon>
                清空
              </el-button>
            </div>
          </template>
        </el-form>
      </PanelCard>

      <PanelCard
        v-if="predictResult"
        eyebrow="Response"
        title="预测结果"
        description="结果摘要、结构化表格和原始返回值集中查看。"
      >
        <div class="result-section">
          <div class="result-header">
            <div class="result-meta">
              <el-tag :type="predictResult.status >= 200 && predictResult.status < 300 ? 'success' : 'danger'">
                HTTP {{ predictResult.status }}
              </el-tag>
              <span>{{ predictResult.responseTime }}ms</span>
            </div>
            <el-button
              v-if="processedImageUrl"
              type="primary"
              @click="downloadProcessedImage"
            >
              <el-icon><Download /></el-icon>
              下载结果图
            </el-button>
          </div>

          <template v-if="modelProfile.kind === 'image' && normalizedImageResult">
            <el-descriptions :column="3" border class="summary-table">
              <el-descriptions-item label="识别数量">{{ normalizedImageResult.count }}</el-descriptions-item>
              <el-descriptions-item label="模型类型">{{ normalizedImageResult.model_type || modelProfile.label }}</el-descriptions-item>
              <el-descriptions-item label="状态">{{ normalizedImageResult.success ? '成功' : '失败' }}</el-descriptions-item>
            </el-descriptions>

            <el-table
              v-if="normalizedImageResult.plates?.length"
              :data="normalizedImageResult.plates"
              stripe
              class="plates-table"
            >
              <el-table-column prop="plate_no" label="车牌号" min-width="140" />
              <el-table-column prop="plate_color" label="颜色" width="100" />
              <el-table-column prop="plate_type" label="类型" width="100" />
              <el-table-column prop="detect_conf" label="检测置信度" width="130">
                <template #default="{ row }">{{ formatNumber(row.detect_conf) }}</template>
              </el-table-column>
              <el-table-column prop="color_conf" label="颜色置信度" width="130">
                <template #default="{ row }">{{ formatNumber(row.color_conf) }}</template>
              </el-table-column>
              <el-table-column prop="bbox" label="位置">
                <template #default="{ row }">{{ row.bbox?.join(', ') || '-' }}</template>
              </el-table-column>
            </el-table>

            <div v-if="processedImageUrl" class="processed-preview">
              <h5>标注结果图</h5>
              <img :src="processedImageUrl" alt="预测标注图" />
            </div>
          </template>

          <CodeBlock class="result-code" :content="formatResult(displayResult)" />
        </div>
      </PanelCard>
    </template>

    <el-skeleton v-else :rows="10" animated />

    <el-dialog v-model="apiDocsVisible" title="API 文档" width="720px">
      <div class="api-docs">
        <h4>健康检查接口</h4>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="URL">{{ baseUrl }}/health</el-descriptions-item>
          <el-descriptions-item label="方法">GET</el-descriptions-item>
        </el-descriptions>

        <h4>预测接口</h4>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="URL">{{ baseUrl }}/predict 或 {{ baseUrl }}/predict/image</el-descriptions-item>
          <el-descriptions-item label="方法">POST</el-descriptions-item>
          <el-descriptions-item label="说明">{{ modelProfile.description }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import PageHero from '@/components/ui/PageHero.vue'
import PanelCard from '@/components/ui/PanelCard.vue'
import CodeBlock from '@/components/ui/CodeBlock.vue'
import { useDeploymentsStore } from '@/stores/deployments'
import { modelsApi } from '@/api'
import { getDeploymentStatusText } from '@/utils/formatters'
import axios from 'axios'

const route = useRoute()
const deploymentsStore = useDeploymentsStore()

const deployment = ref(null)
const model = ref(null)
const loading = ref(false)
const selectedFile = ref(null)
const imagePreviewUrl = ref('')
const processedImageUrl = ref('')
const uploadRef = ref(null)

const jsonInput = ref('{\n  "inputs": {}\n}')
const textInput = ref('')
const parametersInput = ref('{}')
const imageParams = ref({
  conf: 0.3,
  iou: 0.5,
  returnImage: true
})

const healthResult = ref(null)
const predictResult = ref(null)
const apiDocsVisible = ref(false)

const baseUrl = computed(() => {
  if (!deployment.value?.endpoint) return ''
  return deployment.value.endpoint.replace(/\/$/, '')
})

const rawModelType = computed(() => (model.value?.model_type || '').toLowerCase())
const config = computed(() => model.value?.config || {})

const modelProfile = computed(() => {
  const type = rawModelType.value
  const source = `${model.value?.name || ''} ${model.value?.source_path || ''}`.toLowerCase()
  const files = config.value.model_files || {}
  const hasImageWeights = Boolean(files.weights && /\.(pt|pth|onnx|engine)$/i.test(files.weights))
  const isPlate = source.includes('yolo') || source.includes('plate') || type.includes('yolo')
  const isSuperResolution = source.includes('esrgan') || source.includes('realesrgan') || type.includes('esrgan') || type === 'rcan'

  if (isPlate || isSuperResolution || hasImageWeights || ['yolo', 'ultralytics', 'onnx', 'tensorflow', 'pytorch', 'rcan'].includes(type)) {
    return {
      kind: 'image',
      label: isPlate ? '车牌识别图像模型' : (isSuperResolution ? '图像超分模型' : '图像模型'),
      title: isPlate ? '车牌图片预测' : (isSuperResolution ? '图片超分预测' : '图片预测'),
      description: isPlate
        ? '上传车辆图片，返回车牌号、颜色、位置和可下载的标注结果图。'
        : (isSuperResolution
          ? '上传低清图片，返回超分辨率结果图并支持下载。'
          : '上传图片文件进行视觉模型推理，可按模型接口返回检测或识别结果。')
    }
  }

  if (['llama', 'gpt', 'bert', 'transformers', 'huggingface'].includes(type)) {
    return {
      kind: 'text',
      label: '文本模型',
      title: '文本预测',
      description: '输入文本和可选参数，发送到模型文本推理接口。'
    }
  }

  if (['sklearn'].includes(type)) {
    return {
      kind: 'json',
      label: '结构化数据模型',
      title: '结构化数据预测',
      description: '输入 JSON 结构化特征，发送到通用预测接口。'
    }
  }

  return {
    kind: 'json',
    label: type || '自定义模型',
    title: '通用预测',
    description: '输入符合模型服务约定的 JSON 请求体进行测试。'
  }
})

const normalizedImageResult = computed(() => {
  const data = predictResult.value?.data
  if (!data) return null
  const result = data.result || data
  return {
    success: result.success ?? data.success ?? true,
    count: result.count ?? result.plates?.length ?? 0,
    plates: result.plates || [],
    model_type: data.model_type || result.model_type,
    processed_image: result.processed_image || data.processed_image
  }
})

const displayResult = computed(() => {
  if (!predictResult.value?.data) return null
  if (modelProfile.value.kind !== 'image') return predictResult.value.data
  const data = JSON.parse(JSON.stringify(predictResult.value.data))
  const result = data.result || data
  if (result.processed_image) {
    result.processed_image = '[base64 image omitted]'
  }
  return data
})

watch(normalizedImageResult, (value) => {
  processedImageUrl.value = value?.processed_image ? `data:image/jpeg;base64,${value.processed_image}` : ''
})

const copyEndpoint = () => {
  navigator.clipboard.writeText(baseUrl.value)
  ElMessage.success('已复制到剪贴板')
}

const showApiDocs = () => {
  apiDocsVisible.value = true
}

const checkHealth = async () => {
  if (!deployment.value?.id) {
    ElMessage.warning('部署信息不可用')
    return
  }

  loading.value = true
  const startTime = Date.now()
  try {
    const response = await axios.get(`/api/v1/proxy/deployments/${deployment.value.id}/health`, {
      timeout: 10000
    })
    healthResult.value = {
      status: 'ok',
      data: response.data.data,
      responseTime: Date.now() - startTime
    }
    ElMessage.success('健康检查完成')
  } catch (error) {
    healthResult.value = {
      status: 'error',
      message: error.message,
      error: error.response?.data?.detail || '无法连接到服务',
      responseTime: Date.now() - startTime
    }
    ElMessage.error('健康检查失败')
  } finally {
    loading.value = false
  }
}

const handleFileChange = (file) => {
  selectedFile.value = file.raw
  if (imagePreviewUrl.value) URL.revokeObjectURL(imagePreviewUrl.value)
  imagePreviewUrl.value = URL.createObjectURL(file.raw)
}

const handleFileRemove = () => {
  selectedFile.value = null
  if (imagePreviewUrl.value) URL.revokeObjectURL(imagePreviewUrl.value)
  imagePreviewUrl.value = ''
}

const parseJson = (value, fallback = {}) => {
  try {
    return value.trim() ? JSON.parse(value) : fallback
  } catch (error) {
    throw new Error('JSON格式错误: ' + error.message)
  }
}

const sendPredict = async () => {
  if (!deployment.value?.id) {
    ElMessage.warning('部署信息不可用')
    return
  }

  loading.value = true
  const startTime = Date.now()

  try {
    let response

    if (modelProfile.value.kind === 'image') {
      if (!selectedFile.value) {
        ElMessage.warning('请选择要上传的图片')
        return
      }

      const formData = new FormData()
      formData.append('file', selectedFile.value)
      formData.append('conf', imageParams.value.conf)
      formData.append('iou', imageParams.value.iou)
      formData.append('return_image', imageParams.value.returnImage)

      response = await axios.post(`/api/v1/proxy/deployments/${deployment.value.id}/predict/image`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000
      })
    } else if (modelProfile.value.kind === 'text') {
      response = await axios.post(`/api/v1/proxy/deployments/${deployment.value.id}/predict`, {
        text: textInput.value,
        parameters: parseJson(parametersInput.value)
      }, {
        headers: { 'Content-Type': 'application/json' },
        timeout: 60000
      })
    } else {
      response = await axios.post(
        `/api/v1/proxy/deployments/${deployment.value.id}/predict`,
        parseJson(jsonInput.value),
        {
          headers: { 'Content-Type': 'application/json' },
          timeout: 60000
        }
      )
    }

    predictResult.value = {
      status: response.status,
      data: response.data,
      responseTime: Date.now() - startTime
    }
    ElMessage.success('预测请求成功')
  } catch (error) {
    predictResult.value = {
      status: error.response?.status || 0,
      data: error.response?.data || { error: error.message },
      responseTime: Date.now() - startTime
    }
    ElMessage.error('预测请求失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const clearResult = () => {
  predictResult.value = null
  healthResult.value = null
  processedImageUrl.value = ''
  if (uploadRef.value) uploadRef.value.clearFiles()
  handleFileRemove()
}

const downloadProcessedImage = () => {
  if (!processedImageUrl.value) return
  const link = document.createElement('a')
  link.href = processedImageUrl.value
  link.download = `${deployment.value?.name || 'prediction'}-result.jpg`
  link.click()
}

const formatResult = (data) => {
  if (typeof data === 'string') {
    try {
      return JSON.stringify(JSON.parse(data), null, 2)
    } catch {
      return data
    }
  }
  return JSON.stringify(data, null, 2)
}

const formatNumber = (value) => {
  if (typeof value !== 'number') return '-'
  return value.toFixed(4)
}

onMounted(async () => {
  const id = route.params.id
  try {
    deployment.value = await deploymentsStore.fetchDeploymentDetail(id)
    if (deployment.value?.model_id) {
      const response = await modelsApi.getDetail(deployment.value.model_id)
      model.value = response.data
    } else {
      model.value = {
        name: deployment.value?.image || deployment.value?.name || 'custom-image',
        model_type: 'custom',
        source_path: deployment.value?.image || '',
        config: {}
      }
    }
  } catch (error) {
    ElMessage.error('获取部署或模型详情失败')
  }
})
</script>

<style scoped>
.model-playground-page {
  padding: 2px 0 10px;
}

.section-label {
  flex: 0 0 auto;
  font-weight: 600;
}

.health-line {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  color: var(--ui-text-soft);
  font-size: 13px;
}

.image-workbench {
  display: grid;
  grid-template-columns: minmax(320px, 1fr) minmax(280px, 420px);
  gap: 20px;
  align-items: start;
}

.params-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.params-grid :deep(.el-form-item:last-child) {
  grid-column: 1 / -1;
}

.actions-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.preview-box {
  aspect-ratio: 4 / 3;
  border: 1px dashed rgba(68, 80, 86, 0.16);
  background: rgba(248, 249, 245, 0.94);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ui-text-faint);
  overflow: hidden;
}

.preview-box img,
.processed-preview img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.result-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--ui-text-soft);
  font-size: 13px;
  flex-wrap: wrap;
}

.summary-table,
.plates-table,
.processed-preview {
  margin-top: 4px;
}

.processed-preview {
  max-width: 900px;
}

.processed-preview h5 {
  margin: 0 0 10px;
  color: var(--ui-text-soft);
}

.processed-preview img {
  border: 1px solid var(--ui-border);
  border-radius: 18px;
  max-height: 520px;
  background: rgba(248, 249, 245, 0.92);
}

.api-docs {
  padding: 10px 0;
}

.api-docs h4 {
  margin: 20px 0 10px;
  color: var(--ui-text);
}

:deep(.el-upload-dragger) {
  width: 100%;
}

@media (max-width: 900px) {
  .image-workbench,
  .params-grid {
    grid-template-columns: 1fr;
  }

  .endpoint-row,
  .result-header {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
