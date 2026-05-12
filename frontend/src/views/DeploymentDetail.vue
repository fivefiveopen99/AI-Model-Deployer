<template>
  <div class="page-shell deployment-detail-page">
    <PageHero
      eyebrow="Deployment Detail"
      :title="deployment?.name || '部署详情'"
      description="统一查看部署来源、资源配置、Kubernetes 运行态和访问入口，同时把高频动作收敛到页头。"
    >
      <template #meta v-if="deployment">
        <span class="badge-pill">Namespace {{ deployment.namespace }}</span>
        <span class="badge-pill">Status {{ getDeploymentStatusText(deployment.status) }}</span>
        <span class="badge-pill">Replicas {{ deployment.replicas }}</span>
      </template>
      <template #actions>
        <el-button @click="$router.back()">返回</el-button>
        <el-button
          v-if="showDeployAction"
          type="success"
          @click="deployToK8s"
          :disabled="deployment?.status === 'running' || deployment?.status === 'deploying'"
        >
          <el-icon><Ship /></el-icon>
          部署到 K8s
        </el-button>
        <el-button v-if="deployment?.access_path" @click="openAccessEntry">
          <el-icon><Promotion /></el-icon>
          打开页面
        </el-button>
        <el-button type="primary" @click="showScaleDialog">
          <el-icon><ScaleToOriginal /></el-icon>
          扩缩容
        </el-button>
        <el-button @click="fetchK8sStatus" :loading="statusLoading">
          <el-icon><Refresh /></el-icon>
          刷新状态
        </el-button>
      </template>
    </PageHero>

    <template v-if="deployment">
      <section class="metrics-grid">
        <MetricCard label="Deployment ID" :value="deployment.id" hint="平台内部部署主键" tone="brand">
          <template #icon>
            <el-icon :size="28"><Key /></el-icon>
          </template>
        </MetricCard>
        <MetricCard
          label="Source"
          :value="deployment.source_type === 'image' ? '镜像' : '模型'"
          hint="决定部署来源和运行配置结构"
          tone="success"
        >
          <template #icon>
            <el-icon :size="28"><Collection /></el-icon>
          </template>
        </MetricCard>
        <MetricCard label="Replicas" :value="deployment.replicas" hint="当前数据库中的目标副本数" tone="warning">
          <template #icon>
            <el-icon :size="28"><Grid /></el-icon>
          </template>
        </MetricCard>
        <MetricCard
          label="Endpoint"
          :value="deployment.endpoint ? 'Ready' : 'Pending'"
          :hint="deployment.endpoint || deployment.access_path || '尚未生成访问地址'"
          tone="default"
        >
          <template #icon>
            <el-icon :size="28"><Connection /></el-icon>
          </template>
        </MetricCard>
      </section>

      <section class="split-detail-layout">
        <div class="content-stack">
          <PanelCard eyebrow="Overview" title="基础信息" description="部署来源、命名空间、副本数和创建时间。">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="ID">{{ deployment.id }}</el-descriptions-item>
              <el-descriptions-item label="部署来源">
                <el-tag :type="deployment.source_type === 'image' ? 'success' : 'primary'">
                  {{ deployment.source_type === 'image' ? '镜像' : '模型' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item v-if="deployment.source_type === 'model'" label="模型 ID">
                <el-button link @click="$router.push(`/models/${deployment.model_id}`)">
                  {{ deployment.model_id }}
                </el-button>
              </el-descriptions-item>
              <el-descriptions-item v-else label="镜像">
                <span class="mono-text">{{ deployment.image || '-' }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="命名空间">
                <el-tag type="info">{{ deployment.namespace }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="副本数">
                <el-tag>{{ deployment.replicas }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item v-if="deployment.source_type === 'model'" label="服务端口">
                {{ deployment.port }}
              </el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ formatDate(deployment.created_at) }}</el-descriptions-item>
              <el-descriptions-item label="更新时间">{{ formatDate(deployment.updated_at) }}</el-descriptions-item>
            </el-descriptions>
          </PanelCard>

          <PanelCard eyebrow="Routing" title="访问与服务入口" description="统一放置页面访问地址和服务端点。">
            <div class="field-stack">
              <div v-if="deployment.access_path">
                <div class="section-heading">访问地址</div>
                <el-link type="primary" class="entry-link" @click="openAccessEntry">
                  {{ accessEntryUrl }}
                </el-link>
              </div>
              <div v-if="deployment.endpoint">
                <div class="section-heading">服务端点</div>
                <el-input :model-value="deployment.endpoint" readonly>
                  <template #append>
                    <el-button @click="copyEndpoint">
                      <el-icon><CopyDocument /></el-icon>
                    </el-button>
                  </template>
                </el-input>
              </div>
              <div v-if="deployment.k8s_deployment_name">
                <div class="section-heading">Kubernetes 对象</div>
                <el-descriptions :column="1" border>
                  <el-descriptions-item label="Deployment 名称">
                    {{ deployment.k8s_deployment_name }}
                  </el-descriptions-item>
                  <el-descriptions-item v-if="deployment.k8s_service_name" label="Service 名称">
                    {{ deployment.k8s_service_name }}
                  </el-descriptions-item>
                </el-descriptions>
              </div>
            </div>
          </PanelCard>

          <PanelCard eyebrow="Logs" title="Pod 日志" description="直接查看当前部署的日志输出。">
            <div class="logs-header">
              <el-input-number v-model="tailLines" :min="10" :max="1000" :step="10" size="small" />
              <el-button size="small" @click="fetchLogs" :loading="logsLoading">
                <el-icon><Refresh /></el-icon>
                刷新日志
              </el-button>
            </div>
            <CodeBlock :content="logs || '暂无日志'" terminal />
          </PanelCard>
        </div>

        <div class="content-stack">
          <PanelCard eyebrow="Runtime" title="资源配置" description="部署时写入的资源请求与限制。">
            <CodeBlock :content="resourcesText" />
          </PanelCard>

          <PanelCard eyebrow="Storage" title="挂载配置" description="NFS 或其他挂载结构。">
            <CodeBlock :content="mountText" />
          </PanelCard>

          <PanelCard eyebrow="Environment" title="环境变量" description="传递到容器运行时的环境变量。">
            <CodeBlock :content="envText" />
          </PanelCard>

          <PanelCard
            v-if="deployment.source_type === 'image'"
            eyebrow="Workbench"
            title="命令工作台配置"
            description="镜像部署下可选的命令模板和结果目录。"
          >
            <el-alert
              v-if="!inferenceEnabled"
              title="该部署未配置命令运行参数"
              type="warning"
              :closable="false"
              show-icon
            />
            <div v-else class="field-stack">
              <div>
                <div class="section-heading">命令模板</div>
                <CodeBlock :content="deployment.inference_config.command_template" />
              </div>
              <div>
                <div class="section-heading">结果目录</div>
                <span class="mono-text">{{ deployment.inference_config.result_path }}</span>
              </div>
            </div>
          </PanelCard>

          <PanelCard
            v-if="deployment.status_message"
            eyebrow="Status"
            title="状态信息"
            description="部署阶段的错误或附加提示。"
          >
            <el-alert :title="deployment.status_message" :type="deployment.status === 'failed' ? 'error' : 'info'" show-icon />
          </PanelCard>
        </div>
      </section>
    </template>

    <el-skeleton v-else :rows="10" animated />

    <el-dialog v-model="scaleDialogVisible" title="扩缩容" width="420px">
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
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import PageHero from '@/components/ui/PageHero.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import PanelCard from '@/components/ui/PanelCard.vue'
import CodeBlock from '@/components/ui/CodeBlock.vue'
import { useDeploymentsStore } from '@/stores/deployments'
import { formatDate, getDeploymentStatusText } from '@/utils/formatters'

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

const inferenceEnabled = computed(() => Boolean(deployment.value?.inference_config?.enabled))
const accessEntryUrl = computed(() => {
  if (!deployment.value?.access_path) return ''
  const origin = window.location.origin.replace(/\/$/, '')
  return `${origin}${deployment.value.access_path}`
})
const showDeployAction = computed(() => deployment.value?.status !== 'running' && deployment.value?.status !== 'deploying')
const resourcesText = computed(() => JSON.stringify(deployment.value?.resources || {}, null, 2))
const mountText = computed(() => JSON.stringify(deployment.value?.mount_config || {}, null, 2))
const envText = computed(() => JSON.stringify(deployment.value?.env_vars || {}, null, 2))

const copyEndpoint = () => {
  if (!deployment.value?.endpoint) return
  navigator.clipboard.writeText(deployment.value.endpoint)
  ElMessage.success('已复制到剪贴板')
}

const fetchLogs = async () => {
  if (!deployment.value?.k8s_deployment_name) return
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
    await deploymentsStore.getDeploymentStatus(deployment.value.id)
    deployment.value = await deploymentsStore.fetchDeploymentDetail(deployment.value.id)
    ElMessage.success('状态已更新')
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
  if (!deployment.value) return
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

const openAccessEntry = () => {
  if (!deployment.value?.access_path) return
  router.push(deployment.value.access_path)
}

onMounted(async () => {
  try {
    deployment.value = await deploymentsStore.fetchDeploymentDetail(route.params.id)
    if (deployment.value?.k8s_deployment_name) {
      await fetchLogs()
    }
  } catch (error) {
    ElMessage.error('获取部署详情失败')
  }
})
</script>

<style scoped>
.deployment-detail-page {
  padding: 2px 0 10px;
}

.section-heading {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ui-text-faint);
}

.entry-link {
  font-family: var(--ui-font-mono);
  font-size: 13px;
  word-break: break-all;
}

.scale-content {
  padding: 12px 0 4px;
}

.scale-content p {
  margin: 0 0 14px;
}
</style>
