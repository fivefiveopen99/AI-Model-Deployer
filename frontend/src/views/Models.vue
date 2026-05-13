<template>
  <div class="page-shell models-page">
    <PageHero
      eyebrow="模型资产"
      title="模型管理台"
      description="统一管理导入、上传、构建与重置状态。列表保留业务操作密度，但视觉和信息层级统一到新版控制台。"
    >
      <template #meta>
        <span class="badge-pill">总数 {{ modelsStore.total }}</span>
        <span class="badge-pill">就绪 {{ readyCount }}</span>
        <span class="badge-pill">构建中 {{ buildingCount }}</span>
      </template>
      <template #actions>
        <el-button @click="refreshModels">
          <el-icon><Refresh /></el-icon>
          刷新列表
        </el-button>
        <el-button type="primary" @click="showCreateDialog">
          <el-icon><Plus /></el-icon>
          添加模型
        </el-button>
      </template>
    </PageHero>

    <section class="metrics-grid">
      <MetricCard label="模型总数" :value="modelsStore.total" hint="当前登记到平台的全部模型资产" tone="brand">
        <template #icon>
          <el-icon :size="28"><Box /></el-icon>
        </template>
      </MetricCard>
      <MetricCard label="就绪" :value="readyCount" hint="构建完成且可直接创建部署" tone="success">
        <template #icon>
          <el-icon :size="28"><CircleCheck /></el-icon>
        </template>
      </MetricCard>
      <MetricCard label="构建中" :value="buildingCount" hint="包括 building 与 pushing 状态" tone="warning">
        <template #icon>
          <el-icon :size="28"><Loading /></el-icon>
        </template>
      </MetricCard>
      <MetricCard label="失败" :value="failedCount" hint="需要检查依赖、权重或构建日志" tone="danger">
        <template #icon>
          <el-icon :size="28"><Warning /></el-icon>
        </template>
      </MetricCard>
    </section>

    <PanelCard
      eyebrow="模型清单"
      title="模型列表"
      description="保留模型来源、镜像状态和快捷操作，并把构建相关动作统一收敛到列表上下文。"
    >
      <template #actions>
        <span class="badge-pill">第 {{ currentPage }} 页</span>
      </template>

      <el-table :data="modelsStore.models" v-loading="modelsStore.loading" stripe class="models-table">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="模型名称" />
        <el-table-column prop="model_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag>{{ row.model_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source_type" label="来源" width="120">
          <template #default="{ row }">
            <el-tag type="info">{{ row.source_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getModelStatusType(row.status)">
              {{ getModelStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="docker_image" label="Docker镜像">
          <template #default="{ row }">
            <span v-if="row.docker_image">
              {{ formatImageRef(row.docker_image, row.docker_image_tag) }}
            </span>
            <span v-else class="text-gray">未构建</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="350" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button size="small" @click="viewDetail(row)">详情</el-button>
              <el-button
                size="small"
                type="primary"
                @click="buildModel(row)"
                :disabled="row.status === 'building' || row.status === 'pushing'"
              >
                构建
              </el-button>
              <el-button
                v-if="row.status === 'building' || row.status === 'pushing'"
                size="small"
                type="warning"
                @click="resetModelStatus(row)"
              >
                重置
              </el-button>
              <el-button size="small" type="danger" @click="deleteModel(row)">删除</el-button>
            </el-button-group>
          </template>
        </el-table-column>
        <template #empty>
          <EmptyState
            title="模型列表为空"
            description="导入 GitHub 仓库、上传压缩包，或手动登记外部来源后，模型会出现在这里。"
          >
            <template #actions>
              <el-button type="primary" @click="showCreateDialog">添加模型</el-button>
            </template>
          </EmptyState>
        </template>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="modelsStore.total"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </PanelCard>

    <!-- 上传进度对话框 -->
    <el-dialog
      v-model="uploadProgressDialogVisible"
      title="上传进度"
      width="500px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="!uploading"
    >
      <div class="progress-content">
        <el-progress
          :percentage="uploadProgress"
          :status="uploadProgress === 100 ? 'success' : ''"
          :stroke-width="20"
          striped
          striped-flow
        />
        <div class="progress-message">
          <el-icon v-if="uploading" class="is-loading"><Loading /></el-icon>
          <span>{{ uploadProgressMessage }}</span>
        </div>
        <div v-if="uploadError" class="progress-error">
          <el-alert :title="uploadError" type="error" show-icon />
        </div>
      </div>
      <template #footer>
        <el-button @click="uploadProgressDialogVisible = false" :disabled="uploading">
          {{ uploading ? '上传中...' : '关闭' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 构建进度对话框 -->
    <el-dialog
      v-model="buildStore.progressDialogVisible"
      title="构建进度"
      width="760px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="!buildStore.building"
    >
      <div class="progress-content">
        <el-progress
          :percentage="buildStore.buildProgress"
          :status="buildStore.buildProgress === 100 ? 'success' : ''"
          :stroke-width="20"
          striped
          striped-flow
        />
        <div class="progress-message">
          <el-icon v-if="buildStore.building" class="is-loading"><Loading /></el-icon>
          <span>{{ buildStore.progressMessage }}</span>
        </div>
        <div v-if="buildStore.buildError" class="progress-error">
          <el-alert :title="buildStore.buildError" type="error" show-icon />
        </div>
        <div class="build-log-section">
          <div class="build-log-header">
            <span>构建日志</span>
            <el-button text size="small" @click="clearBuildLogs">清空</el-button>
          </div>
          <pre ref="buildLogRef" class="build-log-content">{{ buildStore.buildLogs.join('\n') || '等待构建日志...' }}</pre>
        </div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button v-if="buildStore.building" type="danger" @click="stopBuild">
            <el-icon><CircleClose /></el-icon> 停止构建
          </el-button>
          <el-button v-if="buildStore.building" type="primary" @click="minimizeProgress">
            <el-icon><ArrowDown /></el-icon> 最小化到后台
          </el-button>
          <el-button @click="closeProgressDialog" :disabled="buildStore.building">
            {{ buildStore.building ? '构建中...' : '关闭' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 最小化构建进度悬浮按钮 -->
    <div v-if="buildStore.isProgressMinimized && buildStore.building" class="floating-progress" @click="restoreProgress">
      <div class="floating-progress__content">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span class="floating-progress__text">构建中 {{ buildStore.buildProgress }}%</span>
        <el-progress
          :percentage="buildStore.buildProgress"
          :show-text="false"
          :stroke-width="4"
          class="minimized-bar"
        />
      </div>
    </div>

    <!-- 添加模型对话框 -->
    <el-dialog v-model="createDialogVisible" title="添加模型" width="700px">
      <el-tabs v-model="activeTab">
        <!-- GitHub URL -->
        <el-tab-pane label="GitHub 仓库" name="github">
          <el-form :model="githubForm" :rules="githubRules" ref="githubFormRef" label-width="100px">
            <el-form-item label="模型名称" prop="name">
              <el-input v-model="githubForm.name" placeholder="如：yolov8-plate" />
            </el-form-item>
            <el-form-item label="描述" prop="description">
              <el-input v-model="githubForm.description" type="textarea" placeholder="请输入模型描述" />
            </el-form-item>
            <el-form-item label="GitHub URL" prop="url">
              <el-input v-model="githubForm.url" placeholder="https://github.com/username/repo" />
              <div class="form-tip">支持 GitHub 仓库地址，系统会自动克隆代码</div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 上传压缩包 -->
        <el-tab-pane label="上传压缩包" name="upload">
          <el-form :model="uploadForm" :rules="uploadRules" ref="uploadFormRef" label-width="100px">
            <el-form-item label="模型名称" prop="name">
              <el-input v-model="uploadForm.name" placeholder="如：yolov8-custom" />
            </el-form-item>
            <el-form-item label="描述" prop="description">
              <el-input v-model="uploadForm.description" type="textarea" placeholder="请输入模型描述" />
            </el-form-item>
            <el-form-item label="压缩包" prop="file">
              <el-upload
                ref="uploadRef"
                action="#"
                :auto-upload="false"
                :on-change="handleFileChange"
                :before-upload="beforeUpload"
                :limit="1"
                accept=".zip,.tar.gz,.tgz,.tar"
              >
                <el-button type="primary">
                  <el-icon><Upload /></el-icon>
                  选择文件
                </el-button>
                <template #tip>
                  <div class="el-upload__tip">
                    支持 zip, tar.gz, tar 格式，包含模型代码和权重文件<br>
                    <el-tag type="warning">单个文件最大支持 10GB</el-tag>
                  </div>
                </template>
              </el-upload>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 其他来源 -->
        <el-tab-pane label="其他来源" name="other">
          <el-form :model="otherForm" :rules="otherRules" ref="otherFormRef" label-width="100px">
            <el-form-item label="模型名称" prop="name">
              <el-input v-model="otherForm.name" placeholder="请输入模型名称" />
            </el-form-item>
            <el-form-item label="描述" prop="description">
              <el-input v-model="otherForm.description" type="textarea" placeholder="请输入模型描述" />
            </el-form-item>
            <el-form-item label="来源类型" prop="source_type">
              <el-radio-group v-model="otherForm.source_type">
                <el-radio label="url">下载链接</el-radio>
                <el-radio label="huggingface">HuggingFace</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="路径/URL" prop="source_path">
              <el-input v-model="otherForm.source_path" placeholder="请输入下载链接或模型ID" />
            </el-form-item>
          </el-form>
        </el-tab-pane>

      </el-tabs>

      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreate" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 构建模型对话框 -->
    <el-dialog v-model="buildDialogVisible" title="构建Docker镜像" width="600px">
      <el-alert
        :title="isFinetuneModel(currentModel) ? '微调运行时构建说明' : '构建说明'"
        :description="isFinetuneModel(currentModel)
          ? '将直接使用你填写的 Dockerfile 构建镜像；如果上传了模型目录，也会一并进入构建上下文。构建完成后镜像会推送到内置 Registry。'
          : '系统将自动检测模型类型并安装所需依赖。构建完成后，镜像将推送到内置 Registry：10.10.25.69:5000/ai-models，并由 Kubernetes 节点按需拉取。'"
        type="info"
        show-icon
        :closable="false"
        style="margin-bottom: 20px"
      />
      <el-form :model="buildForm" label-width="120px">
        <el-form-item v-if="!isFinetuneModel(currentModel)" label="基础镜像">
          <el-select v-model="buildForm.base_image" style="width: 100%">
            <el-option label="Python 3.11 Slim" value="python:3.11-slim" />
            <el-option label="Python 3.10 Slim" value="python:3.10-slim" />
            <el-option label="PyTorch CUDA 11.8" value="pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="buildDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitBuild" :loading="buildStore.building">开始构建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Loading, ArrowDown, CircleClose, Box, CircleCheck, Warning } from '@element-plus/icons-vue'
import PageHero from '@/components/ui/PageHero.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import PanelCard from '@/components/ui/PanelCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { useModelsStore } from '@/stores/models'
import { useBuildStore } from '@/stores/build'
import { useWebSocket } from '@/composables/useWebSocket'
import { formatDate, formatImageRef, getModelStatusText, getModelStatusType } from '@/utils/formatters'

const router = useRouter()
const modelsStore = useModelsStore()
const buildStore = useBuildStore()
const { error, lastMessage, subscribe } = useWebSocket()

const currentPage = ref(1)
const pageSize = ref(10)
const createDialogVisible = ref(false)
const buildDialogVisible = ref(false)
const submitting = ref(false)
const uploading = ref(false)
const currentModel = ref(null)
const activeTab = ref('github')
const uploadRef = ref(null)
const selectedFile = ref(null)
const buildLogRef = ref(null)
const readyCount = computed(() => modelsStore.models.filter((row) => row.status === 'ready').length)
const buildingCount = computed(() => modelsStore.models.filter((row) => ['building', 'pushing'].includes(row.status)).length)
const failedCount = computed(() => modelsStore.models.filter((row) => row.status === 'failed').length)

// 上传进度条相关
const uploadProgress = ref(0)
const uploadProgressMessage = ref('')
const uploadError = ref('')
const uploadProgressDialogVisible = ref(false)

// GitHub 表单
const githubFormRef = ref(null)
const githubForm = reactive({
  name: '',
  description: '',
  url: ''
})
const githubRules = {
  name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  url: [{ required: true, message: '请输入 GitHub URL', trigger: 'blur' }]
}

// 上传表单
const uploadFormRef = ref(null)
const uploadForm = reactive({
  name: '',
  description: ''
})
const uploadRules = {
  name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }]
}

// 其他来源表单
const otherFormRef = ref(null)
const otherForm = reactive({
  name: '',
  description: '',
  source_type: 'url',
  source_path: ''
})
const otherRules = {
  name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  source_type: [{ required: true, message: '请选择来源类型', trigger: 'change' }],
  source_path: [{ required: true, message: '请输入路径', trigger: 'blur' }]
}

const buildForm = reactive({
  model_type: 'custom',
  base_image: 'python:3.11-slim'
})

const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

const beforeUpload = (file) => {
  const maxSize = 10 * 1024 * 1024 * 1024 // 10GB
  if (file.size > maxSize) {
    ElMessage.error('文件大小超过 10GB 限制')
    return false
  }
  return true
}

const isFinetuneModel = (model) => {
  return Boolean(model?.config?.workflow_type === 'finetune' || model?.config?.runtime_spec?.dockerfile_content)
}

const showCreateDialog = () => {
  githubForm.name = ''
  githubForm.description = ''
  githubForm.url = ''

  uploadForm.name = ''
  uploadForm.description = ''
  selectedFile.value = null
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }

  otherForm.name = ''
  otherForm.description = ''
  otherForm.source_type = 'url'
  otherForm.source_path = ''

  activeTab.value = 'github'
  createDialogVisible.value = true
}

const submitCreate = async () => {
  submitting.value = true

  try {
    if (activeTab.value === 'github') {
      await githubFormRef.value.validate(async (valid) => {
        if (!valid) {
          submitting.value = false
          return
        }

        uploading.value = true
        uploadProgress.value = 0
        uploadProgressMessage.value = '正在从 GitHub 克隆代码...'
        uploadError.value = ''
        uploadProgressDialogVisible.value = true
        createDialogVisible.value = false

        const formData = new FormData()
        formData.append('name', githubForm.name)
        formData.append('description', githubForm.description || '')
        formData.append('model_type', 'custom')
        formData.append('url', githubForm.url)

        const onProgress = (progressEvent) => {
          if (progressEvent.total) {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            uploadProgress.value = percent
            uploadProgressMessage.value = `正在从 GitHub 克隆代码... ${percent}%`
          }
        }

        await modelsStore.createModelFromUrl(formData, onProgress)
        uploading.value = false
        uploadProgress.value = 100
        uploadProgressMessage.value = 'GitHub 代码克隆完成！'
        ElMessage.success('模型添加成功')
        refreshModels()
      })

    } else if (activeTab.value === 'upload') {
      await uploadFormRef.value.validate(async (valid) => {
        if (!valid) {
          submitting.value = false
          return
        }

        if (!selectedFile.value) {
          ElMessage.error('请选择压缩包文件')
          submitting.value = false
          return
        }

        uploading.value = true
        uploadProgress.value = 0
        uploadProgressMessage.value = '准备上传...'
        uploadError.value = ''
        uploadProgressDialogVisible.value = true
        createDialogVisible.value = false

        const formData = new FormData()
        formData.append('name', uploadForm.name)
        formData.append('description', uploadForm.description || '')
        formData.append('model_type', 'custom')
        formData.append('file', selectedFile.value)

        const onProgress = (progressEvent) => {
          if (progressEvent.total) {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            uploadProgress.value = percent
            const loadedMB = (progressEvent.loaded / 1024 / 1024).toFixed(2)
            const totalMB = (progressEvent.total / 1024 / 1024).toFixed(2)
            uploadProgressMessage.value = `正在上传... ${percent}% (${loadedMB}MB / ${totalMB}MB)`
          }
        }

        await modelsStore.uploadModel(formData, onProgress)
        uploading.value = false
        uploadProgress.value = 100
        uploadProgressMessage.value = '上传完成！'
        ElMessage.success('模型上传成功')
        refreshModels()
      })

    } else if (activeTab.value === 'other') {
      await otherFormRef.value.validate(async (valid) => {
        if (!valid) {
          submitting.value = false
          return
        }

        uploading.value = true
        uploadProgress.value = 0
        uploadProgressMessage.value = '正在添加模型...'
        uploadError.value = ''
        uploadProgressDialogVisible.value = true
        createDialogVisible.value = false

        if (otherForm.source_type === 'url') {
          const formData = new FormData()
          formData.append('name', otherForm.name)
          formData.append('description', otherForm.description || '')
          formData.append('model_type', 'custom')
          formData.append('url', otherForm.source_path)

          const onProgress = (progressEvent) => {
            if (progressEvent.total) {
              const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
              uploadProgress.value = percent
              uploadProgressMessage.value = `正在下载... ${percent}%`
            }
          }

          await modelsStore.createModelFromUrl(formData, onProgress)
        } else {
          await modelsStore.createModel({
            name: otherForm.name,
            description: otherForm.description,
            model_type: 'custom',
            source_type: otherForm.source_type,
            source_path: otherForm.source_path
          })
        }
        uploading.value = false
        uploadProgress.value = 100
        uploadProgressMessage.value = '添加完成！'
        ElMessage.success('模型添加成功')
        refreshModels()
      })
    }

  } catch (error) {
    uploading.value = false
    uploadError.value = error.message || '添加失败'
    let errorMsg = '添加失败'
    if (error.response) {
      if (error.response.status === 413) {
        errorMsg = '文件太大，超过服务器限制（最大支持 10GB）。建议：\n1. 使用 GitHub 仓库方式\n2. 压缩模型文件\n3. 手动上传到服务器'
      } else {
        errorMsg = error.response.data?.detail || error.message
      }
    } else {
      errorMsg = error.message
    }
    ElMessage.error(errorMsg)
  } finally {
    submitting.value = false
  }
}

const buildModel = (row) => {
  currentModel.value = row
  buildForm.base_image = 'python:3.11-slim'
  buildDialogVisible.value = true
}

// 最小化进度对话框
const minimizeProgress = () => {
  buildStore.minimizeProgress()
  ElMessage.info('构建任务已在后台运行，点击悬浮窗可查看进度')
}

// 恢复进度对话框
const restoreProgress = () => {
  buildStore.restoreProgress()
}

// 关闭进度对话框
const closeProgressDialog = () => {
  buildStore.closeProgress()
}

const clearBuildLogs = () => {
  buildStore.setLogs([])
}

// 停止构建
const stopBuild = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要停止当前构建任务吗？',
      '确认停止',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await modelsStore.stopBuild(buildStore.currentModelId)
    buildStore.stopBuild()
    ElMessage.info('构建已停止')
    refreshModels()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('停止构建失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

const submitBuild = async () => {
  if (!currentModel.value) return

  buildStore.startBuild('', currentModel.value.id)
  buildDialogVisible.value = false

  try {
    const result = await modelsStore.buildModel(currentModel.value.id, buildForm)

    if (result.task_id) {
      buildStore.setTask(result.task_id, currentModel.value.id)
      subscribe(result.task_id)
    }
  } catch (error) {
    buildStore.setError(error.message || '构建失败')
    let errorMsg = '构建失败'
    if (error.response) {
      errorMsg = error.response.data?.detail || error.message
    } else if (error.message) {
      errorMsg = error.message
    }
    ElMessage.error(errorMsg)
  }
}

const resetModelStatus = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要重置模型 "${row.name}" 的状态吗？这将允许您重新构建。`,
      '确认重置状态',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await modelsStore.resetStatus(row.id)
    ElMessage.success('状态已重置，可以重新构建')
    refreshModels()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('重置状态失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

const deleteModel = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除模型 "${row.name}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await modelsStore.deleteModel(row.id)
    ElMessage.success('删除成功')
    refreshModels()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

const viewDetail = (row) => {
  router.push(`/models/${row.id}`)
}

const refreshModels = () => {
  return modelsStore.fetchModels({
    skip: (currentPage.value - 1) * pageSize.value,
    limit: pageSize.value
  })
}

const handleSizeChange = (val) => {
  pageSize.value = val
  refreshModels()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  refreshModels()
}

const restoreBuildProgress = async () => {
  const persisted = buildStore.restorePersistedState()
  await refreshModels()

  const activeModels = await modelsStore.fetchActiveBuildModels()
  const activeModel = activeModels[0]
  if (activeModel) {
    const taskId = `build-${activeModel.id}`
    if (!persisted || !buildStore.currentTaskId) {
      buildStore.resumeBuild({
        taskId,
        modelId: activeModel.id,
        progress: buildStore.buildProgress,
        message: activeModel.status_message || '构建任务恢复中...',
        minimized: true
      })
    }
    subscribe(buildStore.currentTaskId || taskId)
    return
  }

  if (buildStore.building) {
    buildStore.building = false
    buildStore.isProgressMinimized = false
    buildStore.progressDialogVisible = true
    buildStore.progressMessage = buildStore.progressMessage || '构建任务已结束'
  }
}

// 监听 WebSocket 消息，包含进度、日志和刷新后的日志回放
const unwatchMessage = watch(() => lastMessage.value, (message) => {
  if (!message) return

  if (message.type === 'log_history') {
    buildStore.setLogs(message.logs || [])
    return
  }

  if (message.type !== 'progress') return

  buildStore.updateProgress(message.progress, message.data?.log ? null : message.message)
  if (message.data?.log) {
    buildStore.addLog(message.data.log)
  }

  if (message.data?.error) {
    buildStore.setError(message.message)
    ElMessage.error('构建失败: ' + message.message)
    refreshModels()
    return
  }

  if (message.progress === 100) {
    buildStore.completeBuild()
    ElMessage.success('构建成功！')
    refreshModels()
  }
})

// 监听 WebSocket 错误
const unwatchError = watch(() => error.value, (newError) => {
  if (newError) {
    buildStore.setError(newError)
    ElMessage.error('构建失败: ' + newError)
  }
})

watch(() => buildStore.buildLogs.length, () => {
  setTimeout(() => {
    if (buildLogRef.value) {
      buildLogRef.value.scrollTop = buildLogRef.value.scrollHeight
    }
  }, 0)
})

onMounted(() => {
  restoreBuildProgress()
})

onUnmounted(() => {
  unwatchMessage()
  unwatchError()
})
</script>

<style scoped>
.models-page {
  padding: 2px 0 10px;
}

.models-table {
  width: 100%;
}

.pagination {
  margin-top: 18px;
  display: flex;
  justify-content: flex-end;
}

.text-gray {
  color: var(--ui-text-faint);
}

.form-tip {
  margin-top: 6px;
}

.build-log-section {
  margin-top: 4px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.build-log-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 42px;
  padding: 0 14px;
  font-size: 12px;
  color: var(--ui-text-soft);
  border: 1px solid rgba(29, 44, 53, 0.08);
  border-bottom: 0;
  border-radius: 18px 18px 0 0;
  background: rgba(249, 250, 246, 0.96);
}

.build-log-content {
  height: 280px;
  margin: 0;
  padding: 16px;
  overflow: auto;
  color: #d7dde8;
  background: #172028;
  font-family: var(--ui-font-mono);
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid rgba(29, 44, 53, 0.08);
  border-top: 0;
  border-radius: 0 0 18px 18px;
}

.minimized-bar :deep(.el-progress-bar__inner) {
  background-color: #fff !important;
}
</style>
