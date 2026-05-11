<template>
  <el-container class="layout-container">
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <div class="logo-mark">
          <el-icon :size="30"><Cpu /></el-icon>
        </div>
        <div class="logo-copy">
          <strong>AI Model Deployer</strong>
          <span>Model build and serving</span>
        </div>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/">
          <el-icon><Odometer /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/models">
          <el-icon><Box /></el-icon>
          <span>模型管理</span>
        </el-menu-item>
        <el-menu-item index="/deployments">
          <el-icon><Ship /></el-icon>
          <span>部署管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <breadcrumb />
        </div>
        <div class="header-right">
          <el-tag :type="k8sStatus.type" size="large" round class="status-pill">
            <span class="status-dot"></span>
            <el-icon><Cloudy /></el-icon>
            K8s {{ k8sStatus.text }}
          </el-tag>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="route-float" mode="out-in">
            <div :key="$route.fullPath" class="route-view-shell">
              <component :is="Component" />
            </div>
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useSystemStore } from '@/stores/system'

const systemStore = useSystemStore()
let statusTimer = null

const k8sStatus = computed(() => ({
  type: systemStore.isK8sConnected ? 'success' : 'danger',
  text: systemStore.isK8sConnected ? '已连接' : '未连接'
}))

onMounted(() => {
  systemStore.fetchStatus()
  statusTimer = setInterval(() => {
    systemStore.fetchStatus()
  }, 30000)
})

onUnmounted(() => {
  if (statusTimer) {
    clearInterval(statusTimer)
  }
})
</script>

<style scoped>
.layout-container {
  min-height: 100vh;
  position: relative;
}

.sidebar {
  margin: 18px 0 18px 18px;
  width: 248px !important;
  border-radius: 20px;
  background:
    linear-gradient(180deg, rgba(15, 23, 42, 0.78) 0%, rgba(30, 41, 59, 0.62) 100%);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.16);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.24);
  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);
  overflow: hidden;
}

.logo {
  min-height: 88px;
  display: flex;
  align-items: center;
  padding: 20px 22px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  gap: 14px;
}

.logo-mark {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.92), rgba(14, 165, 233, 0.68));
  box-shadow: 0 18px 32px rgba(37, 99, 235, 0.28);
  color: #eff6ff;
}

.logo-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.logo-copy strong {
  font-size: 17px;
  font-weight: 700;
  color: #f8fafc;
  letter-spacing: 0.01em;
}

.logo-copy span {
  font-size: 12px;
  color: rgba(226, 232, 240, 0.72);
}

.sidebar-menu {
  border-right: none;
  background: transparent;
  padding: 14px 12px;
}

.sidebar-menu :deep(.el-menu) {
  border-right: none;
  background: transparent;
}

.sidebar-menu :deep(.el-menu-item) {
  height: 48px;
  margin-bottom: 8px;
  border-radius: 12px;
  color: rgba(226, 232, 240, 0.82);
  transition:
    transform 0.2s cubic-bezier(0.22, 1, 0.36, 1),
    background-color 0.2s ease,
    color 0.2s ease,
    box-shadow 0.2s ease;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  transform: translateX(4px);
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.26), rgba(96, 165, 250, 0.14));
  color: #f8fbff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.14), 0 14px 26px rgba(37, 99, 235, 0.18);
}

.sidebar-menu :deep(.el-menu-item .el-icon) {
  color: inherit;
}

.header {
  margin: 18px 18px 0 20px;
  height: 76px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.46);
  border: 1px solid rgba(255, 255, 255, 0.72);
  box-shadow: 0 18px 44px rgba(86, 108, 140, 0.14);
  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.header-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 14px;
  min-height: 38px;
  border: none;
  box-shadow: 0 12px 24px rgba(59, 130, 246, 0.16);
  border-radius: 999px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: currentColor;
  box-shadow: 0 0 0 6px rgba(255, 255, 255, 0.22);
}

.main-content {
  background: transparent;
  padding: 24px 18px 18px 20px;
  overflow-y: auto;
}

.route-view-shell {
  min-height: 100%;
}

.route-float-enter-active,
.route-float-leave-active {
  transition:
    opacity 0.18s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.18s cubic-bezier(0.22, 1, 0.36, 1),
    filter 0.18s ease;
}

.route-float-enter-from,
.route-float-leave-to {
  opacity: 0;
  transform: translateY(6px) scale(0.997);
  filter: blur(2px);
}

@media (max-width: 1100px) {
  .sidebar {
    width: 220px !important;
    margin-right: 0;
  }

  .header {
    margin-left: 16px;
    margin-right: 16px;
  }

  .main-content {
    padding-left: 16px;
    padding-right: 16px;
  }
}

@media (max-width: 820px) {
  .layout-container {
    display: block;
  }

  .sidebar {
    width: auto !important;
    margin: 14px;
  }

  .header {
    margin: 0 14px 14px;
    height: auto;
    min-height: 72px;
    flex-wrap: wrap;
    gap: 10px;
    padding: 16px 18px;
  }

  .main-content {
    padding: 0 14px 14px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .sidebar-menu :deep(.el-menu-item),
  .route-float-enter-active,
  .route-float-leave-active {
    transition: none;
  }
}
</style>
