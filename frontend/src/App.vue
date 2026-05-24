<script setup lang="ts">
import { NAlert, NCard, NLayout, NLayoutContent, NLayoutHeader, NSpace, NText, NUpload, NUploadDragger } from "naive-ui";

import BackendStatus from "./components/BackendStatus.vue";
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
          <n-upload disabled :show-file-list="false">
            <n-upload-dragger>
              <n-text depth="3">Drag & drop a PDF here (coming soon)</n-text>
            </n-upload-dragger>
          </n-upload>
        </n-card>
        <n-alert type="info" title="Scaffold milestone">
          Docker Compose, backend API, and frontend shell are running. Upload and summarization
          pipeline coming next.
        </n-alert>
      </n-space>
    </n-layout-content>
  </n-layout>
</template>
