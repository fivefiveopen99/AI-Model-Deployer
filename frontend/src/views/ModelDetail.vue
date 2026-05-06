<template>
  <div class="model-detail-page">
    <el-page-header @back="$router.back()" title="模型详情" />
    
    <el-card v-if="model" class="detail-card">
      <template #header>
        <div class="card-header">
          <span>{{ model.name }}</span>
          <el-tag :type="getModelStatusType(model.status)">
            {{ getModelStatusText(model.status) }}
          </el-tag>
        </div>
      </template>
      
      <el-descriptions :column="2" border>
        <el-descriptions-item label="ID">{{ model.id }}</el-descriptions-item>
        <el-descriptions-item label="模型类型">
          <el-tag>{{ model.model_type }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="来源类型">
          <el-tag type="info">{{ model.source_type }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(model.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatDate(model.updated_at) }}</el-descriptions-item>
        <el-descriptions-item label="Docker镜像">
          <span v-if="model.docker_image">
            {{ model.docker_image }}:{{ model.docker_image_tag }}
          </span>
          <span v-else class="text-gray">未构建</span>
        </el-descriptions-item>
      </el-descriptions>
      
      <el-divider />
      
      <div class="section">
        <h4>描述</h4>
        <p>{{ model.description || '暂无描述' }}</p>
      </div>
      
      <div class="section">
        <h4>模型路径</h4>
        <el-input v-model="model.source_path" readonly />
      </div>
      
      <div class="section">
        <h4>配置信息</h4>
        <pre class="config-code">{{ JSON.stringify(model.config, null, 2) }}</pre>
      </div>
      
      <div class="section" v-if="model.status_message">
        <h4>状态信息</h4>
        <el-alert :title="model.status_message" :type="model.status === 'failed' ? 'error' : 'info'" />
      </div>
      
      <div class="actions">
        <el-button type="primary" @click="showBuildDialog" :disabled="model.status === 'building'">
          <el-icon><Refresh /></el-icon>
          重新构建
        </el-button>
        <el-button @click="$router.push('/deployments')">
          <el-icon><Ship /></el-icon>
          创建部署
        </el-button>
      </div>
    </el-card>
    
    <el-skeleton v-else :rows="10" animated />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useModelsStore } from '@/stores/models'
import { formatDate, getModelStatusText, getModelStatusType } from '@/utils/formatters'

const route = useRoute()
const modelsStore = useModelsStore()

const model = ref(null)

const showBuildDialog = () => {
  // 可以扩展为显示构建对话框
  ElMessage.info('构建功能在模型列表页面')
}

onMounted(async () => {
  const id = route.params.id
  try {
    model.value = await modelsStore.fetchModelDetail(id)
  } catch (error) {
    ElMessage.error('获取模型详情失败')
  }
})
</script>

<style scoped>
.model-detail-page {
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

.text-gray {
  color: #909399;
}

.actions {
  margin-top: 30px;
  display: flex;
  gap: 10px;
}
</style>
