const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) throw new Error('Failed to fetch health');
  return res.json();
}

export async function fetchSettings() {
  const res = await fetch(`${API_BASE_URL}/settings`);
  if (!res.ok) throw new Error('Failed to fetch settings');
  return res.json();
}

export async function searchWeb(query: string) {
  const res = await fetch(`${API_BASE_URL}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error('Failed to search');
  return res.json();
}

export async function collectItem(item_id: string) {
  const res = await fetch(`${API_BASE_URL}/items/collect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ item_id }),
  });
  if (!res.ok) throw new Error('Failed to collect item');
  return res.json();
}

export async function runExcelJob(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE_URL}/jobs/excel`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error('Failed to run excel job');
  return res.json();
}

export async function fetchItems(limit: number = 50, offset: number = 0) {
  const res = await fetch(`${API_BASE_URL}/items?limit=${limit}&offset=${offset}`);
  if (!res.ok) throw new Error('Failed to fetch items');
  return res.json();
}

export function getExportUrl() {
  return `${API_BASE_URL}/export/latest`;
}

export async function fetchJobs() {
  const res = await fetch(`${API_BASE_URL}/jobs`);
  if (!res.ok) throw new Error('Failed to fetch jobs');
  return res.json();
}

export async function fetchJob(job_id: string) {
  const res = await fetch(`${API_BASE_URL}/jobs/${job_id}`);
  if (!res.ok) throw new Error('Failed to fetch job');
  return res.json();
}

export function getJobExportUrl(job_id: string) {
  return `${API_BASE_URL}/jobs/${job_id}/export`;
}
