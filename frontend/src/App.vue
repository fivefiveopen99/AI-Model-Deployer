<template>
  <div class="app-shell">
    <div class="app-background" aria-hidden="true">
      <span class="bg-orb orb-a"></span>
      <span class="bg-orb orb-b"></span>
      <span class="bg-orb orb-c"></span>
      <span class="bg-grid"></span>
    </div>
    <router-view />
  </div>
</template>

<script setup>
</script>

<style>
:root {
  color-scheme: light;
  --app-bg: #f4f7fb;
  --app-bg-deep: #dbe6f3;
  --app-surface: rgba(255, 255, 255, 0.62);
  --app-surface-strong: rgba(255, 255, 255, 0.82);
  --app-surface-soft: rgba(255, 255, 255, 0.42);
  --app-border: rgba(255, 255, 255, 0.7);
  --app-border-muted: rgba(125, 151, 184, 0.22);
  --app-text: #1f2a37;
  --app-text-secondary: #5d6b7d;
  --app-shadow: 0 20px 60px rgba(67, 97, 138, 0.14);
  --app-shadow-soft: 0 10px 30px rgba(86, 108, 140, 0.12);
  --app-primary: #2563eb;
  --app-primary-soft: rgba(37, 99, 235, 0.14);
  --app-success-soft: rgba(34, 197, 94, 0.15);
  --app-warning-soft: rgba(245, 158, 11, 0.16);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html,
body,
#app,
.app-shell {
  min-height: 100%;
}

body {
  font-family: "SF Pro Display", "PingFang SC", "Microsoft YaHei", sans-serif;
  color: var(--app-text);
  background:
    radial-gradient(circle at top left, rgba(125, 211, 252, 0.55), transparent 32%),
    radial-gradient(circle at 85% 15%, rgba(59, 130, 246, 0.16), transparent 24%),
    linear-gradient(135deg, #eef4fb 0%, #f8fbff 48%, #edf2f8 100%);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 15% 18%, rgba(255, 255, 255, 0.85), transparent 26%),
    radial-gradient(circle at 78% 82%, rgba(191, 219, 254, 0.56), transparent 24%);
  filter: blur(24px);
  opacity: 0.95;
}

.app-shell {
  position: relative;
  overflow: hidden;
}

.app-background {
  position: fixed;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.bg-orb {
  position: absolute;
  border-radius: 999px;
  filter: blur(70px);
  opacity: 0.62;
  animation: ambientFloat 10.5s ease-in-out infinite;
}

.orb-a {
  top: -120px;
  left: -80px;
  width: 340px;
  height: 340px;
  background: rgba(56, 189, 248, 0.28);
}

.orb-b {
  top: 18%;
  right: -110px;
  width: 320px;
  height: 320px;
  background: rgba(37, 99, 235, 0.18);
  animation-delay: -6s;
}

.orb-c {
  bottom: -140px;
  left: 28%;
  width: 360px;
  height: 360px;
  background: rgba(34, 197, 94, 0.16);
  animation-delay: -11s;
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
  background-size: 32px 32px;
  mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 0.42), transparent 85%);
}

.dashboard,
.models-page,
.deployments-page,
.model-detail-page,
.deployment-detail-page,
.model-playground-page {
  position: relative;
  z-index: 1;
}

.dashboard > .el-row,
.models-page > .el-card,
.deployments-page > .el-card,
.model-detail-page > *,
.deployment-detail-page > *,
.model-playground-page > * {
  animation: sectionRise 0.34s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.dashboard > .el-row:nth-child(2),
.model-detail-page > *:nth-child(2),
.deployment-detail-page > *:nth-child(2),
.model-playground-page > *:nth-child(2) {
  animation-delay: 0.03s;
}

.dashboard > .el-row:nth-child(3) {
  animation-delay: 0.06s;
}

.el-card,
.el-dialog,
.el-message-box,
.el-drawer {
  background: var(--app-surface) !important;
  border: 1px solid var(--app-border) !important;
  box-shadow: var(--app-shadow) !important;
  backdrop-filter: blur(22px) saturate(160%);
  -webkit-backdrop-filter: blur(22px) saturate(160%);
}

.el-card {
  border-radius: 18px !important;
  overflow: hidden;
  transition:
    transform 0.26s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.26s cubic-bezier(0.22, 1, 0.36, 1),
    border-color 0.22s ease;
}

.el-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 26px 64px rgba(67, 97, 138, 0.18) !important;
}

.el-card__header,
.el-card__body,
.el-dialog__header,
.el-dialog__body,
.el-dialog__footer {
  background: transparent !important;
}

.el-card__header {
  border-bottom-color: rgba(148, 163, 184, 0.18) !important;
}

.el-dialog {
  border-radius: 20px !important;
}

.el-overlay {
  background: rgba(130, 146, 166, 0.18) !important;
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.el-input__wrapper,
.el-select__wrapper,
.el-textarea__inner,
.el-upload-dragger,
.el-descriptions,
.el-table,
.el-pagination button,
.el-pager li,
.el-collapse,
.el-collapse-item__header,
.el-collapse-item__wrap,
.el-alert,
.el-tag {
  transition:
    transform 0.35s ease,
    box-shadow 0.35s ease,
    background-color 0.35s ease,
    border-color 0.35s ease;
}

.el-input__wrapper,
.el-select__wrapper,
.el-textarea__inner,
.el-upload-dragger,
.el-pagination button,
.el-pager li,
.el-collapse-item__header,
.el-collapse-item__wrap,
.el-alert {
  background: rgba(255, 255, 255, 0.58) !important;
  border-color: rgba(148, 163, 184, 0.22) !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.4), 0 8px 24px rgba(94, 122, 158, 0.08);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.el-button {
  border-radius: 10px !important;
  transition:
    transform 0.18s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.18s cubic-bezier(0.22, 1, 0.36, 1),
    filter 0.18s ease !important;
}

.el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.16);
}

