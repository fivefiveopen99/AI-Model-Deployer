<template>
  <section class="page-hero">
    <div class="page-hero__copy">
      <span v-if="eyebrow" class="page-hero__eyebrow">{{ eyebrow }}</span>
      <h1>{{ title }}</h1>
      <p v-if="description" class="page-hero__description">{{ description }}</p>
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
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 28px 30px;
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(34, 104, 255, 0.14), transparent 28%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(249, 251, 255, 0.92));
  border: 1px solid rgba(151, 168, 197, 0.2);
  box-shadow: var(--ui-shadow-md);
  overflow: hidden;
}

.page-hero::after {
  content: "";
  position: absolute;
  inset: auto 24px 0 auto;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(34, 104, 255, 0.08), transparent 72%);
  pointer-events: none;
}

.page-hero__copy {
  position: relative;
  z-index: 1;
  max-width: 760px;
}

.page-hero__eyebrow {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(34, 104, 255, 0.08);
  color: var(--ui-brand);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.page-hero__copy h1 {
  margin: 14px 0 0;
  font-family: var(--ui-font-display);
  font-size: 34px;
  line-height: 1.08;
  letter-spacing: -0.03em;
  color: var(--ui-text);
}

.page-hero__description {
  max-width: 640px;
  margin: 12px 0 0;
  font-size: 14px;
  line-height: 1.75;
  color: var(--ui-text-soft);
}

.page-hero__meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 18px;
}

.page-hero__actions {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

@media (max-width: 900px) {
  .page-hero {
    flex-direction: column;
    align-items: flex-start;
    padding: 22px 20px;
    border-radius: 20px;
  }

  .page-hero__actions {
    width: 100%;
    justify-content: flex-start;
  }
}

@media (max-width: 720px) {
  .page-hero__copy h1 {
    font-size: 28px;
  }

  .page-hero__actions :deep(.el-button) {
    flex: 1 1 auto;
  }
}
</style>
