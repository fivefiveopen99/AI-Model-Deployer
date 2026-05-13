<template>
  <div class="page-shell dashboard-page">
    <PageHero
      title="模型交付控制台"
      description="查看模型、部署和集群状态。"
    >
      <template #meta>
        <span class="badge-pill">模型 {{ systemStore.status.total_models }}</span>
        <span class="badge-pill">部署 {{ systemStore.status.total_deployments }}</span>
        <span class="badge-pill">运行中 {{ systemStore.status.running_deployments }}</span>
      </template>
      <template #actions>
        <el-button @click="refreshStatus">
          <el-icon><Refresh /></el-icon>
          刷新状态
        </el-button>
        <el-button type="primary" @click="router.push('/models')">
          <el-icon><Plus /></el-icon>
          导入模型
        </el-button>
        <el-button type="success" @click="router.push('/deployments')">
          <el-icon><Ship /></el-icon>
          创建部署
        </el-button>
      </template>
    </PageHero>

    <section class="metrics-grid">
      <MetricCard
        label="模型总数"
        :value="systemStore.status.total_models"
        tone="brand"
      >
        <template #icon>
          <el-icon :size="28"><Box /></el-icon>
        </template>
      </MetricCard>
      <MetricCard
        label="部署总数"
        :value="systemStore.status.total_deployments"
        tone="success"
      >
        <template #icon>
          <el-icon :size="28"><Ship /></el-icon>
        </template>
      </MetricCard>
      <MetricCard
        label="运行中"
        :value="systemStore.status.running_deployments"
        tone="warning"
      >
        <template #icon>
          <el-icon :size="28"><VideoPlay /></el-icon>
        </template>
      </MetricCard>
      <MetricCard
        label="可部署模型"
        :value="readyModelsCount"
        tone="default"
      >
        <template #icon>
          <el-icon :size="28"><CircleCheck /></el-icon>
        </template>
      </MetricCard>
    </section>

    <section class="two-column-grid">
      <PanelCard
        title="系统连接状态"
        description=""
      >
        <div class="status-stack">
          <div class="status-row">
            <div>
              <strong>Kubernetes 连接</strong>
              <p>用于创建部署、服务入口和同步运行状态。</p>
            </div>
            <el-tag :type="systemStore.isK8sConnected ? 'success' : 'danger'">
              {{ systemStore.isK8sConnected ? '已连接' : '未连接' }}
            </el-tag>
          </div>
          <div class="status-row">
            <div>
              <strong>当前工作负载</strong>
              <p>运行中的部署会直接影响测试和推理入口可用性。</p>
            </div>
            <span class="badge-pill">{{ systemStore.status.running_deployments }} 个运行中</span>
          </div>
        </div>
      </PanelCard>

      <PanelCard
        title="推荐操作路径"
        description=""
      >
        <div class="action-grid">
          <button class="action-tile" type="button" @click="router.push('/models')">
            <span class="action-tile__icon"><el-icon><Box /></el-icon></span>
            <strong>导入模型项目</strong>
            <p>支持 GitHub、压缩包和直链导入。</p>
          </button>
          <button class="action-tile" type="button" @click="router.push('/images')">
            <span class="action-tile__icon"><el-icon><Collection /></el-icon></span>
            <strong>管理镜像仓库</strong>
            <p>查看镜像、手动构建运行时，或导入镜像包。</p>
          </button>
          <button class="action-tile" type="button" @click="router.push('/deployments')">
            <span class="action-tile__icon"><el-icon><Ship /></el-icon></span>
            <strong>创建并部署服务</strong>
            <p>从可部署模型或镜像生成部署并推送到集群。</p>
          </button>
        </div>
      </PanelCard>
    </section>

    <section class="two-column-grid">
      <PanelCard
        title="最近模型"
        description=""
      >
        <template #actions>
          <el-button text @click="router.push('/models')">查看全部</el-button>
        </template>
        <el-table :data="recentModels" v-loading="modelsStore.loading" class="dashboard-table">
          <el-table-column prop="name" label="模型名称" min-width="180" />
          <el-table-column prop="model_type" label="类型" width="120" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getModelStatusType(row.status)">
                {{ getModelStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <template #empty>
            <EmptyState
              title="还没有模型"
              description="先导入一个模型项目，平台会自动识别结构并生成镜像构建流程。"
            />
          </template>
        </el-table>
      </PanelCard>

      <PanelCard
        title="最近部署"
        description=""
      >
        <template #actions>
          <el-button text @click="router.push('/deployments')">查看全部</el-button>
        </template>
        <el-table :data="recentDeployments" v-loading="deploymentsStore.loading" class="dashboard-table">
          <el-table-column prop="name" label="部署名称" min-width="180" />
          <el-table-column prop="namespace" label="命名空间" width="120" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getDeploymentStatusType(row.status)">
                {{ getDeploymentStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <template #empty>
            <EmptyState
              title="还没有部署"
              description="模型 ready 之后，即可在部署中心创建部署记录并推送到 Kubernetes。"
            />
          </template>
        </el-table>
      </PanelCard>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PageHero from '@/components/ui/PageHero.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import PanelCard from '@/components/ui/PanelCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { useSystemStore } from '@/stores/system'
import { useModelsStore } from '@/stores/models'
import { useDeploymentsStore } from '@/stores/deployments'
import {
  formatDate,
  getDeploymentStatusText,
  getDeploymentStatusType,
  getModelStatusText,
  getModelStatusType
} from '@/utils/formatters'

const router = useRouter()
const systemStore = useSystemStore()
const modelsStore = useModelsStore()
const deploymentsStore = useDeploymentsStore()

const readyModelsCount = computed(() => modelsStore.models.filter((model) => model.status === 'ready').length)
const recentModels = computed(() => modelsStore.models.slice(0, 5))
const recentDeployments = computed(() => deploymentsStore.deployments.slice(0, 5))

const refreshStatus = async () => {
  await Promise.allSettled([
    systemStore.fetchStatus(),
    modelsStore.fetchModels({ limit: 5 }),
    deploymentsStore.fetchDeployments({ limit: 5 })
  ])
}

onMounted(() => {
  refreshStatus()
})
</script>

<style scoped>
.dashboard-page {
  padding: 0 0 6px;
  gap: 12px;
}

.status-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(27, 86, 159, 0.1);
}

.status-row:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}

.status-row strong {
  display: block;
  margin-bottom: 4px;
  font-size: 14px;
}

.status-row p {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--ui-text-soft);
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.action-tile {
  width: 100%;
  padding: 14px;
  border: 1px solid var(--ui-border);
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(242, 247, 255, 0.96));
  text-align: left;
  color: var(--ui-text);
  cursor: pointer;
  box-shadow: none;
  transition: border-color 0.16s ease, background-color 0.16s ease;
}

.action-tile:hover {
  border-color: rgba(42, 115, 209, 0.32);
  background: #fff;
}

.action-tile__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  margin-bottom: 8px;
  border-radius: 6px;
  color: var(--ui-brand);
  background: var(--ui-brand-soft);
}

.action-tile strong {
  display: block;
  font-size: 15px;
}

.action-tile p {
  margin: 6px 0 0;
  color: var(--ui-text-soft);
  font-size: 12px;
  line-height: 1.5;
}

.dashboard-table {
  width: 100%;
}

.dashboard-page :deep(.panel-card .el-card__header) {
  padding: 14px 16px;
}

.dashboard-page :deep(.panel-card .el-card__body) {
  padding: 14px 16px 16px;
}

.dashboard-page :deep(.el-table td.el-table__cell) {
  padding-top: 10px;
  padding-bottom: 10px;
}

@media (max-width: 900px) {
  .action-grid {
    grid-template-columns: 1fr;
  }

  .status-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
