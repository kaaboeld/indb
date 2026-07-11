<script setup lang="ts">
defineProps<{
  columns: string[];
  rows: string[][];
  empty?: string;
}>();
</script>

<template>
  <div class="table-shell">
    <table class="data-table">
      <thead>
        <tr>
          <th v-for="col in columns" :key="col">{{ col }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!rows.length">
          <td :colspan="columns.length" class="text-center text-indb-muted py-8">
            {{ empty ?? "No data" }}
          </td>
        </tr>
        <tr v-for="(row, i) in rows" :key="i">
          <td v-for="(cell, j) in row" :key="j">
            <slot :name="`cell-${j}`" :row="row" :cell="cell" :index="i">
              {{ cell }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
