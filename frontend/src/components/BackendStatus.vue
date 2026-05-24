<script setup lang="ts">
import { onMounted, ref } from "vue";
import { NSpin, NTag } from "naive-ui";

type Status = "loading" | "connected" | "error";

const status = ref<Status>("loading");
const detail = ref("");

onMounted(async () => {
  const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

  try {
    const response = await fetch(`${baseUrl}/`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = (await response.json()) as { service?: string; status?: string };
    status.value = "connected";
    detail.value = data.service ?? "backend";
  } catch (error) {
    status.value = "error";
    detail.value = error instanceof Error ? error.message : "Unknown error";
  }
});
</script>

<template>
  <n-spin v-if="status === 'loading'" size="small" />
  <n-tag v-else-if="status === 'connected'" type="success" round>
    Backend connected ({{ detail }})
  </n-tag>
  <n-tag v-else type="error" round>Backend unreachable ({{ detail }})</n-tag>
</template>
