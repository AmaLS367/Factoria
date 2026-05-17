export interface HealthStatus {
  status: string;
  app: string;
  db: string;
}

export interface Settings {
  model_name: string;
  llm_provider: string;
  llm_model: string;
  web_search_enabled: boolean;
  web_search_provider: string;
  input_file: string;
  output_file: string;
  batch_size: number;
  target_fields: string[];
  item_label: string;
}

export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
}

export interface ExcelJobStatus {
  status: string;
  output_path: string;
}

export interface Job {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  created_at: string;
  started_at?: string;
  finished_at?: string;
  total_items: number;
  processed_items: number;
  skipped_items: number;
  failed_items: number;
  error_message?: string;
  input_file: string;
  output_file: string;
  run_id?: number;
  sheet_name?: string;
  column_name?: string;
}

export interface PreviewResult {
  file_type: "xlsx" | "csv";
  sheets: string[];
  columns: string[];
  row_count: number;
  sample_rows: Record<string, unknown>[];
}

export interface ItemSource {
  title: string;
  url: string;
  snippet: string;
  provider: string;
  credibility_score: number | null;
  retrieved_at: string;
}

export interface LogEntry {
  timestamp: string;
  level: string;
  logger: string;
  message: string;
}

export interface LogsResponse {
  entries: LogEntry[];
  total_returned: number;
  file: string;
}

export interface ItemField {
  field_name: string;
  field_value: string;
  confidence: number | null;
}
