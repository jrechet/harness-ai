<script setup lang="ts">
defineProps<{ label: string; disabled?: boolean }>();
const emit = defineEmits<{ click: [] }>();
</script>

<template>
  <button class="app-button" :disabled="disabled" @click="emit('click')">{{ label }}</button>
</template>

<style scoped>
.app-button { background: var(--color-primary); color: var(--color-surface); border-radius: var(--radius); padding: var(--space-1) var(--space-2); }
</style>
