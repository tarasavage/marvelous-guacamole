<script setup lang="ts">
import { ref, watch } from "vue";
import { NCard, NLayout, NLayoutContent, NLayoutHeader, NSpace, NText } from "naive-ui";

import BackendStatus from "./components/BackendStatus.vue";
import DocumentHistory from "./components/DocumentHistory.vue";
import JobProgress from "./components/JobProgress.vue";
import PdfUpload from "./components/PdfUpload.vue";
import { useJobPolling } from "./composables/useJobPolling";

const activeJobId = ref<string | null>(null);
const historyRef = ref<InstanceType<typeof DocumentHistory> | null>(null);

const { job, pollError, isPolling, isCompleted } = useJobPolling(activeJobId);

function onUploaded(jobId: string) {
  activeJobId.value = jobId;
}

watch(isCompleted, (completed) => {
  if (completed) {
    historyRef.value?.refresh();
  }
});
</script>

<template>
  <n-layout style="min-height: 100vh">
    <n-layout-header bordered style="padding: 16px 24px">
      <n-space align="center" justify="space-between">
        <n-text strong style="font-size: 1.25rem">PDF Summary AI</n-text>
        <BackendStatus />
      </n-space>
    </n-layout-header>
    <n-layout-content style="padding: 24px; max-width: 720px; margin: 0 auto">
      <n-space vertical size="large">
        <n-card title="Upload PDF">
          <n-space vertical>
            <PdfUpload @uploaded="onUploaded" />
            <JobProgress :job="job" :poll-error="pollError" :is-polling="isPolling" />
          </n-space>
        </n-card>
        <n-card title="Recent summaries">
          <DocumentHistory ref="historyRef" />
        </n-card>
      </n-space>
    </n-layout-content>
  </n-layout>
</template>
