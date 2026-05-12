<template>
  <div class="page-shell registry-images-page">
    <PageHero
      eyebrow="Registry Workspace"
      title="镜像仓库管理"
      description="统一查看私有 Registry 中的仓库、标签和导入入口，同时保留手动构建与本地镜像上传流程。"
    >
      <template #meta>
        <span class="badge-pill">Registry {{ registryUrl || '未配置' }}</span>
        <span v-if="namespacePrefix" class="badge-pill">Namespace {{ namespacePrefix }}</span>
      </template>
      <template #actions>
        <el-button type="primary" @click="openImageUploadDialog">
          <el-icon><Upload /></el-icon>
          镜像上传
        </el-button>
        <el-button @click="fetchImages" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </template>
    </PageHero>

    <section class="metrics-grid">
      <MetricCard label="Repositories" :value="totalRepositories" hint="已发现的 Registry 仓库数量" tone="brand">
        <template #icon>
          <el-icon :size="28"><Collection /></el-icon>
        </template>
      </MetricCard>
      <MetricCard label="Tags" :value="totalTags" hint="全部仓库下的标签总数" tone="success">
        <template #icon>
          <el-icon :size="28"><PriceTag /></el-icon>
        </template>
      </MetricCard>
      <MetricCard label="Entries" :value="flatImages.length" hint="展开后的仓库标签条目数" tone="warning">
        <template #icon>
          <el-icon :size="28"><Files /></el-icon>
        </template>
      </MetricCard>
      <MetricCard label="Import Modes" value="3" hint="手动构建、压缩包上传、本地目录上传" tone="default">
        <template #icon>
          <el-icon :size="28"><Upload /></el-icon>
        </template>
      </MetricCard>
    </section>

    <PanelCard
      eyebrow="Registry Inventory"
      title="镜像列表"
      description="镜像浏览、删除与导入都在同一个面板里完成，避免在工具页之间跳转。"
    >
      <template #actions>
        <span class="badge-pill">{{ flatImages.length }} 条镜像</span>
      </template>

      <el-alert
        v-if="error"
        :title="error"
        type="error"
        show-icon
        :closable="false"
        class="mb-16"
      />

      <el-table :data="flatImages" v-loading="loading" stripe>
        <el-table-column prop="repository" label="Repository" min-width="260" />
        <el-table-column prop="tag" label="Tag" width="180">
          <template #default="{ row }">
            <el-tag size="small">{{ row.tag }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="image_ref" label="完整镜像名" min-width="420">
          <template #default="{ row }">
            <span class="ref-item">{{ row.image_ref }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              type="danger"
              :loading="deletingImageRef === row.image_ref"
              @click="deleteImage(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <EmptyState
            title="私有仓库为空"
            description="先从 Dockerfile 手动构建，或导入已有镜像 tar 包，后续就可以直接从这里部署。"
          >
            <template #actions>
              <el-button type="primary" @click="openImageUploadDialog">导入镜像</el-button>
            </template>
          </EmptyState>
        </template>
      </el-table>
    </PanelCard>

    <el-dialog v-model="imageUploadDialogVisible" title="镜像上传" width="760px">
      <el-tabs v-model="activeUploadTab" @tab-change="handleUploadTabChange">
        <el-tab-pane label="手动构建" name="build">
          <el-form
            ref="buildImageFormRef"
            :model="buildImageForm"
            :rules="buildImageRules"
            label-width="100px"
          >
            <el-form-item label="Dockerfile" prop="dockerfile_content">
              <el-input
                v-model="buildImageForm.dockerfile_content"
                type="textarea"
                :rows="14"
                placeholder="直接填写用于构建镜像的 Dockerfile"
              />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="压缩包上传" name="package">
          <el-form
            ref="uploadFormRef"
            :model="uploadForm"
            :rules="uploadRules"
            label-width="120px"
          >
            <el-form-item label="Repository" prop="repository">
              <el-input v-model="uploadForm.repository" placeholder="如：ai-model/my-runtime" />
            </el-form-item>
            <el-form-item label="Tag" prop="tag">
              <el-input v-model="uploadForm.tag" placeholder="如：v1 或 20260511" />
            </el-form-item>
            <el-form-item label="镜像文件" prop="file">
              <el-upload
                ref="uploadRef"
                action="#"
                :auto-upload="false"
                :limit="1"
                :on-change="handleUploadFileChange"
                accept=".tar"
              >
                <el-button type="primary">选择镜像 tar 文件</el-button>
                <template #tip>
                  <div class="el-upload__tip">
                    支持 `docker save` 导出的 `.tar` 镜像包，上传后将自动 `docker load` 并推送到私有仓库。
                  </div>
                </template>
              </el-upload>
            </el-form-item>
          </el-form>

          <el-progress
            v-if="uploading"
            :percentage="uploadProgress"
            :stroke-width="18"
            striped
            striped-flow
            class="upload-progress"
          />
        </el-tab-pane>

        <el-tab-pane label="本地上传" name="local">
          <el-form
            ref="localUploadFormRef"
            :model="localUploadForm"
            :rules="localUploadRules"
            label-width="120px"
          >
            <el-form-item label="Repository" prop="repository">
              <el-input v-model="localUploadForm.repository" placeholder="如：ai-model/my-runtime" />
            </el-form-item>
            <el-form-item label="Tag" prop="tag">
              <el-input v-model="localUploadForm.tag" placeholder="如：v1 或 20260511" />
            </el-form-item>
            <el-form-item label="镜像包" prop="package_path">
              <el-input v-model="localUploadForm.package_path" readonly placeholder="请选择宿主机目录中的镜像包" />
            </el-form-item>
          </el-form>

          <el-alert
            :title="`浏览目录：${localPackageRoot || '加载中...'}`"
            type="info"
            :closable="false"
            show-icon
            class="mb-16"
          />

          <div class="browser-toolbar">
            <div class="browser-path">
              <span>当前目录：</span>
              <code>{{ localPackageCurrentPath || '/' }}</code>
            </div>
            <div class="browser-actions">
              <el-button
                size="small"
                :disabled="localPackagesLoading || localPackageParentPath === null"
                @click="openLocalDirectory(localPackageParentPath || '')"
              >
                返回上级
              </el-button>
              <el-button size="small" :loading="localPackagesLoading" @click="fetchLocalPackages(localPackageCurrentPath)">
                刷新目录
              </el-button>
            </div>
          </div>

          <div v-if="localDirectories.length" class="browser-section">
            <div class="browser-section-title">目录</div>
            <div class="directory-list">
              <el-button
                v-for="directory in localDirectories"
                :key="directory.path"
                text
                class="directory-button"
                @click="openLocalDirectory(directory.path)"
              >
                {{ directory.name }}
              </el-button>
            </div>
          </div>

          <div class="browser-section">
            <div class="browser-section-title">镜像包</div>
            <el-table :data="localFiles" size="small" v-loading="localPackagesLoading" empty-text="当前目录没有 .tar 镜像包">
              <el-table-column prop="name" label="文件名" min-width="260" />
              <el-table-column label="大小" width="120">
                <template #default="{ row }">
                  {{ formatBytes(row.size) }}
                </template>
              </el-table-column>
              <el-table-column label="修改时间" width="190">
                <template #default="{ row }">
                  {{ formatLocalDate(row.modified_at) }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120">
                <template #default="{ row }">
                  <el-button
                    size="small"
                    :type="localUploadForm.package_path === row.path ? 'success' : 'primary'"
                    plain
                    @click="selectLocalPackage(row.path)"
                  >
                    {{ localUploadForm.package_path === row.path ? '已选择' : '选择' }}
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <el-progress
            v-if="localUploading"
            :percentage="localUploadProgress"
            :stroke-width="18"
            striped
            striped-flow
            class="upload-progress"
          />
          <div v-if="localUploading" class="build-hint">{{ localUploadMessage }}</div>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="closeImageUploadDialog" :disabled="dialogBusy">取消</el-button>
        <el-button type="primary" @click="submitActiveUpload" :loading="dialogBusy">
          {{ activeUploadActionText }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="registryBuildStore.progressDialogVisible"
      title="手动构建进度"
      width="760px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="!registryBuildStore.building"
    >
      <div class="progress-content">
        <el-progress
          :percentage="registryBuildStore.buildProgress"
          :status="registryBuildStore.buildProgress === 100 ? 'success' : ''"
          :stroke-width="20"
          striped
          striped-flow
        />
        <div class="progress-message">
          <el-icon v-if="registryBuildStore.building" class="is-loading"><Refresh /></el-icon>
          <span>{{ registryBuildStore.progressMessage }}</span>
        </div>
        <div v-if="registryBuildStore.buildError" class="progress-error">
          <el-alert :title="registryBuildStore.buildError" type="error" show-icon />
        </div>
        <div v-if="registryBuildStore.resultImage" class="progress-result">
          <el-alert :title="`已推送镜像：${registryBuildStore.resultImage}`" type="success" show-icon :closable="false" />
        </div>
        <div class="build-log-section">
          <div class="build-log-header">
            <span>构建日志</span>
            <el-button text size="small" @click="clearBuildLogs">清空</el-button>
          </div>
          <pre ref="buildLogRef" class="build-log-content">{{ registryBuildStore.buildLogs.join('\n') || '等待构建日志...' }}</pre>
        </div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button v-if="registryBuildStore.building" type="danger" @click="stopRegistryBuild">
            <el-icon><CircleClose /></el-icon>
            停止构建
          </el-button>
          <el-button v-if="registryBuildStore.building" type="primary" @click="minimizeBuildProgress">
            最小化到后台
          </el-button>
          <el-button @click="closeBuildProgressDialog" :disabled="registryBuildStore.building">
            {{ registryBuildStore.building ? '构建中...' : '关闭' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <div
      v-if="registryBuildStore.isProgressMinimized && registryBuildStore.building"
      class="floating-progress"
      @click="restoreBuildProgress"
    >
      <div class="floating-progress__content">
        <el-icon class="is-loading"><Refresh /></el-icon>
        <span class="floating-progress__text">构建中 {{ registryBuildStore.buildProgress }}%</span>
        <el-progress
          :percentage="registryBuildStore.buildProgress"
          :show-text="false"
          :stroke-width="4"
          class="minimized-bar"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleClose, Refresh, Upload } from '@element-plus/icons-vue'
import PageHero from '@/components/ui/PageHero.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import PanelCard from '@/components/ui/PanelCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { systemApi } from '@/api'
import { useWebSocket } from '@/composables/useWebSocket'
import { useRegistryBuildStore } from '@/stores/registryBuild'

const registryBuildStore = useRegistryBuildStore()
const { error: wsError, lastMessage, subscribe } = useWebSocket()
const loading = ref(false)
const images = ref([])
const registryUrl = ref('')
const namespacePrefix = ref('')
const totalRepositories = ref(0)
const totalTags = ref(0)
const error = ref('')
const deletingImageRef = ref('')

const imageUploadDialogVisible = ref(false)
const activeUploadTab = ref('build')

const uploadFormRef = ref(null)
const localUploadFormRef = ref(null)
const buildImageFormRef = ref(null)
const uploadRef = ref(null)
const buildLogRef = ref(null)

const selectedFile = ref(null)
const uploading = ref(false)
const uploadProgress = ref(0)

const localUploading = ref(false)
const localUploadProgress = ref(0)
const localUploadMessage = ref('')
const localPackagesLoading = ref(false)
const localPackageRoot = ref('')
const localPackageCurrentPath = ref('')
const localPackageParentPath = ref(null)
const localDirectories = ref([])
const localFiles = ref([])

const uploadForm = reactive({
  repository: '',
  tag: '',
  file: null
})

const localUploadForm = reactive({
  repository: '',
  tag: '',
  package_path: ''
})

const buildImageForm = reactive({
  dockerfile_content: ''
})

const uploadRules = {
  repository: [{ required: true, message: '请输入 Repository', trigger: 'blur' }],
  tag: [{ required: true, message: '请输入 Tag', trigger: 'blur' }],
  file: [{ required: true, message: '请选择镜像文件', trigger: 'change' }]
}

const localUploadRules = {
  repository: [{ required: true, message: '请输入 Repository', trigger: 'blur' }],
  tag: [{ required: true, message: '请输入 Tag', trigger: 'blur' }],
  package_path: [{ required: true, message: '请选择本地镜像包', trigger: 'change' }]
}

const buildImageRules = {
  dockerfile_content: [{ required: true, message: '请填写 Dockerfile', trigger: 'blur' }]
}

const flatImages = computed(() => {
  return images.value.flatMap((item) => {
    if (!item.tags?.length) {
      return []
    }
    return item.tags.map((tag) => ({
      repository: item.repository,
      tag,
      image_ref: `${item.repository}:${tag}`
    }))
  })
})

const dialogBusy = computed(() => uploading.value || registryBuildStore.building || localUploading.value)

const activeUploadActionText = computed(() => {
  if (activeUploadTab.value === 'build') {
    return '开始构建'
  }
  if (activeUploadTab.value === 'local') {
    return '开始上传'
  }
  return '开始上传'
})

const formatBytes = (size) => {
  if (!size) {
    return '0 B'
  }
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = size
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`
}

const formatLocalDate = (value) => {
  if (!value) {
    return '-'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

const resetUploadForm = () => {
  uploadForm.repository = ''
  uploadForm.tag = ''
  uploadForm.file = null
  selectedFile.value = null
  uploadProgress.value = 0
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

const resetLocalUploadForm = () => {
  localUploadForm.repository = ''
  localUploadForm.tag = ''
  localUploadForm.package_path = ''
  localUploadProgress.value = 0
  localUploadMessage.value = ''
}

const resetBuildImageForm = () => {
  buildImageForm.dockerfile_content = ''
}

const resetImageUploadDialog = () => {
  activeUploadTab.value = 'build'
  resetUploadForm()
  resetLocalUploadForm()
  resetBuildImageForm()
  localPackageCurrentPath.value = ''
  localPackageParentPath.value = null
  localDirectories.value = []
  localFiles.value = []
}

const fetchImages = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await systemApi.getRegistryImages()
    images.value = response.data.items || []
    registryUrl.value = response.data.registry_url || ''
    namespacePrefix.value = response.data.namespace_prefix || ''
    totalRepositories.value = response.data.total_repositories || 0
    totalTags.value = response.data.total_tags || 0
    error.value = response.data.error || ''

    if (response.data.error) {
      ElMessage.error('读取私有仓库镜像失败')
    }
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || '读取私有仓库镜像失败'
    ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

const fetchLocalPackages = async (path = '') => {
  localPackagesLoading.value = true
  try {
    const response = await systemApi.getLocalRegistryImagePackages(path)
    localPackageRoot.value = response.data.root_path || ''
    localPackageCurrentPath.value = response.data.current_path || ''
    localPackageParentPath.value = response.data.parent_path ?? null
    localDirectories.value = response.data.directories || []
    localFiles.value = response.data.files || []
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || err.message || '读取本地镜像包目录失败')
  } finally {
    localPackagesLoading.value = false
  }
}

const openLocalDirectory = async (path = '') => {
  await fetchLocalPackages(path)
}

const selectLocalPackage = (path) => {
  localUploadForm.package_path = path
}

const handleUploadFileChange = (file) => {
  selectedFile.value = file.raw
  uploadForm.file = file.raw
}

const openImageUploadDialog = async () => {
  resetImageUploadDialog()
  imageUploadDialogVisible.value = true
  await fetchLocalPackages('')
}

const closeImageUploadDialog = () => {
  if (dialogBusy.value) {
    return
  }
  imageUploadDialogVisible.value = false
  resetImageUploadDialog()
}

const handleUploadTabChange = async (tabName) => {
  if (tabName === 'local' && !localPackageRoot.value) {
    await fetchLocalPackages('')
  }
}

const submitPackageUpload = async () => {
  if (!uploadFormRef.value) {
    return
  }

  await uploadFormRef.value.validate(async (valid) => {
    if (!valid) {
      return
    }

    if (!selectedFile.value) {
      ElMessage.error('请选择镜像 tar 文件')
      return
    }

    uploading.value = true
    uploadProgress.value = 0

    try {
      const formData = new FormData()
      formData.append('repository', uploadForm.repository)
      formData.append('tag', uploadForm.tag)
      formData.append('file', selectedFile.value)

      await systemApi.uploadRegistryImage(formData, (progressEvent) => {
        if (progressEvent.total) {
          uploadProgress.value = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        }
      })

      ElMessage.success('镜像已上传到私有仓库')
      imageUploadDialogVisible.value = false
      resetImageUploadDialog()
      await fetchImages()
    } catch (err) {
      ElMessage.error(err.response?.data?.detail || err.message || '上传镜像失败')
    } finally {
      uploading.value = false
    }
  })
}

const submitBuildImage = async () => {
  if (!buildImageFormRef.value) {
    return
  }

  await buildImageFormRef.value.validate(async (valid) => {
    if (!valid) {
      return
    }

    registryBuildStore.startBuild()

    try {
      const formData = new FormData()
      formData.append('dockerfile_content', buildImageForm.dockerfile_content)

      const result = await systemApi.buildRegistryImage(formData)
      if (result.data?.task_id) {
        registryBuildStore.setTask(result.data.task_id)
        subscribe(result.data.task_id)
      }

      imageUploadDialogVisible.value = false
      registryBuildStore.updateProgress(0, '镜像构建任务已启动')
      resetImageUploadDialog()
    } catch (err) {
      const message = err.response?.data?.detail || err.message || '启动镜像构建失败'
      registryBuildStore.setError(message)
      ElMessage.error(message)
    }
  })
}

const submitLocalUpload = async () => {
  if (!localUploadFormRef.value) {
    return
  }

  await localUploadFormRef.value.validate(async (valid) => {
    if (!valid) {
      return
    }

    localUploading.value = true
    localUploadProgress.value = 15
    localUploadMessage.value = '正在读取宿主机镜像包...'

    try {
      const formData = new FormData()
      formData.append('repository', localUploadForm.repository)
      formData.append('tag', localUploadForm.tag)
      formData.append('package_path', localUploadForm.package_path)

      localUploadProgress.value = 45
      localUploadMessage.value = '正在导入并推送到私有仓库...'

      await systemApi.uploadLocalRegistryImage(formData)

      localUploadProgress.value = 100
      localUploadMessage.value = '镜像上传完成'
      ElMessage.success('本地镜像包已上传到私有仓库')
      imageUploadDialogVisible.value = false
      resetImageUploadDialog()
      await fetchImages()
    } catch (err) {
      ElMessage.error(err.response?.data?.detail || err.message || '本地镜像包上传失败')
    } finally {
      localUploading.value = false
    }
  })
}

const submitActiveUpload = async () => {
  if (activeUploadTab.value === 'build') {
    await submitBuildImage()
    return
  }
  if (activeUploadTab.value === 'local') {
    await submitLocalUpload()
    return
  }
  await submitPackageUpload()
}

const minimizeBuildProgress = () => {
  registryBuildStore.minimizeProgress()
  ElMessage.info('构建任务已在后台运行，点击悬浮窗可查看进度')
}

const restoreBuildProgress = () => {
  registryBuildStore.restoreProgress()
}

const closeBuildProgressDialog = () => {
  registryBuildStore.closeProgress()
}

const clearBuildLogs = () => {
  registryBuildStore.setLogs([])
}

const stopRegistryBuild = async () => {
  if (!registryBuildStore.currentTaskId) {
    return
  }

  try {
    await ElMessageBox.confirm(
      '确定要停止当前镜像构建任务吗？',
      '确认停止',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await systemApi.stopRegistryBuild(registryBuildStore.currentTaskId)
    registryBuildStore.stopBuild()
    ElMessage.info('构建已停止')
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('停止构建失败: ' + (err.response?.data?.detail || err.message))
    }
  }
}

const deleteImage = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定删除镜像 ${row.image_ref} 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    deletingImageRef.value = row.image_ref
    await systemApi.deleteRegistryImage(row.repository, row.tag)
    ElMessage.success('镜像删除成功')
    await fetchImages()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err.response?.data?.detail || err.message || '删除镜像失败')
    }
  } finally {
    deletingImageRef.value = ''
  }
}

onMounted(() => {
  fetchImages()
  const persisted = registryBuildStore.restorePersistedState()
  if (persisted?.building && registryBuildStore.currentTaskId) {
    registryBuildStore.resumeBuild({
      taskId: registryBuildStore.currentTaskId,
      progress: registryBuildStore.buildProgress,
      message: registryBuildStore.progressMessage || '构建任务恢复中...',
      minimized: true
    })
    subscribe(registryBuildStore.currentTaskId)
  }
})

const unwatchMessage = watch(() => lastMessage.value, async (message) => {
  if (!message) return

  if (message.type === 'log_history') {
    registryBuildStore.setLogs(message.logs || [])
    return
  }

  if (message.type !== 'progress' || message.task_id !== registryBuildStore.currentTaskId) {
    return
  }

  registryBuildStore.updateProgress(message.progress, message.data?.log ? null : message.message)
  if (message.data?.log) {
    registryBuildStore.addLog(message.data.log)
  }

  if (message.data?.error) {
    registryBuildStore.setError(message.message)
    if (message.data?.cancelled) {
      ElMessage.info(message.message)
    } else {
      ElMessage.error(message.message)
    }
    return
  }

  if (message.progress === 100) {
    registryBuildStore.completeBuild(message.data?.registry_image || '')
    ElMessage.success(message.data?.registry_image ? `镜像构建成功：${message.data.registry_image}` : '镜像构建成功')
    await fetchImages()
  }
})

const unwatchWsError = watch(() => wsError.value, (message) => {
  if (!message || !registryBuildStore.building) {
    return
  }
  registryBuildStore.setError(message)
  ElMessage.error(`构建失败: ${message}`)
})

watch(() => registryBuildStore.buildLogs.length, () => {
  setTimeout(() => {
    if (buildLogRef.value) {
      buildLogRef.value.scrollTop = buildLogRef.value.scrollHeight
    }
  }, 0)
})

onUnmounted(() => {
  unwatchMessage()
  unwatchWsError()
})
</script>

<style scoped>
.registry-images-page {
  padding: 0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.subtitle {
  margin-top: 6px;
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #909399;
  flex-wrap: wrap;
}

.summary-row {
  margin-bottom: 16px;
}

.summary-card {
  text-align: center;
  border: 1px solid #ebeef5;
}

.summary-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}

.summary-label {
  margin-top: 8px;
  font-size: 13px;
  color: #909399;
}

.ref-item {
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 12px;
  color: #606266;
  word-break: break-all;
}

.upload-progress {
  margin-top: 12px;
}

.build-hint {
  margin-top: 10px;
  font-size: 13px;
  color: #606266;
}

.progress-content {
  padding: 20px 0;
}

.progress-message {
  margin-top: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #606266;
}

.progress-error,
.progress-result {
  margin-top: 16px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.build-log-section {
  margin-top: 20px;
}

.build-log-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  color: #606266;
  font-size: 13px;
}

.build-log-content {
  margin: 0;
  padding: 12px;
  min-height: 220px;
  max-height: 360px;
  overflow: auto;
  background: #111827;
  color: #e5e7eb;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: Consolas, Monaco, 'Courier New', monospace;
}

.browser-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.browser-path {
  font-size: 13px;
  color: #606266;
  word-break: break-all;
}

.browser-actions {
  display: flex;
  gap: 8px;
}

.browser-section {
  margin-bottom: 16px;
}

.browser-section-title {
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #606266;
}

.directory-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.directory-button {
  padding: 0;
}

.minimized-progress {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: 240px;
  padding: 14px 16px;
  border-radius: 16px;
  background: linear-gradient(135deg, #409eff, #66b1ff);
  box-shadow: 0 16px 32px rgba(64, 158, 255, 0.28);
  color: #fff;
  cursor: pointer;
  z-index: 2000;
}

.minimized-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.minimized-text {
  font-size: 14px;
  font-weight: 600;
}

.minimized-bar :deep(.el-progress-bar__outer) {
  background: rgba(255, 255, 255, 0.25);
}

.minimized-bar :deep(.el-progress-bar__inner) {
  background: #fff;
}

.mb-16 {
  margin-bottom: 16px;
}
</style>
