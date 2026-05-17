import { useRef, useState, useEffect } from 'react';
import { runExcelJob, fetchJob, fetchJobs, getJobExportUrl } from '../api';
import type { Job } from '../types';
import { Card } from './Card';
import { Play, Download, Loader2, Upload, AlertCircle, CheckCircle, Clock } from 'lucide-react';

export function ExcelJob() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadRecentJobs();
  }, []);

  useEffect(() => {
    let intervalId: number;
    if (activeJobId && activeJob?.status !== 'completed' && activeJob?.status !== 'failed') {
      intervalId = window.setInterval(async () => {
        try {
          const job = await fetchJob(activeJobId);
          setActiveJob(job);
          if (job.status === 'completed' || job.status === 'failed') {
            loadRecentJobs();
          }
        } catch (err) {
          console.error("Failed to poll job", err);
        }
      }, 2000);
    }
    return () => clearInterval(intervalId);
  }, [activeJobId, activeJob?.status]);

  const loadRecentJobs = async () => {
    try {
      const jobs = await fetchJobs();
      setRecentJobs(jobs);
    } catch (err) {
      console.error("Failed to load recent jobs", err);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setSelectedFile(file);
    setError(null);
  };

  const handleRunJob = async () => {
    if (!selectedFile) {
      setError('Please select an Excel file first.');
      return;
    }
    setError(null);
    try {
      const data = await runExcelJob(selectedFile);
      setActiveJobId(data.job_id);
      const job = await fetchJob(data.job_id);
      setActiveJob(job);
      loadRecentJobs();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const renderProgressBar = (job: Job) => {
    if (!job.total_items) return null;
    const processed = job.processed_items + job.skipped_items + job.failed_items;
    const percentage = Math.round((processed / job.total_items) * 100);
    return (
      <div className="w-full mt-4">
        <div className="flex justify-between text-xs text-neutral-500 mb-1">
          <span>Progress ({percentage}%)</span>
          <span>{processed} / {job.total_items} items</span>
        </div>
        <div className="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-2">
          <div
            className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
            style={{ width: `${percentage}%` }}
          />
        </div>
        <div className="flex gap-4 mt-2 text-xs text-neutral-500">
          <span className="text-green-600">Processed: {job.processed_items}</span>
          <span className="text-yellow-600">Skipped: {job.skipped_items}</span>
          <span className="text-red-600">Failed: {job.failed_items}</span>
        </div>
      </div>
    );
  };

  const renderJobStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed': return <AlertCircle className="h-5 w-5 text-red-500" />;
      case 'running': return <Loader2 className="h-5 w-5 text-indigo-500 animate-spin" />;
      default: return <Clock className="h-5 w-5 text-neutral-500" />;
    }
  };

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <Card title="Batch Excel Job">
        <div className="space-y-4">
          <p className="text-sm text-neutral-600 dark:text-neutral-300">
            Upload an Excel file to process all items using the research agent.
            Results will be processed in the background.
          </p>

          <div
            className="flex items-center gap-3 p-3 border border-dashed border-neutral-300 dark:border-neutral-600 rounded-md bg-neutral-50 dark:bg-neutral-800 cursor-pointer hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="h-5 w-5 text-neutral-400 dark:text-neutral-500 shrink-0" />
            <span className="text-sm text-neutral-600 dark:text-neutral-300 truncate">
              {selectedFile ? selectedFile.name : 'Click to select an .xlsx file'}
            </span>
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>

          <div className="flex space-x-3">
            <button
              onClick={handleRunJob}
              disabled={!selectedFile || activeJob?.status === 'running' || activeJob?.status === 'queued'}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {(activeJob?.status === 'running' || activeJob?.status === 'queued') ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Play className="h-4 w-4 mr-2 fill-current" />
              )}
              {(activeJob?.status === 'running' || activeJob?.status === 'queued') ? 'Processing...' : 'Run Excel Job'}
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-md text-sm border border-red-200 dark:border-red-800">
            {error}
          </div>
        )}

        {activeJob && (
          <div className="mt-6 p-4 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-neutral-50 dark:bg-neutral-800">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                {renderJobStatusIcon(activeJob.status)}
                <h4 className="font-medium text-neutral-900 dark:text-neutral-100 capitalize">
                  Job {activeJob.status}
                </h4>
              </div>
              {activeJob.status === 'completed' && (
                <a
                  href={getJobExportUrl(activeJob.job_id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-indigo-700 bg-indigo-100 hover:bg-indigo-200 dark:bg-indigo-900 dark:text-indigo-200 dark:hover:bg-indigo-800"
                >
                  <Download className="h-3 w-3 mr-1" />
                  Download Export
                </a>
              )}
            </div>
            {activeJob.error_message && (
              <p className="text-sm text-red-600 mt-2">{activeJob.error_message}</p>
            )}
            {renderProgressBar(activeJob)}
          </div>
        )}
      </Card>

      {recentJobs.length > 0 && (
        <Card title="Recent Jobs">
          <div className="space-y-3">
            {recentJobs.map(job => (
              <div key={job.job_id} className="flex items-center justify-between p-3 border border-neutral-200 dark:border-neutral-700 rounded bg-white dark:bg-neutral-900">
                <div className="flex items-center gap-3">
                  {renderJobStatusIcon(job.status)}
                  <div>
                    <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                      {new Date(job.created_at).toLocaleString()}
                    </p>
                    <p className="text-xs text-neutral-500">
                      {job.processed_items + job.skipped_items + job.failed_items} / {job.total_items} items processed
                    </p>
                  </div>
                </div>
                {job.status === 'completed' && (
                  <a
                    href={getJobExportUrl(job.job_id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 text-neutral-500 hover:text-indigo-600 transition-colors"
                    title="Download"
                  >
                    <Download className="h-4 w-4" />
                  </a>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
