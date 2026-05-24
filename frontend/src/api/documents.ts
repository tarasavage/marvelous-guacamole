import { apiFetch } from "./client";
import type {
  DocumentDetailResponse,
  DocumentListResponse,
  JobResponse,
  UploadResponse,
} from "../types/api";

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<UploadResponse>("/api/documents", {
    method: "POST",
    body: formData,
  });
}

export function getJob(jobId: string): Promise<JobResponse> {
  return apiFetch<JobResponse>(`/api/jobs/${jobId}`);
}

export function listDocuments(): Promise<DocumentListResponse> {
  return apiFetch<DocumentListResponse>("/api/documents");
}

export function getDocument(documentId: string): Promise<DocumentDetailResponse> {
  return apiFetch<DocumentDetailResponse>(`/api/documents/${documentId}`);
}
