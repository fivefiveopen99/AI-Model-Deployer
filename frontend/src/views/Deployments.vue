<template>
  <div class="deployments-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>部署管理</span>
          <div class="header-actions">
            <el-button type="primary" @click="showCreateDialog">
              <el-icon><Plus /></el-icon>
              创建部署
            </el-button>
            <el-button @click="refreshDeployments">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="deploymentsStore.deployments" v-loading="deploymentsStore.loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="部署名称" />
        <el-table-column prop="namespace" label="命名空间" width="120">
          <template #default="{ row }">
            <el-tag type="info">{{ row.namespace }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="replicas" label="副本数" width="100">
          <template #default="{ row }">
            <el-tag>{{ row.replicas }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getDeploymentStatusType(row.status)">
              {{ getDeploymentStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="endpoint" label="访问地址">
          <template #default="{ row }">
            <span v-if="row.endpoint" class="endpoint">{{ row.endpoint }}</span>
            <span v-else class="text-gray">未部署</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button size="small" @click="viewDetail(row)">详情</el-button>
              <el-button 
                size="small" 
                type="success" 
                @click="deployToK8s(row)"
                :disabled="row.status === 'running' || row.status === 'deploying'"
              >
                部署
              </el-button>
              <el-button size="small" type="primary" @click="showScaleDialog(row)">扩缩容</el-button>
              <el-button size="small" type="danger" @click="deleteDeployment(row)">删除</el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
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
    </el-card>

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
    <el-dialog v-model="createDialogVisible" title="创建部署" width="600px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="部署名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入部署名称" />
        </el-form-item>
        <el-form-item label="选择模型" prop="model_id">
          <el-select v-model="form.model_id" placeholder="请选择模型" style="width: 100%">
            <el-option
              v-for="model in readyModels"
              :key="model.id"
              :label="model.name"
              :value="model.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="命名空间" prop="namespace">
          <el-input v-model="form.namespace" placeholder="default" />
        </el-form-item>
        <el-form-item label="副本数" prop="replicas">
          <el-input-number v-model="form.replicas" :min="1" :max="100" />
        </el-form-item>
        <el-form-item label="资源配置">
          <el-collapse>
            <el-collapse-item title="CPU / 内存配置">
              <el-form-item label="CPU限制">
                <el-input v-model="resources.limits.cpu" placeholder="500m" />
              </el-form-item>
              <el-form-item label="内存限制">
                <el-input v-model="resources.limits.memory" placeholder="512Mi" />
              </el-form-item>
              <el-form-item label="CPU请求">
                <el-input v-model="resources.requests.cpu" placeholder="250m" />
              </el-form-item>
              <el-form-item label="内存请求">
                <el-input v-model="resources.requests.memory" placeholder="256Mi" />
              </el-form-item>
            </el-collapse-item>
          </el-collapse>
        </el-form-item>
        <el-form-item label="环境变量">
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
import { useDeploymentsStore } from '@/stores/deployments'
import { useModelsStore } from '@/stores/models'
import { useWebSocket } from '@/composables/useWebSocket'
import { formatDate, getDeploymentStatusText, getDeploymentStatusType } from '@/utils/formatters'

const router = useRouter()
const deploymentsStore = useDeploymentsStore()
const modelsStore = useModelsStore()
const { isConnected, progress, progressMessage, error, connect, subscribe, unsubscribe, disconnect } = useWebSocket()

const currentPage = ref(1)
const pageSize = ref(10)
const createDialogVisible = ref(false)
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
  namespace: 'default',
  replicas: 1
})

const resources = reactive({
  limits: { cpu: '', memory: '' },
  requests: { cpu: '', memory: '' }
})

const envVars = ref([])

const rules = {
  name: [{ required: true, message: '请输入部署名称', trigger: 'blur' }],
  model_id: [{ required: true, message: '请选择模型', trigger: 'change' }],
  namespace: [{ required: true, message: '请输入命名空间', trigger: 'blur' }],
  replicas: [{ required: true, message: '请输入副本数', trigger: 'blur' }]
}

const readyModels = computed(() => {
  return modelsStore.models.filter(m => m.status === 'ready')
})

const showCreateDialog = () => {
  form.name = ''
  form.model_id = null
  form.namespace = 'default'
  form.replicas = 1
  resources.limits = { cpu: '', memory: '' }
  resources.requests = { cpu: '', memory: '' }
  envVars.value = []
  createDialogVisible.value = true
  modelsStore.fetchModels()
}

const addEnv = () => {
  envVars.value.push({ key: '', value: '' })
}

const removeEnv = (index) => {
  envVars.value.splice(index, 1)
}

const submitCreate = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        const envVarsObj = {}
        envVars.value.forEach(env => {
          if (env.key) {
            envVarsObj[env.key] = env.value
          }
        })
        
        const data = {
          ...form,
          resources: {
            limits: resources.limits.cpu || resources.limits.memory ? {
              cpu: resources.limits.cpu || undefined,
              memory: resources.limits.memory || undefined
            } : {},
            requests: resources.requests.cpu || resources.requests.memory ? {
              cpu: resources.requests.cpu || undefined,
              memory: resources.requests.memory || undefined
            } : {}
          },
          env_vars: envVarsObj
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
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.text-gray {
  color: #909399;
}

.endpoint {
  font-family: monospace;
  font-size: 12px;
  color: #409EFF;
}

.env-row {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
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

.progress-error {
  margin-top: 20px;
}
</style>
