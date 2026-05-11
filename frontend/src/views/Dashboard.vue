<template>
  <div class="dashboard">
    <section class="dashboard-hero">
      <div class="hero-copy">
        <span class="hero-eyebrow">Control Center</span>
        <h1>模型构建、分发与部署总览</h1>
        <p>在一个面板内查看模型资产、在线服务和 Kubernetes 连通状态，重点信息保持前置。</p>
      </div>
      <div class="hero-actions">
        <el-button type="primary" @click="$router.push('/models')">
          <el-icon><Plus /></el-icon>
          添加模型
        </el-button>
        <el-button type="success" @click="$router.push('/deployments')">
          <el-icon><Ship /></el-icon>
          创建部署
        </el-button>
        <el-button @click="refreshStatus">
          <el-icon><Refresh /></el-icon>
          刷新状态
        </el-button>
      </div>
    </section>

    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon blue">
            <el-icon :size="40"><Box /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ systemStore.status.total_models }}</div>
            <div class="stat-label">总模型数</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon green">
            <el-icon :size="40"><Ship /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ systemStore.status.total_deployments }}</div>
            <div class="stat-label">总部署数</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon orange">
            <el-icon :size="40"><VideoPlay /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ systemStore.status.running_deployments }}</div>
            <div class="stat-label">运行中</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon purple">
            <el-icon :size="40"><CircleCheck /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ readyModelsCount }}</div>
            <div class="stat-label">就绪模型</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="mt-20">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>系统状态</span>
            </div>
          </template>
          <div class="status-list">
            <div class="status-item">
              <span class="status-label">Kubernetes 连接</span>
              <el-tag :type="systemStore.isK8sConnected ? 'success' : 'danger'">
                {{ systemStore.isK8sConnected ? '已连接' : '未连接' }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>快速操作</span>
            </div>
          </template>
          <div class="quick-actions">
            <el-button type="primary" @click="$router.push('/models')">
              <el-icon><Plus /></el-icon>
              添加模型
            </el-button>
            <el-button type="success" @click="$router.push('/deployments')">
              <el-icon><Ship /></el-icon>
              创建部署
            </el-button>
            <el-button @click="refreshStatus">
              <el-icon><Refresh /></el-icon>
              刷新状态
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="mt-20">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近模型</span>
              <el-button text @click="$router.push('/models')">查看全部</el-button>
            </div>
          </template>
          <el-table :data="modelsStore.models.slice(0, 5)" v-loading="modelsStore.loading">
            <el-table-column prop="name" label="模型名称" />
            <el-table-column prop="model_type" label="类型" />
            <el-table-column prop="status" label="状态">
              <template #default="{ row }">
                <el-tag :type="getModelStatusType(row.status)">
                  {{ getModelStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useSystemStore } from '@/stores/system'
import { useModelsStore } from '@/stores/models'
import { formatDate, getModelStatusText, getModelStatusType } from '@/utils/formatters'

const systemStore = useSystemStore()
const modelsStore = useModelsStore()

const readyModelsCount = computed(() => {
  return modelsStore.models.filter(m => m.status === 'ready').length
})

const refreshStatus = () => {
  systemStore.fetchStatus()
  modelsStore.fetchModels()
}

onMounted(() => {
  systemStore.fetchStatus()
  modelsStore.fetchModels()
})
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.dashboard-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 20px;
  margin-bottom: 18px;
  padding: 4px 2px 0;
}

.hero-copy {
  max-width: 640px;
}

.hero-eyebrow {
  display: inline-block;
  margin-bottom: 12px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--app-text-tertiary);
}

.hero-copy h1 {
  margin: 0;
  font-size: 34px;
  line-height: 1.08;
  letter-spacing: -0.045em;
  color: var(--app-text);
}

.hero-copy p {
  margin-top: 10px;
  max-width: 580px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--app-text-secondary);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 16px;
  min-height: 156px;
  position: relative;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.24), transparent 45%);
}

.stat-card::after {
  content: "";
  position: absolute;
  inset: auto -36px -62px auto;
  width: 140px;
  height: 140px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.34);
  filter: blur(20px);
}

.stat-card::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.18), transparent 58%);
  pointer-events: none;
}

.stat-icon {
  width: 80px;
  height: 80px;
  border-radius: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20px;
  box-shadow: 0 22px 34px rgba(37, 45, 57, 0.14);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  animation: floatIcon 8s cubic-bezier(0.37, 0, 0.2, 1) infinite;
}

.stat-icon.blue {
  background: linear-gradient(135deg, rgba(47, 91, 131, 0.16), rgba(188, 207, 223, 0.4));
  color: #2f5b83;
}

.stat-icon.green {
  background: linear-gradient(135deg, rgba(47, 143, 111, 0.16), rgba(203, 232, 221, 0.4));
  color: #287b60;
}

.stat-icon.orange {
  background: linear-gradient(135deg, rgba(178, 130, 61, 0.18), rgba(239, 222, 193, 0.38));
  color: #8e6931;
}

.stat-icon.purple {
  background: linear-gradient(135deg, rgba(85, 112, 138, 0.16), rgba(207, 218, 228, 0.38));
  color: #4f6680;
}

.stat-info {
  flex: 1;
  position: relative;
  z-index: 1;
}

.stat-value {
  font-size: 34px;
  font-weight: 700;
  color: var(--app-text);
  line-height: 1.1;
  letter-spacing: -0.03em;
}

.stat-label {
  font-size: 14px;
  color: var(--app-text-secondary);
  margin-top: 8px;
}

.mt-20 {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 0;
  border-bottom: 1px solid rgba(92, 103, 116, 0.12);
}

.status-item:last-child {
  border-bottom: none;
}

.status-label {
  font-size: 14px;
  color: #4d5d6e;
}

.quick-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

/* 使系统状态和快速操作卡片高度一致 */
.el-col-12 .el-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.el-col-12 .el-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

@keyframes floatIcon {
  0%,
  100% {
    transform: translateY(0) rotate(0deg);
  }
  45% {
    transform: translateY(-6px) rotate(2deg);
  }
  70% {
    transform: translateY(2px) rotate(-1deg);
  }
}

@media (max-width: 980px) {
  .dashboard-hero {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 760px) {
  .hero-copy h1 {
    font-size: 30px;
  }
}
</style>
