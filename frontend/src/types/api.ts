export interface UploadResponse {
  job_id: string;
  document_id: string;
}

export interface Progress {
  current_batch: number;
  total_batches: number;
  pages_processed: number;
  total_pages: number;
}

export interface JobResponse {
  status: string;
  stage: string;
  progress: Progress;
  error?: string | null;
}

export interface DocumentSummaryItem {
  id: string;
  filename: string;
  uploaded_at: string;
  status: string;
  summary_preview?: string | null;
}

export interface DocumentListResponse {
  items: DocumentSummaryItem[];
}

export interface DocumentDetailResponse {
  id: string;
  filename: string;
  uploaded_at: string;
  completed_at?: string | null;
  status: string;
  stage: string;
  summary?: string | null;
  error_message?: string | null;
  progress: Progress;
}
