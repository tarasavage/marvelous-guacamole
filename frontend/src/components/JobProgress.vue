<script setup lang="ts">
import { computed } from "vue";
import { NAlert, NProgress, NSpace, NSpin, NText } from "naive-ui";

import type { JobResponse } from "../types/api";

const props = defineProps<{
  job: JobResponse | null;
  pollError: string | null;
  isPolling: boolean;
}>();

const displayError = computed(() => props.pollError ?? props.job?.error ?? null);

const progressPercent = computed(() => {
  if (!props.job) {
    return 0;
  }

  const { status, progress } = props.job;
  if (status === "completed") {
    return 100;
  }
  if (status === "summarizing") {
    return 95;
  }
  if (status === "extracting" && progress.total_batches > 0) {
    return Math.round((progress.current_batch / progress.total_batches) * 100);
  }
  if (status === "queued" || status === "pending") {
    return 5;
  }
  return 0;
});

const progressLabel = computed(() => {
  if (!props.job) {
    return "";
  }

  const { status, stage, progress } = props.job;
  if (status === "extracting" && progress.total_batches > 0) {
    return `${stage} (batch ${progress.current_batch}/${progress.total_batches})`;
  }
  return stage;
});

const showProgress = computed(
  () => props.job !== null && props.job.status !== "completed" && props.job.status !== "failed",
);
</script>

<template>
  <n-space v-if="job || pollError" vertical>
    <n-spin v-if="isPolling && !job" size="small" />
    <template v-else-if="job">
      <n-text strong>{{ progressLabel }}</n-text>
      <n-progress
        v-if="showProgress"
        type="line"
        :percentage="progressPercent"
        :processing="job.status === 'summarizing'"
        :show-indicator="true"
      />
      <n-alert v-if="job.status === 'completed'" type="success" title="Summary ready" />
    </template>
    <n-alert v-if="displayError" type="error" :title="displayError" />
  </n-space>
</template>
