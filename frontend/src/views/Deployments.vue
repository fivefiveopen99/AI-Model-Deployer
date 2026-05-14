<template>
  <div class="page-shell deployments-page">
    <PageHero
      class="deployments-hero"
      eyebrow="部署中心"
      title="部署管理中心"
      description="把模型部署、镜像部署、资源配置和访问入口收敛在同一条交付路径里。"
    >
      <template #meta>
        <span class="badge-pill">总数 {{ deploymentsStore.total }}</span>
        <span class="badge-pill">运行中 {{ runningCount }}</span>
        <span class="badge-pill">镜像来源 {{ imageSourceCount }}</span>
      </template>
      <template #actions>
        <el-button type="primary" class="hero-primary" @click="showCreateDialog('model')">
          <el-icon><Plus /></el-icon>
          部署模型
        </el-button>
        <el-button type="success" class="hero-primary" @click="showCreateDialog('image')">
          <el-icon><Plus /></el-icon>
          部署镜像
        </el-button>
        <el-button class="hero-secondary" @click="refreshDeployments">
          <el-icon><Refresh /></el-icon>
          刷新列表
        </el-button>
      </template>
    </PageHero>

    <section class="metrics-grid">
      <MetricCard label="部署总数" :value="deploymentsStore.total" hint="平台当前记录的全部部署对象" tone="brand">
        <template #icon>
          <el-icon :size="28"><Ship /></el-icon>
        </template>
      </MetricCard>
      <MetricCard label="运行中" :value="runningCount" hint="已经同步为运行中的在线服务" tone="success">
        <template #icon>
          <el-icon :size="28"><Promotion /></el-icon>
        </template>
      </MetricCard>
      <MetricCard label="待处理" :value="pendingCount" hint="已创建记录但还未开始或完成部署" tone="warning">
        <template #icon>
          <el-icon :size="28"><Clock /></el-icon>
        </template>
      </MetricCard>
      <MetricCard label="镜像来源" :value="imageSourceCount" hint="直接从 Registry 镜像创建的部署" tone="default">
        <template #icon>
          <el-icon :size="28"><Collection /></el-icon>
        </template>
      </MetricCard>
    </section>

    <PanelCard
      eyebrow="部署清单"
      title="所有部署"
      description="查看状态、访问地址、扩缩容与后续操作。"
    >
      <template #actions>
        <el-tag type="info" effect="plain" class="count-pill">
          {{ deploymentsStore.total }} 个部署
        </el-tag>
      </template>

      <div class="deployments-table-shell">
        <el-table
          :data="deploymentsStore.deployments"
          v-loading="deploymentsStore.loading"
          :fit="false"
          stripe
          class="deployments-table"
          empty-text=""
        >
          <el-table-column prop="id" label="ID" width="64" />
          <el-table-column prop="name" label="部署名称" width="156" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="deployment-name-cell">
              <strong class="deployment-name-primary" :title="row.name">{{ row.name }}</strong>
              <span>#{{ row.id }} · {{ row.namespace }}</span>
            </div>
          </template>
          </el-table-column>
          <el-table-column prop="source_type" label="来源" width="84">
          <template #default="{ row }">
            <el-tag :type="row.source_type === 'image' ? 'success' : 'primary'" effect="plain">
              {{ row.source_type === 'image' ? '镜像' : '模型' }}
            </el-tag>
          </template>
          </el-table-column>
          <el-table-column prop="namespace" label="命名空间" width="96">
          <template #default="{ row }">
            <el-tag type="info">{{ row.namespace }}</el-tag>
          </template>
          </el-table-column>
          <el-table-column prop="replicas" label="副本数" width="80">
          <template #default="{ row }">
            <el-tag>{{ row.replicas }}</el-tag>
          </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="96">
          <template #default="{ row }">
            <el-tag :type="getDeploymentStatusType(row.status)" effect="plain">
              {{ getDeploymentStatusText(row.status) }}
            </el-tag>
          </template>
          </el-table-column>
          <el-table-column label="访问地址" width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="access-entry-cell">
              <el-link
                v-if="row.access_path"
                type="primary"
                class="entry-link"
                @click="openAccessEntry(row)"
              >
                {{ row.access_path }}
              </el-link>
              <span v-else class="text-gray">未配置</span>
            </div>
          </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="132">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
          </el-table-column>
          <el-table-column label="操作" width="248">
          <template #default="{ row }">
            <div class="action-row">
              <el-button size="small" @click="viewDetail(row)">详情</el-button>
              <el-button
                v-if="shouldShowDeployAction(row)"
                size="small"
                type="success"
                @click="deployToK8s(row)"
                :disabled="row.status === 'running' || row.status === 'deploying'"
              >
                部署
              </el-button>
              <el-button size="small" type="primary" @click="showScaleDialog(row)">扩缩容</el-button>
              <el-button size="small" type="danger" @click="deleteDeployment(row)">删除</el-button>
            </div>
          </template>
          </el-table-column>
          <template #empty>
            <div class="deployments-empty">
              <div class="empty-title">暂无部署</div>
              <div class="empty-text">先选择“部署模型”或“部署镜像”，创建第一条部署记录。</div>
              <div class="empty-actions">
                <el-button type="primary" @click="showCreateDialog('model')">部署模型</el-button>
                <el-button type="success" class="empty-action-success" @click="showCreateDialog('image')">部署镜像</el-button>
              </div>
            </div>
          </template>
        </el-table>
      </div>

      <div v-if="deploymentsStore.total > 0" class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="deploymentsStore.total"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </PanelCard>

    <!-- 部署进度对话框 -->
    <el-dialog
      v-model="progressDialogVisible"
      title="部署进度"
      width="500px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="!deploying"
    >
      <div class="progress-content">
        <el-progress
          :percentage="deployProgress"
          :status="deployProgress === 100 ? 'success' : ''"
          :stroke-width="20"
          striped
          striped-flow
        />
        <div class="progress-message">
          <el-icon v-if="deploying" class="is-loading"><Loading /></el-icon>
          <span>{{ progressMessage }}</span>
        </div>
        <div v-if="deployError" class="progress-error">
          <el-alert :title="deployError" type="error" show-icon />
        </div>
      </div>
      <template #footer>
        <el-button @click="progressDialogVisible = false" :disabled="deploying">
          {{ deploying ? '部署中...' : '关闭' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 创建部署对话框 -->
    <el-dialog
      v-model="createDialogVisible"
      :title="createMode === 'image' ? '部署镜像' : '部署模型'"
      width="720px"
      top="6vh"
      class="deployment-create-dialog"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="部署名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入部署名称" />
        </el-form-item>
        <el-form-item v-if="createMode === 'model'" label="选择模型" prop="model_id">
          <el-select v-model="form.model_id" placeholder="请选择模型" style="width: 100%">
            <el-option
              v-for="model in readyModels"
              :key="model.id"
              :label="model.name"
              :value="model.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-else label="选择镜像" prop="image">
          <el-select
            v-model="form.image"
            placeholder="请选择私有仓库镜像"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="image in registryImageOptions"
              :key="image.image_ref"
              :label="image.image_ref"
              :value="image.image_ref"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="createMode === 'image'" label="工作台配置">
          <div class="mount-panel">
            <div class="mount-grid">
                <div class="resource-field inference-full-width">
                  <label>命令模板</label>
                  <el-input
                    v-model="inferenceConfig.command_template"
                    type="textarea"
                    :rows="4"
                    placeholder="如：python test_lora_sd.py --model_dir {{model_dir}} --position {{position}}"
                  />
                <div class="form-tip">使用 <code v-pre>{{variable_name}}</code> 定义可变参数，部署后在命令工作台中填写并运行。</div>
              </div>
              <div class="resource-field">
                <label>结果目录</label>
                <el-input v-model="inferenceConfig.result_path" placeholder="如：/workspace/output" />
              </div>
              <div class="resource-field inference-full-width">
                <label>模板变量</label>
                <div class="variable-tags" v-if="inferenceVariableNames.length">
                  <el-tag v-for="name in inferenceVariableNames" :key="name">{{ name }}</el-tag>
                </div>
                <div v-else class="form-tip">当前模板未解析到变量，占位符格式为 <code v-pre>{{variable_name}}</code>。</div>
              </div>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="命名空间" prop="namespace">
          <el-input v-model="form.namespace" placeholder="default" />
        </el-form-item>
        <el-form-item label="副本数" prop="replicas">
          <el-input-number v-model="form.replicas" :min="1" :max="100" />
        </el-form-item>
        <el-form-item label="资源配置">
          <div class="resource-panel">
            <div class="resource-grid">
              <div class="resource-field">
                <label>CPU 请求</label>
                <el-select v-model="resources.requests.cpu" placeholder="不设置" clearable>
                  <el-option
                    v-for="option in cpuOptions"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </div>
              <div class="resource-field">
                <label>CPU 限制</label>
                <el-select v-model="resources.limits.cpu" placeholder="不设置" clearable>
                  <el-option
                    v-for="option in cpuOptions"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </div>
              <div class="resource-field">
                <label>内存请求</label>
                <el-select v-model="resources.requests.memory" placeholder="不设置" clearable>
                  <el-option
                    v-for="option in memoryOptions"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </div>
              <div class="resource-field">
                <label>内存限制</label>
                <el-select v-model="resources.limits.memory" placeholder="不设置" clearable>
                  <el-option
                    v-for="option in memoryOptions"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </div>
              <div class="resource-field">
                <label>显卡类型</label>
                <el-select v-model="resources.gpu.resourceName" @change="handleGpuTypeChange">
                  <el-option label="不使用显卡" value="" />
                  <el-option label="NVIDIA GPU" value="nvidia.com/gpu" />
                </el-select>
              </div>
              <div class="resource-field">
                <label>显卡数量</label>
                <el-select
                  v-model="resources.gpu.count"
                  :disabled="!resources.gpu.resourceName"
                >
                  <el-option
                    v-for="option in gpuCountOptions"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </div>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="挂载配置">
          <div class="mount-panel">
            <div class="mount-grid">
              <div class="resource-field">
                <label>挂载类型</label>
                <el-select v-model="mountConfig.type" @change="handleMountTypeChange">
                  <el-option label="不挂载" value="" />
                  <el-option label="NFS" value="nfs" />
                </el-select>
              </div>
              <div class="resource-field mount-browser-field" v-if="mountConfig.type === 'nfs'">
                <label>NFS 目录</label>
                <el-input v-model="mountConfig.directory" readonly placeholder="请选择 NFS 目录" />
                <div class="form-tip" v-if="nfsServer">挂载服务器：{{ nfsServer }}</div>
                <div class="form-tip" v-if="nfsExportRoot">导出根目录：{{ nfsExportRoot }}</div>
                <div class="form-tip" v-if="nfsRootPath && nfsRootPath !== nfsExportRoot">浏览目录：{{ nfsRootPath }}</div>
                <div class="browser-toolbar">
                  <div class="browser-path">
                    <span>当前目录：</span>
                    <code>{{ nfsCurrentPath || '/' }}</code>
                  </div>
                  <div class="browser-actions">
                    <el-button
                      size="small"
                      :disabled="nfsDirectoriesLoading || nfsParentPath === null"
                      @click="openNfsDirectory(nfsParentPath || '')"
                    >
                      返回上级
                    </el-button>
                    <el-button size="small" :loading="nfsDirectoriesLoading" @click="fetchNfsDirectories(nfsCurrentPath)">
                      刷新目录
                    </el-button>
                  </div>
                </div>
                <div class="directory-list" v-if="nfsDirectories.length">
                  <el-button
                    v-for="directory in nfsDirectories"
                    :key="directory.path"
                    text
                    class="directory-button"
                    @click="openNfsDirectory(directory.path)"
                  >
                    {{ directory.name }}
                  </el-button>
                </div>
                <el-table
                  :data="nfsDirectories"
                  size="small"
                  v-loading="nfsDirectoriesLoading"
                  empty-text="当前目录没有可选子目录"
                  class="mount-directory-table"
                >
                  <el-table-column prop="name" label="目录名" min-width="220" />
                  <el-table-column label="操作" width="120">
                    <template #default="{ row }">
                      <el-button
                        size="small"
                        :type="mountConfig.directory === row.path ? 'success' : 'primary'"
                        plain
                        @click="selectNfsDirectory(row.path)"
                      >
                        {{ mountConfig.directory === row.path ? '已选择' : '选择' }}
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
              <div class="resource-field" v-if="mountConfig.type">
                <label>容器挂载路径</label>
                <el-input v-model="mountConfig.mount_path" placeholder="如：/workspace/models" />
              </div>
              <div class="resource-field" v-if="mountConfig.type">
                <label>子路径</label>
                <el-input v-model="mountConfig.sub_path" placeholder="可选，如：project-a" />
              </div>
              <div class="resource-field" v-if="mountConfig.type">
                <label>只读挂载</label>
                <el-switch v-model="mountConfig.read_only" />
              </div>
            </div>
          </div>
        </el-form-item>
        <el-form-item v-if="createMode === 'model'" label="环境变量">
          <div v-for="(env, index) in envVars" :key="index" class="env-row">
            <el-input v-model="env.key" placeholder="Key" style="width: 150px" />
            <el-input v-model="env.value" placeholder="Value" style="width: 200px; margin-left: 10px" />
            <el-button type="danger" circle size="small" @click="removeEnv(index)" style="margin-left: 10px">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <el-button type="primary" text @click="addEnv">
            <el-icon><Plus /></el-icon>
            添加环境变量
          </el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreate" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 扩缩容对话框 -->
    <el-dialog v-model="scaleDialogVisible" title="扩缩容" width="400px">
      <div v-if="currentDeployment" class="scale-content">
        <p>部署名称: <strong>{{ currentDeployment.name }}</strong></p>
        <p>当前副本数: <strong>{{ currentDeployment.replicas }}</strong></p>
        <el-form-item label="新副本数">
          <el-input-number v-model="scaleReplicas" :min="0" :max="100" />
        </el-form-item>
      </div>
      <template #footer>
        <el-button @click="scaleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitScale" :loading="scaling">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHero from '@/components/ui/PageHero.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import PanelCard from '@/components/ui/PanelCard.vue'
import { useDeploymentsStore } from '@/stores/deployments'
import { useModelsStore } from '@/stores/models'
import { useWebSocket } from '@/composables/useWebSocket'
import { systemApi } from '@/api'
import { formatDate, getDeploymentStatusText, getDeploymentStatusType } from '@/utils/formatters'

const router = useRouter()
const deploymentsStore = useDeploymentsStore()
const modelsStore = useModelsStore()
const { isConnected, progress, progressMessage, error, connect, subscribe, unsubscribe, disconnect } = useWebSocket()

const currentPage = ref(1)
const pageSize = ref(10)
const createDialogVisible = ref(false)
const createMode = ref('model')
const scaleDialogVisible = ref(false)
const progressDialogVisible = ref(false)
const submitting = ref(false)
const scaling = ref(false)
const deploying = ref(false)
const currentDeployment = ref(null)
const scaleReplicas = ref(1)
const formRef = ref(null)

// 进度条相关
const deployProgress = ref(0)
const deployError = ref('')
const currentTaskId = ref('')

const form = reactive({
  name: '',
  model_id: null,
  image: '',
  namespace: 'default',
  replicas: 1
})
const registryImageOptions = ref([])
const inferenceConfig = reactive({
  command_template: '',
  result_path: ''
})

const resources = reactive({
  limits: { cpu: '', memory: '' },
  requests: { cpu: '', memory: '' },
  gpu: { resourceName: '', count: 0 }
})
const mountConfig = reactive({
  type: '',
  directory: '',
  mount_path: '',
  sub_path: '',
  read_only: false
})
const nfsRootPath = ref('')
const nfsServer = ref('')
const nfsExportRoot = ref('')
const nfsCurrentPath = ref('')
const nfsParentPath = ref(null)
const nfsDirectoriesLoading = ref(false)
const nfsDirectories = ref([])

const envVars = ref([])

const cpuOptions = [
  { label: '0.25 核', value: '250m' },
  { label: '0.5 核', value: '500m' },
  { label: '1 核', value: '1' },
  { label: '2 核', value: '2' },
  { label: '4 核', value: '4' },
  { label: '8 核', value: '8' }
]

const memoryOptions = [
  { label: '256 MiB', value: '256Mi' },
  { label: '512 MiB', value: '512Mi' },
  { label: '1 GiB', value: '1Gi' },
  { label: '2 GiB', value: '2Gi' },
  { label: '4 GiB', value: '4Gi' },
  { label: '8 GiB', value: '8Gi' },
  { label: '16 GiB', value: '16Gi' },
  { label: '32 GiB', value: '32Gi' }
]

const gpuCountOptions = [
  { label: '0 张', value: 0 },
  { label: '1 张', value: 1 },
  { label: '2 张', value: 2 },
  { label: '4 张', value: 4 },
  { label: '8 张', value: 8 }
]

const rules = {
  name: [{ required: true, message: '请输入部署名称', trigger: 'blur' }],
  model_id: [{
    validator: (rule, value, callback) => {
      if (createMode.value === 'model' && !value) {
        callback(new Error('请选择模型'))
        return
      }
      callback()
    },
    trigger: 'change'
  }],
  image: [{
    validator: (rule, value, callback) => {
      if (createMode.value === 'image' && !value) {
        callback(new Error('请选择镜像'))
        return
      }
      callback()
    },
    trigger: 'change'
  }],
  namespace: [{ required: true, message: '请输入命名空间', trigger: 'blur' }],
  replicas: [{ required: true, message: '请输入副本数', trigger: 'blur' }]
}

const isRegistryBackedModel = (model) => {
  return Boolean(
    model?.status === 'ready' &&
    model?.docker_image &&
    model?.docker_image_tag
  )
}

const isImageWorkflowModel = (model) => {
  return Boolean(
    model?.config?.workflow_type === 'finetune' ||
    model?.config?.runtime_spec?.dockerfile_content
  )
}

const isPlatformModelRegistryRepository = (repository, namespacePrefix = '') => {
  const normalizedRepository = (repository || '').trim().replace(/^\/+|\/+$/g, '')
  const normalizedNamespace = (namespacePrefix || '').trim().replace(/^\/+|\/+$/g, '')
  const platformRepository = normalizedNamespace ? `${normalizedNamespace}/ai-model` : 'ai-model'

  return normalizedRepository === platformRepository
}

const readyModels = computed(() => {
  return modelsStore.models.filter(model => (
    isRegistryBackedModel(model) &&
    !isImageWorkflowModel(model)
  ))
})

const runningCount = computed(() => deploymentsStore.deployments.filter((deployment) => deployment.status === 'running').length)
const pendingCount = computed(() => deploymentsStore.deployments.filter((deployment) => ['pending', 'deploying'].includes(deployment.status)).length)
const imageSourceCount = computed(() => deploymentsStore.deployments.filter((deployment) => deployment.source_type === 'image').length)

const inferenceVariableNames = computed(() => {
  const matches = inferenceConfig.command_template.matchAll(/\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}/g)
  const seen = new Set()
  const names = []
  for (const match of matches) {
    const name = match[1]
    if (!seen.has(name)) {
      seen.add(name)
      names.push(name)
    }
  }
  return names
})

const shouldShowDeployAction = (deployment) => {
  return deployment?.status !== 'running' && deployment?.status !== 'deploying'
}

const loadRegistryImages = async () => {
  const response = await systemApi.getRegistryImages()
  const items = response.data.items || []
  const namespacePrefix = response.data.namespace_prefix || ''

  registryImageOptions.value = items
    .filter(item => !isPlatformModelRegistryRepository(item.repository, namespacePrefix))
    .flatMap(item => (item.tags || []).map(tag => ({
      repository: item.repository,
      tag,
      image_ref: `${item.repository}:${tag}`
    })))
}

const showCreateDialog = async (mode = 'model') => {
  createMode.value = mode
  form.name = ''
  form.model_id = null
  form.image = ''
  form.namespace = 'default'
  form.replicas = 1
  inferenceConfig.command_template = ''
  inferenceConfig.result_path = ''
  resources.limits = { cpu: '', memory: '' }
  resources.requests = { cpu: '', memory: '' }
  resources.gpu = { resourceName: '', count: 0 }
  mountConfig.type = ''
  mountConfig.directory = ''
  mountConfig.mount_path = ''
  mountConfig.sub_path = ''
  mountConfig.read_only = false
  nfsRootPath.value = ''
  nfsServer.value = ''
  nfsExportRoot.value = ''
  nfsCurrentPath.value = ''
  nfsParentPath.value = null
  nfsDirectories.value = []
  envVars.value = []
  createDialogVisible.value = true
  if (mode === 'model') {
    await modelsStore.fetchModels()
  } else {
    await loadRegistryImages()
  }
}

const addEnv = () => {
  envVars.value.push({ key: '', value: '' })
}

const removeEnv = (index) => {
  envVars.value.splice(index, 1)
}

const handleGpuTypeChange = (resourceName) => {
  resources.gpu.count = resourceName ? 1 : 0
}

const handleMountTypeChange = (type) => {
  if (type !== 'nfs') {
    mountConfig.directory = ''
    nfsServer.value = ''
    nfsExportRoot.value = ''
    nfsCurrentPath.value = ''
    nfsParentPath.value = null
    nfsDirectories.value = []
  }
  if (!type) {
    mountConfig.mount_path = ''
    mountConfig.sub_path = ''
    mountConfig.read_only = false
  }
  if (type === 'nfs') {
    fetchNfsDirectories('')
  }
}

const fetchNfsDirectories = async (path = '') => {
  nfsDirectoriesLoading.value = true
  try {
    const response = await systemApi.getNfsDirectories(path)
    nfsRootPath.value = response.data.root_path || ''
    nfsServer.value = response.data.server || ''
    nfsExportRoot.value = response.data.export_root || ''
    nfsCurrentPath.value = response.data.current_path || ''
    nfsParentPath.value = response.data.parent_path ?? null
    nfsDirectories.value = response.data.directories || []
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.message || '读取 NFS 目录失败')
  } finally {
    nfsDirectoriesLoading.value = false
  }
}

