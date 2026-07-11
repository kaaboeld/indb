<script setup lang="ts">
import { ref } from "vue";

const props = defineProps<{ text: string }>();
const copied = ref(false);

async function copy() {
  if (!props.text.trim()) return;
  await navigator.clipboard.writeText(props.text);
  copied.value = true;
  setTimeout(() => {
    copied.value = false;
  }, 1500);
}
</script>

<template>
  <div class="panel flex flex-col min-h-[200px]">
    <div class="panel-header">
      <span class="text-xs uppercase tracking-widest text-indb-muted">Output</span>
      <button type="button" class="btn-ghost text-xs py-1 px-3" @click="copy">
        {{ copied ? "Copied" : "Copy log" }}
      </button>
    </div>
    <pre class="log-panel flex-1 m-4 mt-0 whitespace-pre-wrap break-words">{{ text || "—" }}</pre>
  </div>
</template>
