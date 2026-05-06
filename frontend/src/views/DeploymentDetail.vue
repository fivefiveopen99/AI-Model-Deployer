<template>
  <div class="deployment-detail-page">
    <el-page-header @back="$router.back()" title="部署详情" />
    
    <el-card v-if="deployment" class="detail-card">
      <template #header>
        <div class="card-header">
          <span>{{ deployment.name }}</span>
          <el-tag :type="getDeploymentStatusType(deployment.status)">
            {{ getDeploymentStatusText(deployment.status) }}
          </el-tag>
        </div>
      </template>
      
      <el-descriptions :column="2" border>
        <el-descriptions-item label="ID">{{ deployment.id }}</el-descriptions-item>
        <el-descriptions-item label="模型ID">
          <el-button link @click="$router.push(`/models/${deployment.model_id}`)">
            {{ deployment.model_id }}
          </el-button>
        </el-descriptions-item>
        <el-descriptions-item label="命名空间">
          <el-tag type="info">{{ deployment.namespace }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="副本数">
          <el-tag>{{ deployment.replicas }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(deployment.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatDate(deployment.updated_at) }}</el-descriptions-item>
      </el-descriptions>
      
      <el-divider />
      
      <div class="section" v-if="deployment.endpoint">
        <h4>访问地址</h4>
        <el-input v-model="deployment.endpoint" readonly>
          <template #append>
            <el-button @click="copyEndpoint">
              <el-icon><CopyDocument /></el-icon>
            </el-button>
          </template>
        </el-input>
      </div>
      
      <div class="section" v-if="deployment.k8s_deployment_name">
        <h4>Kubernetes信息</h4>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="Deployment名称">
            {{ deployment.k8s_deployment_name }}
          </el-descriptions-item>
          <el-descriptions-item label="Service名称">
            {{ deployment.k8s_service_name }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
      
      <div class="section">
        <h4>资源配置</h4>
        <pre class="config-code">{{ JSON.stringify(deployment.resources, null, 2) }}</pre>
      </div>
      
      <div class="section">
        <h4>环境变量</h4>
        <pre class="config-code">{{ JSON.stringify(deployment.env_vars, null, 2) }}</pre>
      </div>
      
      <div class="section" v-if="deployment.status_message">
        <h4>状态信息</h4>
        <el-alert :title="deployment.status_message" :type="deployment.status === 'failed' ? 'error' : 'info'" />
      </div>
      
      <el-divider />
      
      <div class="section">
        <h4>Pod日志</h4>
        <div class="logs-header">
          <el-input-number v-model="tailLines" :min="10" :max="1000" :step="10" size="small" />
          <el-button size="small" @click="fetchLogs" :loading="logsLoading">
            <el-icon><Refresh /></el-icon>
            刷新日志
          </el-button>
        </div>
        <pre class="logs-content" v-loading="logsLoading">{{ logs || '暂无日志' }}</pre>
      </div>
      
      <div class="actions">
        <el-button 
          type="success" 
          @click="deployToK8s"
          :disabled="deployment.status === 'running' || deployment.status === 'deploying'"
        >
          <el-icon><Ship /></el-icon>
          部署到K8s
        </el-button>
        <el-button 
          type="primary" 
          @click="goToPlayground"
          :disabled="!deployment.endpoint"
        >
          <el-icon><ChatLineRound /></el-icon>
          交互测试
        </el-button>
        <el-button type="primary" @click="showScaleDialog">
          <el-icon><ScaleToOriginal /></el-icon>
          扩缩容
        </el-button>
        <el-button @click="fetchK8sStatus" :loading="statusLoading">
          <el-icon><Refresh /></el-icon>
          刷新状态
        </el-button>
      </div>
    </el-card>
    
    <el-skeleton v-else :rows="10" animated />

    <!-- 扩缩容对话框 -->
    <el-dialog v-model="scaleDialogVisible" title="扩缩容" width="400px">
      <div class="scale-content">
        <p>当前副本数: <strong>{{ deployment?.replicas }}</strong></p>
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
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useDeploymentsStore } from '@/stores/deployments'
import { formatDate, getDeploymentStatusText, getDeploymentStatusType } from '@/utils/formatters'

const route = useRoute()
const router = useRouter()
const deploymentsStore = useDeploymentsStore()

const deployment = ref(null)
const logs = ref('')
const tailLines = ref(100)
const logsLoading = ref(false)
const statusLoading = ref(false)
const scaleDialogVisible = ref(false)
const scaleReplicas = ref(1)
const scaling = ref(false)

const copyEndpoint = () => {
  navigator.clipboard.writeText(deployment.value.endpoint)
  ElMessage.success('已复制到剪贴板')
}

const fetchLogs = async () => {
  if (!deployment.value) return
  logsLoading.value = true
  try {
    await deploymentsStore.getDeploymentLogs(deployment.value.id, tailLines.value)
    logs.value = deploymentsStore.logs
  } catch (error) {
    ElMessage.error('获取日志失败')
  } finally {
    logsLoading.value = false
  }
}

const fetchK8sStatus = async () => {
  if (!deployment.value) return
  statusLoading.value = true
  try {
    const status = await deploymentsStore.getDeploymentStatus(deployment.value.id)
    ElMessage.success('状态已更新')
    console.log('K8s Status:', status)
  } catch (error) {
    ElMessage.error('获取状态失败')
  } finally {
    statusLoading.value = false
  }
}

const deployToK8s = async () => {
  if (!deployment.value) return
  try {
    await deploymentsStore.deployToK8s(deployment.value.id)
    ElMessage.success('部署任务已启动')
    deployment.value = await deploymentsStore.fetchDeploymentDetail(deployment.value.id)
  } catch (error) {
    ElMessage.error('部署失败: ' + (error.response?.data?.detail || error.message))
  }
}

const showScaleDialog = () => {
  scaleReplicas.value = deployment.value.replicas
  scaleDialogVisible.value = true
}

const submitScale = async () => {
  if (!deployment.value) return
  scaling.value = true
  try {
    await deploymentsStore.scaleDeployment(deployment.value.id, scaleReplicas.value)
    ElMessage.success('扩缩容成功')
    scaleDialogVisible.value = false
    deployment.value = await deploymentsStore.fetchDeploymentDetail(deployment.value.id)
  } catch (error) {
    ElMessage.error('扩缩容失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    scaling.value = false
  }
}

const goToPlayground = () => {
  if (!deployment.value) return
  router.push(`/deployments/${deployment.value.id}/playground`)
}

onMounted(async () => {
  const id = route.params.id
  try {
    deployment.value = await deploymentsStore.fetchDeploymentDetail(id)
    if (deployment.value?.k8s_deployment_name) {
      fetchLogs()
    }
  } catch (error) {
    ElMessage.error('获取部署详情失败')
  }
})
</script>

<style scoped>
.deployment-detail-page {
  padding: 0;
}

.detail-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section {
  margin: 20px 0;
}

.section h4 {
  margin-bottom: 10px;
  color: #606266;
}

.config-code {
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  overflow-x: auto;
}

.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.logs-content {
  background-color: #1e1e1e;
  color: #d4d4d4;
  padding: 15px;
  border-radius: 4px;
  max-height: 400px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.actions {
  margin-top: 30px;
  display: flex;
  gap: 10px;
}

.scale-content {
  padding: 20px 0;
}

.scale-content p {
  margin-bottom: 15px;
}
</style>
