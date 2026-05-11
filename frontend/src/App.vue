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
  --app-bg: #f4f1eb;
  --app-bg-deep: #ebe6de;
  --app-bg-muted: #ddd7ce;
  --app-surface: rgba(255, 255, 255, 0.62);
  --app-surface-strong: rgba(255, 255, 255, 0.78);
  --app-surface-soft: rgba(255, 255, 255, 0.48);
  --app-surface-contrast: rgba(24, 32, 42, 0.74);
  --app-border: rgba(92, 103, 116, 0.14);
  --app-border-muted: rgba(92, 103, 116, 0.08);
  --app-text: #18202a;
  --app-text-secondary: #617080;
  --app-text-tertiary: #8b97a5;
  --app-shadow: 0 28px 80px rgba(37, 45, 57, 0.09);
  --app-shadow-soft: 0 16px 38px rgba(37, 45, 57, 0.07);
  --app-shadow-strong: 0 28px 72px rgba(37, 45, 57, 0.16);
  --app-primary: #2f5b83;
  --app-primary-strong: #224463;
  --app-primary-soft: rgba(47, 91, 131, 0.12);
  --app-primary-tint: rgba(95, 133, 170, 0.22);
  --app-success-soft: rgba(46, 133, 101, 0.12);
  --app-warning-soft: rgba(178, 130, 61, 0.12);
  --app-danger-soft: rgba(183, 95, 82, 0.1);
  --app-radius-xl: 26px;
  --app-radius-lg: 20px;
  --app-radius-md: 14px;
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
    radial-gradient(circle at top left, rgba(255, 255, 255, 0.8), transparent 22%),
    radial-gradient(circle at 85% 12%, rgba(93, 129, 164, 0.16), transparent 26%),
    radial-gradient(circle at 70% 78%, rgba(210, 223, 235, 0.5), transparent 26%),
    linear-gradient(180deg, #fbf8f3 0%, #f4f1eb 42%, #ece8e0 100%);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 10% 18%, rgba(255, 255, 255, 0.86), transparent 26%),
    radial-gradient(circle at 84% 24%, rgba(91, 122, 153, 0.14), transparent 20%),
    radial-gradient(circle at 72% 84%, rgba(191, 204, 217, 0.42), transparent 26%);
  filter: blur(48px);
  opacity: 0.9;
}

body::after {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(rgba(255, 255, 255, 0.24), rgba(255, 255, 255, 0.04)),
    linear-gradient(90deg, rgba(24, 32, 42, 0.012) 1px, transparent 1px),
    linear-gradient(rgba(24, 32, 42, 0.012) 1px, transparent 1px);
  background-size: auto, 72px 72px, 72px 72px;
  mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 0.45), transparent 86%);
  opacity: 0.46;
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
  filter: blur(110px);
  opacity: 0.48;
  animation: ambientFloat 18s cubic-bezier(0.37, 0, 0.2, 1) infinite;
}

.orb-a {
  top: -130px;
  left: -120px;
  width: 420px;
  height: 420px;
  background: rgba(255, 255, 255, 0.84);
}

.orb-b {
  top: 12%;
  right: -140px;
  width: 420px;
  height: 420px;
  background: rgba(72, 104, 138, 0.18);
  animation-delay: -5s;
}

.orb-c {
  bottom: -180px;
  left: 18%;
  width: 520px;
  height: 520px;
  background: rgba(193, 205, 217, 0.34);
  animation-delay: -9s;
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(94, 108, 122, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(94, 108, 122, 0.03) 1px, transparent 1px);
  background-size: 54px 54px;
  mask-image: radial-gradient(circle at top, rgba(0, 0, 0, 0.26), transparent 76%);
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

.dashboard > *,
.models-page > *,
.deployments-page > *,
.model-detail-page > *,
.deployment-detail-page > *,
.model-playground-page > * {
  animation: sectionRise 0.56s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.dashboard > *:nth-child(2),
.models-page > *:nth-child(2),
.deployments-page > *:nth-child(2),
.model-detail-page > *:nth-child(2),
.deployment-detail-page > *:nth-child(2),
.model-playground-page > *:nth-child(2) {
  animation-delay: 0.03s;
}

.dashboard > *:nth-child(3) {
  animation-delay: 0.06s;
}

.el-card,
.el-dialog,
.el-message-box,
.el-drawer {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.66), rgba(255, 255, 255, 0.52)) !important;
  border: 1px solid var(--app-border) !important;
  box-shadow: var(--app-shadow) !important;
  backdrop-filter: blur(26px) saturate(145%);
  -webkit-backdrop-filter: blur(26px) saturate(145%);
}

.el-card {
  border-radius: var(--app-radius-xl) !important;
  overflow: hidden;
  transition:
    transform 0.45s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.45s cubic-bezier(0.22, 1, 0.36, 1),
    border-color 0.28s ease,
    background-color 0.28s ease;
}

