<script setup lang="ts">
defineProps<{
  label: string;
  value: string;
  tone?: "default" | "ok" | "warn" | "err";
}>();

const toneClass: Record<string, string> = {
  default: "text-indb-white",
  ok: "text-emerald-400",
  warn: "text-indb-yellow",
  err: "text-indb-red",
};
</script>

<template>
  <div class="stat-card">
    <span class="stat-label">{{ label }}</span>
    <span class="stat-value" :class="toneClass[tone ?? 'default']">{{ value }}</span>
  </div>
</template>
