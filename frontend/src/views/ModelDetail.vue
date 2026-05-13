<template>
  <div class="page-shell model-detail-page">
    <PageHero
      eyebrow="Model Detail"
      :title="model?.name || '模型详情'"
      description="查看模型来源、构建镜像、配置内容和当前状态信息。详情页保持阅读优先，不再沿用默认描述表单布局。"
    >
      <template #meta v-if="model">
        <span class="badge-pill">Type {{ model.model_type || 'custom' }}</span>
        <span class="badge-pill">Source {{ model.source_type }}</span>
        <span class="badge-pill">Status {{ getModelStatusText(model.status) }}</span>
      </template>
      <template #actions>
        <el-button @click="$router.back()">返回</el-button>
        <el-button type="primary" @click="showBuildDialog" :disabled="model?.status === 'building'">
          <el-icon><Refresh /></el-icon>
          重新构建
        </el-button>
        <el-button @click="$router.push('/deployments')">
          <el-icon><Ship /></el-icon>
          创建部署
        </el-button>
      </template>
    </PageHero>

    <template v-if="model">
      <section class="metrics-grid">
        <MetricCard label="Model ID" :value="model.id" hint="平台内部模型主键" tone="brand">
          <template #icon>
            <el-icon :size="28"><Key /></el-icon>
          </template>
        </MetricCard>
        <MetricCard label="Status" :value="getModelStatusText(model.status)" hint="当前模型生命周期状态" tone="success">
          <template #icon>
            <el-icon :size="28"><CircleCheck /></el-icon>
          </template>
        </MetricCard>
        <MetricCard label="Source" :value="model.source_type" hint="导入方式或资产来源" tone="warning">
          <template #icon>
            <el-icon :size="28"><Link /></el-icon>
          </template>
        </MetricCard>
        <MetricCard
          label="Image"
          :value="model.docker_image ? 'Ready' : 'Pending'"
          :hint="dockerImageRef"
          tone="default"
        >
          <template #icon>
            <el-icon :size="28"><Box /></el-icon>
          </template>
        </MetricCard>
      </section>

      <section class="split-detail-layout">
        <div class="content-stack">
          <PanelCard eyebrow="Overview" title="基础信息" description="模型来源、时间线和镜像信息。">
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
              <el-descriptions-item label="Docker 镜像">
                <span class="mono-text">{{ dockerImageRef }}</span>
              </el-descriptions-item>
            </el-descriptions>
          </PanelCard>

          <PanelCard eyebrow="Source" title="模型来源与描述" description="保留原始路径，便于回溯实际资产位置。">
            <div class="field-stack">
              <div>
                <div class="section-heading">描述</div>
                <p class="body-copy">{{ model.description || '暂无描述' }}</p>
              </div>
              <div>
                <div class="section-heading">模型路径</div>
                <el-input v-model="model.source_path" readonly />
              </div>
            </div>
          </PanelCard>
        </div>

        <div class="content-stack">
          <PanelCard eyebrow="Runtime" title="配置信息" description="后端识别出的模型配置和构建相关字段。">
            <CodeBlock :content="configText" />
          </PanelCard>

          <PanelCard
            v-if="model.status_message"
            eyebrow="Status"
            title="状态信息"
            description="构建失败或进行中的补充说明。"
          >
            <el-alert :title="model.status_message" :type="model.status === 'failed' ? 'error' : 'info'" show-icon />
          </PanelCard>
        </div>
      </section>
    </template>

    <el-skeleton v-else :rows="10" animated />
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import PageHero from '@/components/ui/PageHero.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import PanelCard from '@/components/ui/PanelCard.vue'
import CodeBlock from '@/components/ui/CodeBlock.vue'
import { useModelsStore } from '@/stores/models'
import { formatDate, formatImageRef, getModelStatusText } from '@/utils/formatters'

const route = useRoute()
const modelsStore = useModelsStore()
const model = ref(null)

const dockerImageRef = computed(() => {
  if (!model.value?.docker_image) {
    return '未构建'
  }
  return formatImageRef(model.value.docker_image, model.value.docker_image_tag)
})

const configText = computed(() => JSON.stringify(model.value?.config || {}, null, 2))

const showBuildDialog = () => {
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

.body-copy {
  margin: 0;
  line-height: 1.75;
  color: var(--ui-text-soft);
}
</style>
