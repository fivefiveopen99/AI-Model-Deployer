<template>
  <el-card class="panel-card">
    <template v-if="title || description || eyebrow || $slots.actions || $slots.header" #header>
      <slot name="header">
        <div class="panel-card__header">
          <div class="panel-card__copy">
            <span v-if="eyebrow" class="panel-card__eyebrow">{{ eyebrow }}</span>
            <h2 v-if="title">{{ title }}</h2>
          </div>
          <div v-if="$slots.actions" class="panel-card__actions">
            <slot name="actions" />
          </div>
        </div>
      </slot>
    </template>
    <slot />
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
.panel-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.panel-card__copy {
  min-width: 0;
}

.panel-card__eyebrow {
  display: inline-block;
  margin-bottom: 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: none;
  color: var(--ui-text-faint);
}

.panel-card__copy h2 {
  margin: 0;
  font-family: var(--ui-font-display);
  font-size: 22px;
  letter-spacing: 0;
  line-height: 1.2;
}

.panel-card__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

@media (max-width: 900px) {
  .panel-card__header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
