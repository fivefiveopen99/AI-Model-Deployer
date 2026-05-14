<template>
  <div class="page-shell dashboard-page">
    <PageHero
      eyebrow="平台总览"
      title="模型交付控制台"
      description="集中查看模型资产、部署运行和集群连接情况，并从这里快速进入导入、镜像和部署操作。"
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
        hint="已登记到平台、可继续构建或管理的模型资产数量。"
        tone="brand"
      >
        <template #icon>
          <el-icon :size="28"><Box /></el-icon>
        </template>
      </MetricCard>
      <MetricCard
        label="部署总数"
        :value="systemStore.status.total_deployments"
        hint="当前平台内已创建的全部部署记录。"
        tone="success"
      >
        <template #icon>
          <el-icon :size="28"><Ship /></el-icon>
        </template>
      </MetricCard>
      <MetricCard
        label="运行中"
        :value="systemStore.status.running_deployments"
        hint="已经成功部署并处于运行状态的服务数量。"
        tone="warning"
      >
        <template #icon>
          <el-icon :size="28"><VideoPlay /></el-icon>
        </template>
      </MetricCard>
      <MetricCard
        label="可部署模型"
        :value="readyModelsCount"
        hint="镜像已准备完成，可直接创建部署的模型数量。"
        tone="default"
      >
        <template #icon>
          <el-icon :size="28"><CircleCheck /></el-icon>
        </template>
      </MetricCard>
    </section>

    <section class="two-column-grid">
      <PanelCard
        eyebrow="系统状态"
        title="系统连接状态"
        description="先确认 Kubernetes 连接和当前工作负载，再决定下一步是导入、构建还是直接部署。"
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
        eyebrow="快捷入口"
        title="推荐操作路径"
        description="围绕“导入模型、管理镜像、创建部署”三条高频路径组织入口，减少页面切换成本。"
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
        eyebrow="最近活动"
        title="最近模型"
        description="优先展示最新导入或最近变更的模型，便于快速回到正在处理的资产。"
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
        eyebrow="最近活动"
        title="最近部署"
        description="持续跟踪最近的部署记录和当前运行状态，减少在列表页中翻找。"
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
  padding: 0 0 10px;
  gap: 20px;
}

.status-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 0;
  border-bottom: 1px solid rgba(151, 168, 197, 0.2);
}

.status-row:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}

.status-row strong {
  display: block;
  margin-bottom: 6px;
  font-size: 15px;
  color: var(--ui-text);
}

.status-row p {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--ui-text-soft);
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.action-tile {
  width: 100%;
  padding: 18px;
  border: 1px solid var(--ui-border);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 249, 253, 0.96));
  text-align: left;
  color: var(--ui-text);
  cursor: pointer;
  box-shadow: var(--ui-shadow-sm);
  transition: transform 0.18s ease, border-color 0.16s ease, background-color 0.16s ease, box-shadow 0.16s ease;
}

.action-tile:hover {
  transform: translateY(-2px);
  border-color: rgba(34, 104, 255, 0.22);
  background: #fff;
  box-shadow: var(--ui-shadow-md);
}

.action-tile__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  margin-bottom: 12px;
  border-radius: 14px;
  color: var(--ui-brand);
  background: var(--ui-brand-soft);
}

.action-tile strong {
  display: block;
  font-size: 16px;
  letter-spacing: -0.01em;
}

.action-tile p {
  margin: 8px 0 0;
  color: var(--ui-text-soft);
  font-size: 13px;
  line-height: 1.65;
}

.dashboard-table {
  width: 100%;
}

.dashboard-page :deep(.panel-card .el-card__header) {
  padding: 20px 22px 0;
}

.dashboard-page :deep(.panel-card .el-card__body) {
  padding: 18px 22px 22px;
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
