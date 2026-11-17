<script setup lang="ts">
defineProps<{ since: Date }>();
</script>

<template>
  <span class="new-badge">New</span>
</template>

<style scoped>
.new-badge { background: var(--color-danger); color: var(--color-surface); border-radius: var(--radius); padding: 0 var(--space-1); }
</style>