.el-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--app-shadow-strong) !important;
  border-color: rgba(92, 103, 116, 0.18) !important;
}

.el-card__header,
.el-card__body,
.el-dialog__header,
.el-dialog__body,
.el-dialog__footer {
  background: transparent !important;
}

.el-card__header {
  border-bottom-color: rgba(92, 103, 116, 0.12) !important;
}

.el-dialog {
  border-radius: calc(var(--app-radius-xl) + 2px) !important;
}

.el-overlay {
  background: rgba(244, 241, 235, 0.42) !important;
  backdrop-filter: blur(18px) saturate(130%);
  -webkit-backdrop-filter: blur(18px) saturate(130%);
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
    transform 0.42s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.42s cubic-bezier(0.22, 1, 0.36, 1),
    background-color 0.42s ease,
    border-color 0.42s ease;
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
  background: rgba(255, 255, 255, 0.68) !important;
  border-color: rgba(92, 103, 116, 0.08) !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.92), 0 12px 24px rgba(37, 45, 57, 0.04);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.el-input__wrapper,
.el-select__wrapper,
.el-textarea__inner,
.el-upload-dragger,
.el-pagination button,
.el-pager li {
  border-radius: 12px;
}

.el-button {
  border-radius: 12px !important;
  transition:
    transform 0.28s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.28s cubic-bezier(0.22, 1, 0.36, 1),
    filter 0.28s ease,
    background-color 0.28s ease !important;
}

.el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 24px rgba(37, 45, 57, 0.09);
}

.el-button:active {
  transform: translateY(0);
}

.el-button--primary {
  background: linear-gradient(180deg, #3b688f 0%, #2f5b83 100%) !important;
  border-color: transparent !important;
}

.el-button--success {
  background: linear-gradient(180deg, #2f8f6f 0%, #287b60 100%) !important;
  border-color: transparent !important;
}

.el-button--default {
  background: rgba(255, 255, 255, 0.72) !important;
  border-color: rgba(92, 103, 116, 0.12) !important;
  color: var(--app-text) !important;
}

.el-table,
.el-descriptions__body {
  border-radius: 18px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.56) !important;
  backdrop-filter: blur(22px) saturate(138%);
  -webkit-backdrop-filter: blur(22px) saturate(138%);
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
  letter-spacing: 0.01em;
}

.el-table .el-table__row {
  transition:
    transform 0.35s cubic-bezier(0.22, 1, 0.36, 1),
    background-color 0.35s ease;
}

.el-table .el-table__row:hover > td.el-table__cell {
  background: rgba(47, 91, 131, 0.04) !important;
}

.el-table .el-table__row:hover {
  transform: translateX(4px);
}

.el-descriptions__label {
  color: var(--app-text-secondary);
}

.el-upload-dragger:hover,
.el-input__wrapper:hover,
.el-select__wrapper:hover,
.el-textarea__inner:hover {
  box-shadow: 0 18px 30px rgba(37, 45, 57, 0.08);
  border-color: rgba(47, 91, 131, 0.18) !important;
}

.el-page-header {
  padding: 14px 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(92, 103, 116, 0.1);
  box-shadow: var(--app-shadow-soft);
  backdrop-filter: blur(18px) saturate(138%);
  -webkit-backdrop-filter: blur(18px) saturate(138%);
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
  background: rgba(250, 248, 244, 0.74) !important;
  border: 1px solid rgba(92, 103, 116, 0.08);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(14px) saturate(130%);
  -webkit-backdrop-filter: blur(14px) saturate(130%);
}

.el-tag {
  border-radius: 999px;
  font-weight: 600;
  padding-left: 10px;
  padding-right: 10px;
}

.el-tag--info {
  background: rgba(97, 112, 128, 0.1) !important;
  color: #516070 !important;
  border-color: transparent !important;
}

.el-tag--success {
  background: var(--app-success-soft) !important;
  color: #266b53 !important;
  border-color: transparent !important;
}

.el-tag--warning {
  background: var(--app-warning-soft) !important;
  color: #8e6931 !important;
  border-color: transparent !important;
}

.el-tag--danger {
  background: var(--app-danger-soft) !important;
  color: #9d5348 !important;
  border-color: transparent !important;
}

@keyframes ambientFloat {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1) rotate(0deg);
  }
  40% {
    transform: translate3d(0, 22px, 0) scale(1.06) rotate(6deg);
  }
  65% {
    transform: translate3d(-14px, 8px, 0) scale(0.98) rotate(-4deg);
  }
}

@keyframes sectionRise {
  from {
    opacity: 0;
    transform: translateY(14px) scale(0.988);
    filter: blur(10px);
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
