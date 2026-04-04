<template>
  <div :class="panelClass">
    <h4 class="panel-title">{{ title }}</h4>
    <div class="panel-content">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(
  defineProps<{
    title: string;
    variant?: 'prediction' | 'trends' | 'demographics' | 'medication' | 'surge' | 'default';
  }>(),
  { variant: 'default' }
);

const panelClass = computed(() => {
  const base = 'analytics-panel';
  const v = props.variant ? `${props.variant}-panel` : '';
  return v ? `${base} ${v}` : base;
});
</script>

<style scoped>
.analytics-panel {
  background: #ffffff;
  border-radius: 8px;
  padding: 12px 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  margin-bottom: 16px;
}
.panel-title {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 700;
}
.panel-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
@media (max-width: 768px) {
  .analytics-panel { padding: 10px 12px; }
  .panel-title { font-size: 15px; }
}
</style>
