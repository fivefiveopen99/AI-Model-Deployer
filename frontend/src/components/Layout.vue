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
  isolation: isolate;
}

.layout-container::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.08), transparent 18%),
    radial-gradient(circle at 0 0, rgba(255, 255, 255, 0.24), transparent 22%);
  opacity: 0.8;
}

.sidebar {
  margin: 18px 0 18px 18px;
  width: 248px !important;
  border-radius: 28px;
  background:
    linear-gradient(180deg, rgba(28, 37, 48, 0.86) 0%, rgba(43, 55, 70, 0.76) 100%);
  color: #f8fafc;
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 28px 56px rgba(24, 32, 42, 0.16);
  backdrop-filter: blur(28px) saturate(132%);
  -webkit-backdrop-filter: blur(28px) saturate(132%);
  overflow: hidden;
  position: relative;
}

.sidebar::after {
  content: "";
  position: absolute;
  inset: auto -40px -80px auto;
  width: 180px;
  height: 180px;
  border-radius: 999px;
  background: rgba(106, 143, 177, 0.18);
  filter: blur(48px);
  pointer-events: none;
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
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #4b7296 0%, #2f5b83 100%);
  box-shadow: 0 16px 30px rgba(47, 91, 131, 0.26);
  color: #fff;
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
  letter-spacing: -0.01em;
}

.logo-copy span {
  font-size: 12px;
  color: rgba(226, 232, 240, 0.74);
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
  height: 50px;
  margin-bottom: 8px;
  border-radius: 14px;
  color: rgba(226, 232, 240, 0.84);
  transition:
    transform 0.32s cubic-bezier(0.22, 1, 0.36, 1),
    background-color 0.32s ease,
    color 0.32s ease,
    box-shadow 0.32s ease;
  font-weight: 500;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  transform: translateX(4px);
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(180deg, rgba(89, 127, 161, 0.28), rgba(89, 127, 161, 0.16));
  color: #fff;
  box-shadow:
    inset 0 0 0 1px rgba(191, 212, 232, 0.12),
    0 14px 24px rgba(24, 32, 42, 0.16);
}

.sidebar-menu :deep(.el-menu-item .el-icon) {
  color: inherit;
}

.header {
  margin: 18px 18px 0 20px;
  height: 76px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.56);
  border: 1px solid rgba(92, 103, 116, 0.12);
  box-shadow: 0 18px 36px rgba(37, 45, 57, 0.07);
  backdrop-filter: blur(28px) saturate(138%);
  -webkit-backdrop-filter: blur(28px) saturate(138%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.header-left {
  min-width: 0;
}

.header-left :deep(.el-breadcrumb__inner),
.header-left :deep(.el-breadcrumb__separator) {
  color: var(--app-text-secondary);
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
  padding: 0 16px;
  min-height: 40px;
  border: 1px solid rgba(92, 103, 116, 0.08);
  box-shadow: 0 10px 20px rgba(37, 45, 57, 0.05);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.54);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: currentColor;
  box-shadow: 0 0 0 7px rgba(255, 255, 255, 0.3);
}

.main-content {
  background: transparent;
  padding: 24px 18px 18px 20px;
  overflow-y: auto;
}

.route-view-shell {
  min-height: 100%;
  animation: routeShellIn 0.6s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.route-float-enter-active,
.route-float-leave-active {
  transition:
    opacity 0.3s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.3s cubic-bezier(0.22, 1, 0.36, 1),
    filter 0.3s ease;
}

.route-float-enter-from,
.route-float-leave-to {
  opacity: 0;
  transform: translateY(14px) scale(0.992);
  filter: blur(8px);
}

@keyframes routeShellIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
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
