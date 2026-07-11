<script setup lang="ts">
defineProps<{
  modelValue: string;
  class?: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
  change: [];
}>();

function onChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value;
  emit("update:modelValue", value);
  emit("change");
}
</script>

<template>
  <div class="select-field" :class="class">
    <span class="select-field-arrow" aria-hidden="true">▾</span>
    <select class="select" :value="modelValue" @change="onChange">
      <slot />
    </select>
  </div>
</template>
