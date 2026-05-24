import { computed, onUnmounted, ref, watch, type Ref } from "vue";

import { getJob } from "../api/documents";
import { ApiError } from "../api/client";
import type { JobResponse } from "../types/api";

const POLL_INTERVAL_MS = 2000;
const TERMINAL_STATUSES = new Set(["completed", "failed"]);

export function useJobPolling(jobId: Ref<string | null>) {
  const job = ref<JobResponse | null>(null);
  const pollError = ref<string | null>(null);
  const isPolling = ref(false);

  let intervalId: ReturnType<typeof setInterval> | null = null;

  function stopPolling() {
    if (intervalId !== null) {
      clearInterval(intervalId);
      intervalId = null;
    }
    isPolling.value = false;
  }

  async function pollOnce(id: string) {
    try {
      job.value = await getJob(id);
      pollError.value = null;

      if (TERMINAL_STATUSES.has(job.value.status)) {
        stopPolling();
      }
    } catch (error) {
      pollError.value = error instanceof ApiError ? error.message : "Failed to poll job status";
      stopPolling();
    }
  }

  function startPolling(id: string) {
    stopPolling();
    isPolling.value = true;
    void pollOnce(id);
    intervalId = setInterval(() => {
      void pollOnce(id);
    }, POLL_INTERVAL_MS);
  }

  watch(
    jobId,
    (id) => {
      job.value = null;
      pollError.value = null;
      if (id) {
        startPolling(id);
      } else {
        stopPolling();
      }
    },
    { immediate: true },
  );

  onUnmounted(stopPolling);

  const isTerminal = computed(() => job.value !== null && TERMINAL_STATUSES.has(job.value.status));
  const isCompleted = computed(() => job.value?.status === "completed");
  const isFailed = computed(() => job.value?.status === "failed" || pollError.value !== null);

  return {
    job,
    pollError,
    isPolling,
    isTerminal,
    isCompleted,
    isFailed,
  };
}
