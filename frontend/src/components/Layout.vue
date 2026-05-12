<template>
  <div class="layout-shell">
    <aside class="layout-sidebar">
      <div class="sidebar-brand">
        <div class="sidebar-brand__mark">
          <el-icon :size="24"><Cpu /></el-icon>
        </div>
        <div class="sidebar-brand__copy">
          <strong>AI Model Deployer</strong>
          <span>模型构建、镜像仓库与集群部署</span>
        </div>
      </div>

      <div class="sidebar-caption">功能导航</div>

      <el-menu
        :default-active="$route.path"
        router
        class="sidebar-menu"
      >
        <el-menu-item
          v-for="item in navItems"
          :key="item.path"
          :index="item.path"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span class="sidebar-menu__label">{{ item.label }}</span>
        </el-menu-item>
        <el-menu-item index="/images">
          <el-icon><Collection /></el-icon>
          <span>镜像管理</span>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-status">
        <div class="sidebar-status__card">
          <span class="sidebar-status__label">集群状态</span>
          <strong>{{ systemStore.isK8sConnected ? '已连接' : '未连接' }}</strong>
          <small>{{ systemStore.isK8sConnected ? 'Kubernetes 已连接' : '等待 Kubernetes' }}</small>
        </div>
        <div class="sidebar-status__pair">
          <span class="badge-pill">模型 {{ systemStore.status.total_models || 0 }}</span>
          <span class="badge-pill">运行 {{ systemStore.status.running_deployments || 0 }}</span>
        </div>
      </div>
    </aside>

    <div class="layout-main">
      <header class="layout-topbar">
        <div class="layout-topbar__left">
          <el-button class="mobile-nav-button" circle @click="mobileDrawerVisible = true">
            <el-icon><Operation /></el-icon>
          </el-button>
          <div>
            <span class="layout-topbar__eyebrow">当前页面</span>
            <div class="layout-topbar__title">{{ currentMeta.navLabel }}</div>
          </div>
        </div>
        <div class="layout-topbar__right">
          <span class="badge-pill">
            <span class="status-dot" :class="{ 'is-online': systemStore.isK8sConnected }"></span>
            K8s {{ systemStore.isK8sConnected ? '在线' : '离线' }}
          </span>
        </div>
      </header>

      <main class="layout-content">
        <router-view v-slot="{ Component }">
          <transition name="layout-fade" mode="out-in">
            <section :key="$route.fullPath" class="layout-route-shell">
              <component :is="Component" />
            </section>
          </transition>
        </router-view>
      </main>
    </div>

    <el-drawer
      v-model="mobileDrawerVisible"
      direction="ltr"
      size="288px"
      class="mobile-drawer"
    >
      <template #header>
        <div class="mobile-drawer__header">
          <strong>AI Model Deployer</strong>
          <span>功能导航</span>
        </div>
      </template>
      <div class="mobile-drawer__body">
        <el-menu
          :default-active="$route.path"
          router
          class="sidebar-menu sidebar-menu--mobile"
          @select="mobileDrawerVisible = false"
        >
          <el-menu-item
            v-for="item in navItems"
            :key="item.path"
            :index="item.path"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span class="sidebar-menu__label">{{ item.label }}</span>
          </el-menu-item>
        </el-menu>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useSystemStore } from '@/stores/system'

const route = useRoute()
const systemStore = useSystemStore()
const mobileDrawerVisible = ref(false)

const navItems = [
  { path: '/', label: '总览', icon: 'Odometer' },
  { path: '/models', label: '模型管理', icon: 'Box' },
  { path: '/deployments', label: '部署管理', icon: 'Ship' },
  { path: '/images', label: '镜像仓库', icon: 'Collection' }
]

const currentMeta = computed(() => ({
  navLabel: route.meta?.navLabel || '控制台',
  navDescription: route.meta?.navDescription || ''
}))

watch(() => route.fullPath, () => {
  mobileDrawerVisible.value = false
})

