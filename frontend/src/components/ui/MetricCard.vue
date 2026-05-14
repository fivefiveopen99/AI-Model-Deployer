<template>
  <article class="metric-card" :class="`metric-card--${tone}`">
    <span class="metric-card__accent"></span>
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
  grid-template-columns: 56px minmax(0, 1fr);
  gap: 16px;
  min-height: 128px;
  padding: 22px 20px;
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(249, 251, 255, 0.96));
  border: 1px solid var(--ui-border);
  box-shadow: var(--ui-shadow-sm);
  overflow: hidden;
}

.metric-card__accent {
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  border-radius: 999px;
  background: var(--ui-brand);
}

.metric-card__icon {
  position: relative;
  z-index: 1;
  width: 56px;
  height: 56px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--ui-brand-soft);
  color: var(--ui-brand);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.metric-card__content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-card__label {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--ui-text-faint);
}

.metric-card__value {
  font-size: 32px;
  line-height: 1.02;
  color: var(--ui-text);
}

.metric-card__hint {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--ui-text-soft);
}

.metric-card--brand .metric-card__accent {
  background: var(--ui-brand);
}

.metric-card--success .metric-card__accent {
  background: var(--ui-success);
}

.metric-card--warning .metric-card__accent {
  background: var(--ui-warning);
}

.metric-card--danger .metric-card__accent {
  background: var(--ui-danger);
}

.metric-card--success .metric-card__icon {
  color: var(--ui-success);
  background: rgba(47, 160, 107, 0.12);
}

.metric-card--warning .metric-card__icon {
  color: var(--ui-warning);
  background: rgba(242, 156, 74, 0.14);
}

.metric-card--danger .metric-card__icon {
  color: var(--ui-danger);
  background: rgba(225, 86, 86, 0.12);
}

.metric-card--default .metric-card__accent {
  background: #7b8aa6;
}

.metric-card--default .metric-card__icon {
  color: #4b5e7e;
  background: rgba(123, 138, 166, 0.12);
}

@media (max-width: 720px) {
  .metric-card {
    min-height: 116px;
    padding: 18px 16px;
    border-radius: 18px;
  }

  .metric-card__value {
    font-size: 28px;
  }
}
</style>
