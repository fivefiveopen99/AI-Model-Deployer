<template>
  <div class="layout-shell" :class="{ 'layout-shell--standalone': hideSidebar }">
    <aside v-if="!hideSidebar" class="layout-sidebar">
      <div class="sidebar-brand">
        <div class="sidebar-brand__mark">
          <svg viewBox="0 0 124 76" aria-hidden="true" class="sidebar-brand__logo">
            <rect x="2" y="2" width="120" height="72" rx="24" fill="#1d6fd7" />
            <circle cx="34" cy="38" r="19" fill="none" stroke="#ffffff" stroke-width="5" />
            <path
              d="M97 24a19 19 0 1 0 .2 28.2"
              fill="none"
              stroke="#ffffff"
              stroke-width="5"
              stroke-linecap="round"
            />
            <path
              d="M77 38h28"
              fill="none"
              stroke="#ffffff"
              stroke-width="5"
              stroke-linecap="round"
            />
          </svg>
        </div>
        <div class="sidebar-brand__copy">
          <strong>OG-MAP</strong>
          <span class="sidebar-brand__subtitle">模型应用平台</span>
          <span class="sidebar-brand__subtitle sidebar-brand__subtitle--cn">奥工模型应用平台</span>
        </div>
      </div>

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
      </el-menu>
    </aside>

    <div class="layout-main">
      <header class="layout-topbar">
        <div class="layout-topbar__left">
          <el-button v-if="!hideSidebar" class="mobile-nav-button" circle @click="mobileDrawerVisible = true">
            <el-icon><Operation /></el-icon>
          </el-button>
          <div class="layout-topbar__copy">
            <div class="layout-topbar__title">{{ currentMeta.navLabel }}</div>
            <p v-if="currentMeta.navDescription" class="layout-topbar__description">
              {{ currentMeta.navDescription }}
            </p>
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
      v-if="!hideSidebar"
      v-model="mobileDrawerVisible"
      direction="ltr"
      size="288px"
      class="mobile-drawer"
    >
      <template #header>
        <div class="mobile-drawer__header">
          <strong>OG-MAP</strong>
          <span class="mobile-drawer__subtitle">模型应用平台</span>
          <span class="mobile-drawer__subtitle mobile-drawer__subtitle--cn">奥工模型应用平台</span>
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
  { path: '/images', label: '镜像仓库', icon: 'Collection' },
  { path: '/deployments', label: '部署管理', icon: 'Ship' }
]

const currentMeta = computed(() => ({
  navLabel: route.meta?.navLabel || '控制台',
  navDescription: route.meta?.navDescription || ''
}))
const hideSidebar = computed(() => Boolean(route.meta?.hideSidebar))

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
  grid-template-columns: 198px minmax(0, 1fr);
  gap: 20px;
  height: 100vh;
  padding: 16px;
  overflow: hidden;
}

.layout-shell--standalone {
  grid-template-columns: minmax(0, 1fr);
}

.layout-sidebar {
  display: flex;
  flex-direction: column;
  gap: 18px;
  height: calc(100vh - 32px);
  padding: 18px 14px;
  border-radius: 24px;
  background: var(--ui-sidebar);
  border: 1px solid rgba(151, 168, 197, 0.22);
  box-shadow: var(--ui-shadow-sm);
  overflow: hidden;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 4px 14px;
  border-bottom: 1px solid rgba(151, 168, 197, 0.22);
}

.sidebar-brand__mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 38px;
  flex: 0 0 60px;
}

.sidebar-brand__logo {
  display: block;
  width: 60px;
  height: 38px;
}

.sidebar-brand__copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
  align-items: flex-start;
  text-align: left;
}

.sidebar-brand__copy strong {
  font-size: 19px;
  line-height: 1.05;
  letter-spacing: -0.02em;
  color: var(--ui-text);
}

.sidebar-brand__subtitle {
  display: block;
  max-width: 100%;
  font-size: 10px;
  letter-spacing: 0;
  color: var(--ui-text-faint);
  line-height: 1.3;
  white-space: nowrap;
}

.sidebar-brand__subtitle--cn {
  letter-spacing: 0;
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
  height: 48px;
  min-height: 48px;
  line-height: 1;
  margin-bottom: 8px;
  padding: 0 14px !important;
  border-radius: 14px;
  color: var(--ui-text-soft);
  font-weight: 600;
}

.sidebar-menu :deep(.el-menu-item .el-icon) {
  margin: 0;
  justify-self: center;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: rgba(34, 104, 255, 0.06);
  color: var(--ui-text);
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: var(--ui-sidebar-strong);
  color: var(--ui-brand-strong);
  box-shadow: inset 0 0 0 1px rgba(34, 104, 255, 0.08);
}

.sidebar-menu__label {
  display: block;
  min-width: 0;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.layout-main {
  min-width: 0;
  height: calc(100vh - 32px);
  display: flex;
  flex-direction: column;
  gap: 18px;
  overflow: hidden;
}

.layout-topbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  min-height: 72px;
  padding: 6px 6px 0;
  gap: 16px;
}

.layout-topbar__left,
.layout-topbar__right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.layout-topbar__copy {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.layout-topbar__title {
  margin-top: 0;
  font-family: var(--ui-font-display);
  font-size: 28px;
  line-height: 1.05;
  letter-spacing: -0.03em;
}

.layout-topbar__description {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--ui-text-soft);
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
  box-shadow: 0 0 0 3px rgba(20, 120, 93, 0.12);
}

.mobile-drawer__header {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.mobile-drawer__subtitle {
  display: block;
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
