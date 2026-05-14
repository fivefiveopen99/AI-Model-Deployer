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
  padding: 18px 20px;
  border-radius: 18px;
  border: 1px solid var(--ui-border);
  background: linear-gradient(180deg, rgba(249, 250, 253, 0.98), rgba(244, 247, 251, 0.96));
  color: var(--ui-text);
  font-family: var(--ui-font-mono);
  font-size: 12px;
  line-height: 1.6;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.code-block--terminal {
  border-color: rgba(18, 24, 37, 0.08);
  background: linear-gradient(180deg, #121826, #1a2435);
  color: #dde7f5;
}
</style>
