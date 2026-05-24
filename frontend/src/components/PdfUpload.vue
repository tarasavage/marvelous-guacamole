<script setup lang="ts">
import { ref } from "vue";
import type { UploadCustomRequestOptions } from "naive-ui";
import { NAlert, NSpace, NText, NUpload, NUploadDragger } from "naive-ui";

import { uploadDocument } from "../api/documents";
import { ApiError } from "../api/client";
import { MAX_FILE_SIZE_BYTES, PDF_MAGIC } from "../constants/limits";

const emit = defineEmits<{
  uploaded: [jobId: string];
}>();

const uploadError = ref<string | null>(null);
const uploading = ref(false);

async function validateFile(file: File): Promise<string | null> {
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return "PDF exceeds maximum size of 50 MB";
  }

  const isPdfMime =
    file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!isPdfMime) {
    return "File must be a PDF";
  }

  const header = await file.slice(0, 4).text();
  if (!header.startsWith(PDF_MAGIC)) {
    return "File is not a valid PDF";
  }

  return null;
}

async function customRequest({ file, onFinish, onError }: UploadCustomRequestOptions) {
  uploadError.value = null;
  const rawFile = file.file;
  if (!rawFile) {
    onError();
    return;
  }

  const validationError = await validateFile(rawFile);
  if (validationError) {
    uploadError.value = validationError;
    onError();
    return;
  }

  uploading.value = true;
  try {
    const response = await uploadDocument(rawFile);
    emit("uploaded", response.job_id);
    onFinish();
  } catch (error) {
    uploadError.value = error instanceof ApiError ? error.message : "Upload failed";
    onError();
  } finally {
    uploading.value = false;
  }
}
</script>

<template>
  <n-space vertical>
    <n-upload
      :custom-request="customRequest"
      :disabled="uploading"
      :max="1"
      accept=".pdf,application/pdf"
      :show-file-list="false"
    >
      <n-upload-dragger>
        <n-text depth="3">
          {{ uploading ? "Uploading…" : "Drag & drop a PDF here, or click to browse" }}
        </n-text>
      </n-upload-dragger>
    </n-upload>
    <n-alert v-if="uploadError" type="error" :title="uploadError" />
  </n-space>
</template>
