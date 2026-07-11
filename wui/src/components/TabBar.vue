<script setup lang="ts">
import type { TabId } from "../types";

defineProps<{
  active: TabId;
}>();

const emit = defineEmits<{ change: [TabId] }>();

const tabs: { id: TabId; label: string; icon: string }[] = [
  { id: "control", label: "Control", icon: "◉" },
  { id: "events", label: "Events", icon: "≡" },
  { id: "modules", label: "Modules", icon: "⬡" },
  { id: "cluster", label: "Cluster", icon: "◎" },
  { id: "query", label: "Query", icon: "⌁" },
  { id: "analytics", label: "Analytics", icon: "◈" },
];
</script>

<template>
  <nav class="flex flex-wrap gap-1">
    <button
      v-for="tab in tabs"
      :key="tab.id"
      type="button"
      :class="active === tab.id ? 'tab-btn-active' : 'tab-btn'"
      @click="emit('change', tab.id)"
    >
      <span class="font-mono text-indb-red">{{ tab.icon }}</span>
      {{ tab.label }}
    </button>
  </nav>
</template>
