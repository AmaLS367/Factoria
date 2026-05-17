const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchHealth() {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) throw new Error("Failed to fetch health");
  return res.json();
}

export async function fetchSettings() {
  const res = await fetch(`${API_BASE_URL}/settings`);
  if (!res.ok) throw new Error("Failed to fetch settings");
  return res.json();
}

export async function searchWeb(query: string) {
  const res = await fetch(`${API_BASE_URL}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error("Failed to search");
  return res.json();
}

export async function collectItem(item_id: string) {
  const res = await fetch(`${API_BASE_URL}/items/collect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item_id }),
  });
  if (!res.ok) throw new Error("Failed to collect item");
  return res.json();
}

export async function previewFile(file: File, sheetName?: string) {
  const formData = new FormData();
  formData.append("file", file);
  const url = sheetName
    ? `${API_BASE_URL}/jobs/excel/preview?sheet_name=${encodeURIComponent(sheetName)}`
    : `${API_BASE_URL}/jobs/excel/preview`;
  const res = await fetch(url, { method: "POST", body: formData });
  if (!res.ok) throw new Error("Failed to preview file");
  return res.json();
}

export async function runExcelJob(
  file: File,
  sheetName?: string,
  columnName?: string,
) {
  const formData = new FormData();
  formData.append("file", file);
  if (sheetName) formData.append("sheet_name", sheetName);
  if (columnName) formData.append("column_name", columnName);
  const res = await fetch(`${API_BASE_URL}/jobs/excel`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Failed to run excel job");
  return res.json();
}

export async function cancelJob(jobId: string) {
  const res = await fetch(`${API_BASE_URL}/jobs/${jobId}/cancel`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to cancel job");
  return res.json();
}

export async function retryJob(jobId: string) {
  const res = await fetch(`${API_BASE_URL}/jobs/${jobId}/retry`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to retry job");
  return res.json();
}

export async function fetchItems(limit: number = 50, offset: number = 0) {
  const res = await fetch(
    `${API_BASE_URL}/items?limit=${limit}&offset=${offset}`,
  );
  if (!res.ok) throw new Error("Failed to fetch items");
  return res.json();
}

export function getExportUrl() {
  return `${API_BASE_URL}/export/latest`;
}

export async function fetchJobs() {
  const res = await fetch(`${API_BASE_URL}/jobs`);
  if (!res.ok) throw new Error("Failed to fetch jobs");
  return res.json();
}

export async function fetchJob(job_id: string) {
  const res = await fetch(`${API_BASE_URL}/jobs/${job_id}`);
  if (!res.ok) throw new Error("Failed to fetch job");
  return res.json();
}

export function getJobExportUrl(job_id: string) {
  return `${API_BASE_URL}/jobs/${job_id}/export`;
}

export async function fetchItemSources(identifierValue: string) {
  const res = await fetch(
    `${API_BASE_URL}/items/${encodeURIComponent(identifierValue)}/sources`,
  );
  if (!res.ok) throw new Error("Failed to fetch sources");
  return res.json();
}

export async function fetchLogs(lines: number = 200, level: string = "") {
  const params = new URLSearchParams({ lines: String(lines) });
  if (level) params.set("level", level);
  const res = await fetch(`${API_BASE_URL}/logs?${params}`);
  if (!res.ok) throw new Error("Failed to fetch logs");
  return res.json();
}

import type { ItemField } from "./types";

export async function fetchItemFields(
  identifierValue: string,
): Promise<ItemField[]> {
  const res = await fetch(
    `${API_BASE_URL}/items/${encodeURIComponent(identifierValue)}/fields`,
  );
  if (!res.ok) throw new Error("Failed to fetch fields");
  return res.json();
}
