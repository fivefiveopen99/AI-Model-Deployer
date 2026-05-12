<template>
  <section class="page-hero">
    <div class="page-hero__copy">
      <span v-if="eyebrow" class="page-hero__eyebrow">{{ eyebrow }}</span>
      <h1>{{ title }}</h1>
      <div v-if="$slots.meta" class="page-hero__meta">
        <slot name="meta" />
      </div>
    </div>
    <div v-if="$slots.actions" class="page-hero__actions">
      <slot name="actions" />
    </div>
  </section>
</template>

<script setup>
defineProps({
  eyebrow: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.page-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  padding: 2px 2px 0;
}

.page-hero__copy {
  max-width: 760px;
}

.page-hero__eyebrow {
  display: inline-block;
  margin-bottom: 4px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: none;
  color: var(--ui-text-faint);
}

.page-hero__copy h1 {
  margin: 0;
  font-family: var(--ui-font-display);
  font-size: 30px;
  line-height: 1.15;
  letter-spacing: 0;
  color: var(--ui-text);
}

.page-hero__meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.page-hero__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

@media (max-width: 900px) {
  .page-hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .page-hero__actions {
    width: 100%;
    justify-content: flex-start;
  }
}

@media (max-width: 720px) {
  .page-hero__actions :deep(.el-button) {
    flex: 1 1 auto;
  }
}
</style>
