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
  --app-bg: #f3f6fb;
  --app-bg-deep: #e6edf7;
  --app-surface: rgba(255, 255, 255, 0.8);
  --app-surface-strong: rgba(255, 255, 255, 0.94);
  --app-surface-soft: rgba(255, 255, 255, 0.72);
  --app-border: rgba(109, 138, 176, 0.12);
  --app-border-muted: rgba(109, 138, 176, 0.16);
  --app-text: #1d1d1f;
  --app-text-secondary: #667085;
  --app-shadow: 0 20px 50px rgba(52, 72, 101, 0.08);
  --app-shadow-soft: 0 10px 26px rgba(52, 72, 101, 0.06);
  --app-primary: #0071e3;
  --app-primary-soft: rgba(0, 113, 227, 0.1);
  --app-success-soft: rgba(52, 199, 89, 0.12);
  --app-warning-soft: rgba(255, 159, 10, 0.12);
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
    radial-gradient(circle at top center, rgba(0, 113, 227, 0.1), transparent 26%),
    radial-gradient(circle at 15% 14%, rgba(255, 255, 255, 0.9), transparent 20%),
    linear-gradient(180deg, #f8fbff 0%, #f3f6fb 44%, #eff4fa 100%);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 15% 18%, rgba(255, 255, 255, 0.9), transparent 24%),
    radial-gradient(circle at 80% 78%, rgba(125, 211, 252, 0.12), transparent 24%);
  filter: blur(28px);
  opacity: 0.92;
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
  filter: blur(84px);
  opacity: 0.45;
  animation: ambientFloat 10.5s ease-in-out infinite;
}

.orb-a {
  top: -120px;
  left: -80px;
  width: 340px;
  height: 340px;
  background: rgba(255, 255, 255, 0.72);
}

.orb-b {
  top: 18%;
  right: -110px;
  width: 320px;
  height: 320px;
  background: rgba(59, 130, 246, 0.14);
  animation-delay: -6s;
}

.orb-c {
  bottom: -140px;
  left: 28%;
  width: 360px;
  height: 360px;
  background: rgba(34, 197, 94, 0.1);
  animation-delay: -11s;
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(116, 139, 173, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(116, 139, 173, 0.03) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 0.22), transparent 82%);
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
  backdrop-filter: blur(18px) saturate(130%);
  -webkit-backdrop-filter: blur(18px) saturate(130%);
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
  transform: translateY(-2px);
  box-shadow: 0 24px 48px rgba(52, 72, 101, 0.1) !important;
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
  background: rgba(245, 245, 247, 0.62) !important;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
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
  background: rgba(255, 255, 255, 0.88) !important;
  border-color: rgba(17, 17, 17, 0.08) !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.92), 0 6px 18px rgba(15, 23, 42, 0.04);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.el-button {
  border-radius: 10px !important;
  transition:
    transform 0.18s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.18s cubic-bezier(0.22, 1, 0.36, 1),
    filter 0.18s ease !important;
}

.el-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.08);
}

.el-button:active {
  transform: translateY(0);
}

.el-button--primary {
  background: linear-gradient(180deg, #0077ed 0%, #0071e3 100%) !important;
  border-color: transparent !important;
}

.el-button--success {
  background: linear-gradient(180deg, #34c759 0%, #2fb451 100%) !important;
  border-color: transparent !important;
}

.el-button--default {
  background: rgba(255, 255, 255, 0.9) !important;
  border-color: rgba(17, 17, 17, 0.08) !important;
  color: var(--app-text) !important;
}

.el-table,
.el-descriptions__body {
  border-radius: 14px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.95) !important;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
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
  font-size: 13px;
}

.el-table .el-table__row {
  transition:
    transform 0.25s ease,
    background-color 0.25s ease;
}

.el-table .el-table__row:hover > td.el-table__cell {
  background: rgba(0, 113, 227, 0.03) !important;
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
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(17, 17, 17, 0.06);
  box-shadow: var(--app-shadow-soft);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
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
  background: rgba(251, 251, 253, 0.96) !important;
  border: 1px solid rgba(17, 17, 17, 0.06);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.el-tag {
  border-radius: 999px;
  font-weight: 600;
}

.el-tag--info {
  background: rgba(120, 120, 128, 0.08) !important;
  color: #4a4a4f !important;
  border-color: transparent !important;
}

.el-tag--success {
  background: rgba(52, 199, 89, 0.1) !important;
  color: #248a3d !important;
  border-color: transparent !important;
}

.el-tag--warning {
  background: rgba(255, 159, 10, 0.12) !important;
  color: #b06800 !important;
  border-color: transparent !important;
}

.el-tag--danger {
  background: rgba(255, 59, 48, 0.1) !important;
  color: #c9342c !important;
  border-color: transparent !important;
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
