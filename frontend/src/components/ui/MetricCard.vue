<template>
  <article class="metric-card" :class="`metric-card--${tone}`">
    <div class="metric-card__icon" v-if="$slots.icon">
      <slot name="icon" />
    </div>
    <div class="metric-card__content">
      <span class="metric-card__label">{{ label }}</span>
      <strong class="metric-card__value value-strong">{{ value }}</strong>
      <p v-if="hint" class="metric-card__hint">{{ hint }}</p>
    </div>
  </article>
</template>

<script setup>
defineProps({
  label: {
    type: String,
    required: true
  },
  value: {
    type: [String, Number],
    required: true
  },
  hint: {
    type: String,
    default: ''
  },
  tone: {
    type: String,
    default: 'default'
  }
})
</script>

<style scoped>
.metric-card {
  position: relative;
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr);
  gap: 14px;
  min-height: 96px;
  padding: 14px;
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 251, 255, 0.98));
  border: 1px solid var(--ui-border);
  box-shadow: none;
  overflow: hidden;
}

.metric-card::after {
  display: none;
}

.metric-card__icon {
  position: relative;
  z-index: 1;
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--ui-brand-soft);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.metric-card__content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-card__label {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: none;
  color: var(--ui-text-faint);
}

.metric-card__value {
  font-size: 26px;
  line-height: 1;
  color: var(--ui-text);
}

.metric-card__hint {
  display: none;
}

.metric-card--brand .metric-card__icon {
  color: var(--ui-brand);
  background: #e2efff;
}

.metric-card--success .metric-card__icon {
  color: #1162c4;
  background: #e7f1ff;
}

.metric-card--warning .metric-card__icon {
  color: #315fba;
  background: #edf4ff;
}

.metric-card--danger .metric-card__icon {
  color: var(--ui-danger);
  background: rgba(160, 70, 55, 0.12);
}

.metric-card--default .metric-card__icon {
  color: var(--ui-brand-strong);
  background: #f1f6ff;
}
</style>