const openNfsDirectory = async (path = '') => {
  await fetchNfsDirectories(path)
}

const selectNfsDirectory = (path) => {
  mountConfig.directory = path
}

const buildResourceConfig = () => {
  const limits = {}
  const requests = {}

  if (resources.limits.cpu) limits.cpu = resources.limits.cpu
  if (resources.limits.memory) limits.memory = resources.limits.memory
  if (resources.requests.cpu) requests.cpu = resources.requests.cpu
  if (resources.requests.memory) requests.memory = resources.requests.memory

  if (resources.gpu.resourceName && resources.gpu.count > 0) {
    limits[resources.gpu.resourceName] = String(resources.gpu.count)
  }

  return {
    limits,
    requests
  }
}

const buildMountConfig = () => {
  if (!mountConfig.type) {
    return {}
  }

  const config = {
    enabled: true,
    type: mountConfig.type,
    mount_path: mountConfig.mount_path,
    sub_path: mountConfig.sub_path || '',
    read_only: mountConfig.read_only
  }

  if (mountConfig.type === 'nfs') {
    config.directory = mountConfig.directory
  }

  return config
}

const submitCreate = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        if (createMode.value === 'image') {
          if (!inferenceConfig.command_template.trim()) {
            ElMessage.error('镜像部署必须填写命令模板')
            return
          }
          if (!inferenceConfig.result_path.trim()) {
            ElMessage.error('镜像部署必须填写结果目录')
            return
          }
        }

        const envVarsObj = {}
        envVars.value.forEach(env => {
          if (env.key) {
            envVarsObj[env.key] = env.value
          }
        })
        
        const data = {
          ...form,
          source_type: createMode.value,
          resources: buildResourceConfig(),
          mount_config: buildMountConfig(),
          env_vars: createMode.value === 'model' ? envVarsObj : {},
          inference_config: createMode.value === 'image' ? {
            enabled: Boolean(inferenceConfig.command_template.trim() && inferenceConfig.result_path.trim()),
            command_template: inferenceConfig.command_template.trim(),
            variable_names: inferenceVariableNames.value,
            result_source: 'container',
            result_path: inferenceConfig.result_path.trim()
          } : {}
        }
        
        await deploymentsStore.createDeployment(data)
        ElMessage.success('部署创建成功')
        createDialogVisible.value = false
        refreshDeployments()
      } catch (error) {
        ElMessage.error('部署创建失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        submitting.value = false
      }
    }
  })
}