.el-button:active {
  transform: translateY(0);
}

.el-button--primary {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
  border-color: transparent !important;
}

.el-button--success {
  background: linear-gradient(135deg, #16a34a 0%, #15803d 100%) !important;
  border-color: transparent !important;
}

.el-table,
.el-descriptions__body {
  border-radius: 14px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.4) !important;
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.el-table tr,
.el-table th.el-table__cell,
.el-table td.el-table__cell,
.el-table__inner-wrapper::before,
.el-descriptions__table,
.el-descriptions__cell {
  background: transparent !important;
}

.el-table th.el-table__cell {
  color: var(--app-text);
  font-weight: 600;
}

.el-table .el-table__row {
  transition:
    transform 0.25s ease,
    background-color 0.25s ease;
}

.el-table .el-table__row:hover > td.el-table__cell {
  background: rgba(255, 255, 255, 0.48) !important;
}

.el-table .el-table__row:hover {
  transform: translateX(3px);
}

.el-descriptions__label {
  color: var(--app-text-secondary);
}

.el-upload-dragger:hover,
.el-input__wrapper:hover,
.el-select__wrapper:hover,
.el-textarea__inner:hover {
  box-shadow: 0 12px 28px rgba(86, 108, 140, 0.14);
}

.el-page-header {
  padding: 14px 18px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.52);
  border: 1px solid rgba(255, 255, 255, 0.76);
  box-shadow: var(--app-shadow-soft);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.card-header,
.actions-row,
.quick-actions,
.logs-header,
.endpoint-row,
.result-header {
  gap: 12px;
}

.config-code,
.logs-content,
.result-code {
  background: rgba(240, 245, 252, 0.72) !important;
  border: 1px solid rgba(148, 163, 184, 0.14);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}

@keyframes ambientFloat {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(0, 16px, 0) scale(1.04);
  }
}

@keyframes sectionRise {
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.995);
    filter: blur(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
    filter: blur(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
</style>
