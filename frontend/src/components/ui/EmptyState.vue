<template>
  <div class="empty-state">
    <span class="empty-state__badge">当前暂无内容</span>
    <h3>{{ title }}</h3>
    <p>{{ description }}</p>
    <div v-if="$slots.actions" class="empty-state__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({
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
.empty-state__badge {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  background: var(--ui-brand-soft);
  color: var(--ui-brand);
  font-size: 12px;
  font-weight: 700;
}
</style>
