<template>
  <el-card class="panel-card">
    <template v-if="title || description || eyebrow || $slots.actions || $slots.header" #header>
      <slot name="header">
        <div class="panel-card__header">
          <div class="panel-card__copy">
            <span v-if="eyebrow" class="panel-card__eyebrow">{{ eyebrow }}</span>
            <h2 v-if="title">{{ title }}</h2>
            <p v-if="description">{{ description }}</p>
          </div>
          <div v-if="$slots.actions" class="panel-card__actions">
            <slot name="actions" />
          </div>
        </div>
      </slot>
    </template>
    <div class="panel-card__body">
      <slot />
    </div>
  </el-card>
</template>

<script setup>
defineProps({
  eyebrow: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    default: ''
  },
  description: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.panel-card {
  border-radius: 22px !important;
}

.panel-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.panel-card__copy {
  min-width: 0;
}

.panel-card__eyebrow {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  margin-bottom: 10px;
  padding: 0 10px;
  border-radius: 999px;
  background: var(--ui-brand-soft);
  color: var(--ui-brand);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.panel-card__copy h2 {
  margin: 0;
  font-family: var(--ui-font-display);
  font-size: 20px;
  letter-spacing: -0.02em;
  line-height: 1.25;
  color: var(--ui-text);
}

.panel-card__copy p {
  max-width: 680px;
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--ui-text-soft);
}

.panel-card__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.panel-card__body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

@media (max-width: 900px) {
  .panel-card__header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
