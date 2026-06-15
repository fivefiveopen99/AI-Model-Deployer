<template>
  <div class="page-shell deployment-detail-page">
    <PageHero
      eyebrow="部署详情"
      :title="deployment?.name || '部署详情'"
      description="集中查看部署来源、资源配置、Kubernetes 运行情况和访问入口，便于在一个页面完成排查和后续操作。"
    >
      <template #meta v-if="deployment">
        <span class="badge-pill">命名空间 {{ deployment.namespace }}</span>
        <span class="badge-pill">状态 {{ getDeploymentStatusText(deployment.status) }}</span>
        <span class="badge-pill">副本数 {{ deployment.replicas }}</span>
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
        <MetricCard label="部署编号" :value="deployment.id" hint="平台内部用于追踪部署记录的唯一编号。" tone="brand">
          <template #icon>
            <el-icon :size="28"><Key /></el-icon>
          </template>
        </MetricCard>
        <MetricCard
          label="部署来源"
          :value="deployment.source_type === 'image' ? '镜像' : '模型'"
          hint="决定当前部署来自模型服务还是镜像工作台路径。"
          tone="success"
        >
          <template #icon>
            <el-icon :size="28"><Collection /></el-icon>
          </template>
        </MetricCard>
        <MetricCard label="副本数量" :value="deployment.replicas" hint="当前数据库中记录的目标副本数。" tone="warning">
          <template #icon>
            <el-icon :size="28"><Grid /></el-icon>
          </template>
        </MetricCard>
        <MetricCard
          label="服务入口"
          :value="deployment.endpoint ? '已生成' : '待生成'"
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
          <PanelCard eyebrow="概览信息" title="基础信息" description="集中展示部署来源、命名空间、副本数和创建时间。">
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

          <PanelCard eyebrow="访问入口" title="访问与服务入口" description="统一展示页面访问地址、服务端点和 Kubernetes 对象信息。">
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
                  <el-descriptions-item label="部署名称">
                    {{ deployment.k8s_deployment_name }}
                  </el-descriptions-item>
                  <el-descriptions-item v-if="deployment.k8s_service_name" label="服务名称">
                    {{ deployment.k8s_service_name }}
                  </el-descriptions-item>
                </el-descriptions>
              </div>
            </div>
          </PanelCard>

          <PanelCard eyebrow="运行日志" title="容器日志" description="直接查看当前部署的日志输出，用于排查运行状态和错误信息。">
            <div class="logs-header">
              <el-input-number v-model="tailLines" :min="10" :max="1000" :step="10" size="small" />
              <el-button size="small" @click="fetchLogs" :loading="logsLoading">
                <el-icon><Refresh /></el-icon>
                刷新日志
              </el-button>
            </div>
            <CodeBlock :content="logs || '暂无日志'" terminal />
          </PanelCard>

          <PanelCard
            v-if="inferenceEnabled"
            eyebrow="API 调用"
            title="命令工作台 API"
            description="外部程序可以直接调用平台代理 API。"
          >
            <div class="api-endpoint-list">
              <div v-for="item in apiEndpoints" :key="item.path" class="api-endpoint-item">
                <div class="api-endpoint-main">
                  <el-tag :type="item.method === 'POST' ? 'success' : 'info'" effect="plain">
                    {{ item.method }}
                  </el-tag>
                  <code>{{ item.url }}</code>
                </div>
                <div class="api-endpoint-meta">
                  <span>{{ item.description }}</span>
                  <el-button size="small" @click="copyText(item.url)">
                    <el-icon><CopyDocument /></el-icon>
                  </el-button>
                </div>
              </div>
            </div>

            <div class="section-heading api-section-heading">curl 示例</div>
            <el-tabs class="api-curl-tabs">
              <el-tab-pane label="启动任务">
                <CodeBlock :content="runInferenceCurl" terminal />
              </el-tab-pane>
              <el-tab-pane label="查询结果">
                <CodeBlock :content="queryResultCurl" terminal />
              </el-tab-pane>
              <el-tab-pane label="下载全部">
                <CodeBlock :content="downloadAllCurl" terminal />
              </el-tab-pane>
            </el-tabs>
          </PanelCard>
        </div>

        <div class="content-stack">
          <PanelCard eyebrow="运行配置" title="资源配置" description="展示部署时写入的资源请求和资源限制。">
            <CodeBlock :content="resourcesText" />
          </PanelCard>

          <PanelCard eyebrow="存储挂载" title="挂载配置" description="展示 NFS 或其他挂载结构，便于核对路径。">
            <CodeBlock :content="mountText" />
          </PanelCard>

          <PanelCard eyebrow="环境变量" title="环境变量" description="展示传递到容器运行时的环境变量内容。">
            <CodeBlock :content="envText" />
          </PanelCard>

          <PanelCard
            v-if="deployment.source_type === 'image'"
            eyebrow="命令工作台"
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
            eyebrow="状态补充"
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
const inferenceVariableNames = computed(() => deployment.value?.inference_config?.variable_names || [])
const appOrigin = computed(() => {
  if (typeof window === 'undefined') return ''
  return window.location.origin.replace(/\/$/, '')
})
const accessEntryUrl = computed(() => {
  if (!deployment.value?.access_path) return ''
  return `${appOrigin.value}${deployment.value.access_path}`
})
const showDeployAction = computed(() => deployment.value?.status !== 'running' && deployment.value?.status !== 'deploying')
const resourcesText = computed(() => JSON.stringify(deployment.value?.resources || {}, null, 2))
const mountText = computed(() => JSON.stringify(deployment.value?.mount_config || {}, null, 2))
const envText = computed(() => JSON.stringify(deployment.value?.env_vars || {}, null, 2))
const deploymentApiBaseUrl = computed(() => {
  if (!deployment.value?.id) return ''
  return `${appOrigin.value}/api/v1/deployments/${deployment.value.id}`
})
const apiEndpoints = computed(() => {
  if (!deploymentApiBaseUrl.value) return []
  return [
    {
      method: 'POST',
      path: '/run-inference',
      url: `${deploymentApiBaseUrl.value}/run-inference`,
      description: '启动一次命令工作台任务'
    },
    {
      method: 'GET',
      path: '/inference-result',
      url: `${deploymentApiBaseUrl.value}/inference-result`,
      description: '查询最近一次运行结果和运行中状态'
    },
    {
      method: 'GET',
      path: '/inference-previews',
      url: `${deploymentApiBaseUrl.value}/inference-previews`,
      description: '批量获取结果图片预览'
    },
    {
      method: 'GET',
      path: '/inference-files/{file_key}/preview',
      url: `${deploymentApiBaseUrl.value}/inference-files/{file_key}/preview`,
      description: '预览单个结果文件'
    },
    {
      method: 'GET',
      path: '/inference-files/{file_key}/download',
      url: `${deploymentApiBaseUrl.value}/inference-files/{file_key}/download`,
      description: '下载单个结果文件'
    },
    {
      method: 'GET',
      path: '/inference-files/download-all',
      url: `${deploymentApiBaseUrl.value}/inference-files/download-all`,
      description: '打包下载全部结果文件'
    }
  ]
})
const apiExampleVariables = computed(() => {
  const names = inferenceVariableNames.value.length ? inferenceVariableNames.value : ['prompt']
  return names.reduce((variables, name) => {
    variables[name] = name === 'prompt' ? '你的输入内容' : `请填写 ${name}`
    return variables
  }, {})
})
const apiRequestExampleText = computed(() => JSON.stringify({
  variables: apiExampleVariables.value
}, null, 2))
const runInferenceCurl = computed(() => ([
  `curl -X POST '${deploymentApiBaseUrl.value}/run-inference' \\`,
  `  -H 'Content-Type: application/json' \\`,
  `  -d '${apiRequestExampleText.value}'`
]).join('\n'))
const queryResultCurl = computed(() => `curl '${deploymentApiBaseUrl.value}/inference-result?view=readable'`)
const downloadAllCurl = computed(() => ([
  `curl -L '${deploymentApiBaseUrl.value}/inference-files/download-all' \\`,
  `  -o '${deployment.value?.name || 'deployment'}-results.zip'`
]).join('\n'))

const copyText = async (text) => {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.setAttribute('readonly', '')
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    ElMessage.success('已复制到剪贴板')
  }
}

const copyEndpoint = () => {
  copyText(deployment.value?.endpoint)
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
  const target = router.resolve(deployment.value.access_path)
  window.open(target.href, '_blank', 'noopener')
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

.api-section-heading {
  margin-top: 18px;
}

.api-endpoint-main code {
  min-width: 0;
  overflow-wrap: anywhere;
  font-family: var(--ui-font-mono);
}

.api-endpoint-list {
  display: grid;
  gap: 10px;
}

.api-endpoint-item {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--ui-border);
  border-radius: 8px;
  background: #fff;
}

.api-endpoint-main,
.api-endpoint-meta {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 10px;
  align-items: center;
}

.api-endpoint-meta {
  grid-template-columns: minmax(0, 1fr) auto;
  color: var(--ui-text-soft);
  font-size: 13px;
}

.api-curl-tabs {
  margin-top: 4px;
}

.scale-content {
  padding: 12px 0 4px;
}

.scale-content p {
  margin: 0 0 14px;
}
</style>