const deployToK8s = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要部署 "${row.name}" 到 Kubernetes 吗？`,
      '确认部署',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )
    
    deploying.value = true
    deployProgress.value = 0
    deployError.value = ''
    progressDialogVisible.value = true
    
    // 启动部署任务
    const result = await deploymentsStore.deployToK8s(row.id)
    
    if (result.task_id) {
      currentTaskId.value = result.task_id
      
      // 订阅进度
      subscribe(result.task_id)
      
      // 监听进度变化
      const unwatch = watch(() => progress.value, (newProgress) => {
        deployProgress.value = newProgress
        
        if (newProgress === 100) {
          deploying.value = false
          ElMessage.success('部署成功！')
          refreshDeployments()
          unwatch()
        }
      })
      
      // 监听错误
      const unwatchError = watch(() => error.value, (newError) => {
        if (newError) {
          deployError.value = newError
          deploying.value = false
          ElMessage.error('部署失败: ' + newError)
          unwatchError()
        }
      })
    }
  } catch (error) {
    deploying.value = false
    deployError.value = error.message || '部署失败'
    if (error !== 'cancel') {
      ElMessage.error('部署失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

const showScaleDialog = (row) => {
  currentDeployment.value = row
  scaleReplicas.value = row.replicas
  scaleDialogVisible.value = true
}

const submitScale = async () => {
  if (!currentDeployment.value) return
  
  scaling.value = true
  try {
    await deploymentsStore.scaleDeployment(currentDeployment.value.id, scaleReplicas.value)
    ElMessage.success('扩缩容成功')
    scaleDialogVisible.value = false
    refreshDeployments()
  } catch (error) {
    ElMessage.error('扩缩容失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    scaling.value = false
  }
}

const deleteDeployment = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除部署 "${row.name}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await deploymentsStore.deleteDeployment(row.id)
    ElMessage.success('删除成功')
    refreshDeployments()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

const viewDetail = (row) => {
  router.push(`/deployments/${row.id}`)
}

const openAccessEntry = (row) => {
  if (!row?.access_path) return
  const target = router.resolve(row.access_path)
  window.open(target.href, '_blank', 'noopener')
}

const refreshDeployments = () => {
  deploymentsStore.fetchDeployments({
    skip: (currentPage.value - 1) * pageSize.value,
    limit: pageSize.value
  })
}

const handleSizeChange = (val) => {
  pageSize.value = val
  refreshDeployments()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  refreshDeployments()
}

onMounted(() => {
  refreshDeployments()
  // 启动自动轮询，每10秒刷新一次部署状态
  startPolling()
})

onUnmounted(() => {
  // 组件卸载时停止轮询
  stopPolling()
})

// 轮询定时器
let pollingTimer = null

const startPolling = () => {
  // 每10秒刷新一次部署列表
  pollingTimer = setInterval(() => {
    // 只在页面可见时刷新
    if (!document.hidden) {
      refreshDeployments()
    }
  }, 10000)
}

const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}
</script>

<style scoped>
.deployments-page {
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.deployments-page :deep(.deployments-hero .page-hero__copy) {
  padding-left: 0;
}

.deployments-page :deep(.deployments-hero .page-hero__meta) {
  margin-left: 0;
}

.hero-primary,
.hero-secondary {
  min-width: 112px;
  min-height: 42px;
  padding: 0 16px;
}

.deployments-shell :deep(.el-card__body) {
  padding-top: 8px;
}

.shell-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 18px;
}

.shell-header h2 {
  margin: 0;
  font-size: 24px;
  line-height: 1.15;
  letter-spacing: -0.03em;
}

.shell-header p {
  margin-top: 6px;
  font-size: 13px;
  color: #667085;
}

.count-pill {
  padding: 0 12px;
  min-height: 34px;
}

.deployments-table-shell {
  width: 100%;
  overflow-x: auto;
}

.pagination {
  margin-top: 18px;
  display: flex;
  justify-content: flex-end;
}

.text-gray {
  color: #8e8e93;
}

.form-tip {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
}

.deployment-name-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.deployment-name-cell strong {
  font-size: 14px;
  color: #1d1d1f;
}

.deployment-name-primary {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.deployment-name-cell span {
  font-size: 12px;
  color: #86868b;
}

.access-entry-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.entry-link {
  display: inline-block;
  max-width: 100%;
  color: #2563eb;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.deployments-table {
  min-width: 1060px;
}

.action-row {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 6px;
  white-space: nowrap;
}

.action-row :deep(.el-button) {
  flex: 0 0 auto;
  margin-left: 0 !important;
}

.deployments-table :deep(.el-table__header th) {
  height: 50px;
  white-space: nowrap;
}

.deployments-table :deep(.el-table__empty-block) {
  min-height: 220px;
}

.deployments-table :deep(.el-table__row td) {
  height: 62px;
  vertical-align: top;
}

.deployments-table :deep(.cell) {
  line-height: 1.45;
}

.deployments-table :deep(.el-table__body td) {
  padding: 14px 0;
}

.deployments-empty {
  display: flex;
  min-height: 220px;
  padding: 28px 16px 20px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 12px;
}

.empty-title {
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
}

.empty-text {
  max-width: 420px;
  font-size: 13px;
  line-height: 1.7;
  color: #667085;
}

.empty-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
}

.empty-actions :deep(.empty-action-success) {
  color: #ffffff !important;
  border-color: transparent !important;
  background: linear-gradient(180deg, #34c759 0%, #2fb451 100%) !important;
  box-shadow: 0 8px 18px rgba(47, 180, 81, 0.2);
}

.empty-actions :deep(.empty-action-success:hover),
.empty-actions :deep(.empty-action-success:focus-visible) {
  color: #ffffff !important;
  background: linear-gradient(180deg, #3fd065 0%, #35bd57 100%) !important;
  border-color: transparent !important;
}

.env-row {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.resource-panel {
  width: 100%;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  padding: 16px;
  background: #fafafa;
}

.mount-panel {
  width: 100%;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  padding: 16px;
  background: #fafafa;
}

.mount-browser-field {
  grid-column: 1 / -1;
}

.inference-full-width {
  grid-column: 1 / -1;
}

.variable-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.resource-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.mount-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.mount-directory-table {
  margin-top: 12px;
}

.resource-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.resource-field label {
  font-size: 13px;
  color: #606266;
  line-height: 1;
}

.resource-field :deep(.el-select) {
  width: 100%;
}

.scale-content {
  padding: 20px 0;
}

.scale-content p {
  margin-bottom: 15px;
}

.progress-content {
  padding: 20px 0;
}

.progress-message {
  margin-top: 20px;
  text-align: center;
  color: #606266;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

@media (max-width: 900px) {
  .deployment-create-dialog {
    --el-dialog-margin-top: 4vh;
  }

  .shell-header {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 720px) {
  .hero-primary,
  .hero-secondary {
    flex: 1 1 0;
  }

  .empty-actions {
    width: 100%;
  }

  .empty-actions :deep(.el-button) {
    flex: 1 1 0;
  }

  .resource-grid,
  .mount-grid {
    grid-template-columns: 1fr;
  }
}
</style>
