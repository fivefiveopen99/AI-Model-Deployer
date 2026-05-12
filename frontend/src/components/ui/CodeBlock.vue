<template>
  <pre class="code-block" :class="{ 'code-block--terminal': terminal }">{{ content }}</pre>
</template>

<script setup>
defineProps({
  content: {
    type: String,
    default: ''
  },
  terminal: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.code-block {
  margin: 0;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid var(--ui-border);
  background: rgba(248, 249, 245, 0.94);
  color: var(--ui-text);
  font-family: var(--ui-font-mono);
  font-size: 12px;
  line-height: 1.6;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.code-block--terminal {
  border-color: rgba(29, 44, 53, 0.12);
  background: #172028;
  color: #dce8f0;
}
</style>
