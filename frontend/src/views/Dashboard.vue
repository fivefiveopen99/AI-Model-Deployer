<template>
  <div class="dashboard">
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

.stat-card {
  display: flex;
  align-items: center;
  padding: 12px;
  min-height: 144px;
  position: relative;
  overflow: hidden;
}

.stat-card::after {
  content: "";
  position: absolute;
  inset: auto -30px -55px auto;
  width: 120px;
  height: 120px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.26);
  filter: blur(14px);
}

.stat-icon {
  width: 80px;
  height: 80px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20px;
  box-shadow: 0 18px 34px rgba(86, 108, 140, 0.16);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  animation: floatIcon 5.5s ease-in-out infinite;
}

.stat-icon.blue {
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.18), rgba(125, 211, 252, 0.34));
  color: #2563eb;
}

.stat-icon.green {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(187, 247, 208, 0.34));
  color: #15803d;
}

.stat-icon.orange {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.18), rgba(253, 230, 138, 0.36));
  color: #d97706;
}

.stat-icon.purple {
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.16), rgba(191, 219, 254, 0.34));
  color: #0369a1;
}

.stat-info {
  flex: 1;
  position: relative;
  z-index: 1;
}

.stat-value {
  font-size: 34px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.1;
  letter-spacing: -0.03em;
}

.stat-label {
  font-size: 14px;
  color: #64748b;
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
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
}

.status-item:last-child {
  border-bottom: none;
}

.status-label {
  font-size: 14px;
  color: #475569;
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
    transform: translateY(0);
  }
  50% {
    transform: translateY(-4px);
  }
}
</style>
