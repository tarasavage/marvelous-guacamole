import { onMounted, ref } from "vue";

import { getDocument, listDocuments } from "../api/documents";
import { ApiError } from "../api/client";
import type { DocumentDetailResponse, DocumentSummaryItem } from "../types/api";

export function useDocumentHistory() {
  const items = ref<DocumentSummaryItem[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const expandedId = ref<string | null>(null);
  const expandedDetail = ref<DocumentDetailResponse | null>(null);
  const detailLoading = ref(false);

  async function refresh() {
    loading.value = true;
    error.value = null;
    try {
      const response = await listDocuments();
      items.value = response.items;
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : "Failed to load history";
    } finally {
      loading.value = false;
    }
  }

  async function loadDetail(id: string) {
    expandedId.value = id;
    detailLoading.value = true;
    try {
      expandedDetail.value = await getDocument(id);
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : "Failed to load summary";
      expandedId.value = null;
      expandedDetail.value = null;
    } finally {
      detailLoading.value = false;
    }
  }

  function clearDetail() {
    expandedId.value = null;
    expandedDetail.value = null;
  }

  onMounted(refresh);

  return {
    items,
    loading,
    error,
    expandedId,
    expandedDetail,
    detailLoading,
    refresh,
    loadDetail,
    clearDetail,
  };
}