onMounted(() => {
  systemStore.fetchStatus().catch(() => {})
})
</script>

<style scoped>
.layout-shell {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 288px minmax(0, 1fr);
  gap: 16px;
  height: 100vh;
  padding: 14px;
  overflow: hidden;
}

.layout-sidebar {
  display: flex;
  flex-direction: column;
  gap: 14px;
  height: calc(100vh - 28px);
  padding: 14px;
  border-radius: 8px;
  background: var(--ui-sidebar);
  border: 1px solid rgba(67, 79, 84, 0.12);
  box-shadow: none;
  overflow: hidden;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 14px;
  padding-bottom: 18px;
  border-bottom: 1px solid rgba(67, 79, 84, 0.1);
}

.sidebar-brand__mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 8px;
  background: var(--ui-brand);
  color: #fff;
  box-shadow: none;
}

.sidebar-brand__copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sidebar-brand__copy strong {
  font-size: 18px;
  color: var(--ui-text);
}

.sidebar-brand__copy span {
  font-size: 12px;
  color: var(--ui-text-faint);
  line-height: 1.5;
}

.sidebar-caption,
.layout-topbar__eyebrow {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: none;
  color: var(--ui-text-faint);
}

.sidebar-menu {
  border-right: 0;
  background: transparent;
}

.sidebar-menu :deep(.el-menu) {
  border-right: 0;
  background: transparent;
}

.sidebar-menu :deep(.el-menu-item) {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  align-items: center;
  height: 44px;
  min-height: 44px;
  line-height: 1;
  margin-bottom: 8px;
  padding: 0 12px !important;
  border-radius: 6px;
  color: var(--ui-text-soft);
}

.sidebar-menu :deep(.el-menu-item .el-icon) {
  margin: 0;
  justify-self: center;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.62);
  color: var(--ui-text);
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: var(--ui-sidebar-strong);
  color: var(--ui-brand-strong);
  box-shadow: none;
}

.sidebar-menu__label {
  display: block;
  min-width: 0;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-status {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sidebar-status__card {
  padding: 16px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid rgba(67, 79, 84, 0.1);
  box-shadow: none;
}

.sidebar-status__label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: none;
  color: var(--ui-text-faint);
}

.sidebar-status__card strong {
  display: block;
  margin-top: 10px;
  font-family: var(--ui-font-display);
  font-size: 26px;
  letter-spacing: 0;
}

.sidebar-status__card small {
  display: block;
  margin-top: 6px;
  color: var(--ui-text-soft);
}

.sidebar-status__pair {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.layout-main {
  min-width: 0;
  height: calc(100vh - 28px);
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
}

.layout-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 64px;
  padding: 0 8px 0 6px;
  gap: 12px;
}

.layout-topbar__left,
.layout-topbar__right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.layout-topbar__title {
  margin-top: 6px;
  font-family: var(--ui-font-display);
  font-size: 24px;
  line-height: 1;
  letter-spacing: 0;
}

.layout-content {
  min-width: 0;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0 2px 18px 0;
}

.layout-route-shell {
  min-height: 0;
}

.mobile-nav-button {
  display: none;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(115, 128, 134, 0.42);
}

.status-dot.is-online {
  background: var(--ui-success);
  box-shadow: none;
}

.mobile-drawer__header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mobile-drawer__header span {
  font-size: 12px;
  color: var(--ui-text-faint);
}

.mobile-drawer__body {
  padding-top: 8px;
}

.layout-fade-enter-active,
.layout-fade-leave-active {
  transition: opacity 0.14s ease-out, transform 0.14s ease-out;
}

.layout-fade-enter-from,
.layout-fade-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

@media (max-width: 1060px) {
  .layout-shell {
    grid-template-columns: 1fr;
    padding: 14px;
  }

  .layout-sidebar {
    display: none;
  }

  .mobile-nav-button {
    display: inline-flex;
  }

  .layout-topbar {
    padding: 4px 2px;
  }
}

@media (max-width: 720px) {
  .layout-topbar {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
