<script setup lang="ts">
import { ref, watch } from "vue";
import { NAlert, NCollapse, NCollapseItem, NEmpty, NSpace, NSpin, NTag, NText } from "naive-ui";

import { useDocumentHistory } from "../composables/useDocumentHistory";

const {
  items,
  loading,
  error,
  expandedId,
  expandedDetail,
  detailLoading,
  refresh,
  loadDetail,
  clearDetail,
} = useDocumentHistory();

const expandedNames = ref<Array<string | number>>([]);

watch(expandedNames, (names) => {
  const id = names[0];
  if (typeof id === "string") {
    void loadDetail(id);
  } else {
    clearDetail();
  }
});

defineExpose({ refresh });

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}
</script>

<template>
  <n-space vertical>
    <n-spin v-if="loading && items.length === 0" size="small" />
    <n-alert v-else-if="error" type="error" :title="error" />
    <n-empty v-else-if="items.length === 0" description="No completed summaries yet" />
    <n-collapse v-else v-model:expanded-names="expandedNames" accordion>
      <n-collapse-item v-for="item in items" :key="item.id" :name="item.id" :title="item.filename">
        <template #header-extra>
          <n-space align="center" :size="8">
            <n-text depth="3">{{ formatDate(item.uploaded_at) }}</n-text>
            <n-tag size="small" type="success" round>{{ item.status }}</n-tag>
          </n-space>
        </template>
        <n-spin v-if="detailLoading && expandedId === item.id" size="small" />
        <n-text
          v-else-if="expandedDetail?.id === item.id && expandedDetail.summary"
          style="white-space: pre-wrap"
        >
          {{ expandedDetail.summary }}
        </n-text>
        <n-text v-else-if="item.summary_preview" depth="3" style="white-space: pre-wrap">
          {{ item.summary_preview }}
        </n-text>
      </n-collapse-item>
    </n-collapse>
  </n-space>
</template>
