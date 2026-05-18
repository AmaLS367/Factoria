import { useRef, useState, useEffect } from "react";
import {
  runExcelJob,
  fetchJob,
  fetchJobs,
  getJobExportUrl,
  previewFile,
  cancelJob,
  retryJob,
} from "../api";
import type { Job, PreviewResult, SchemaTemplate } from "../types";
import { Card } from "./Card";
import { LayoutTemplate } from "lucide-react";
import {
  Play,
  Download,
  Loader2,
  Upload,
  AlertCircle,
  X,
  CheckCircle,
  Clock,
  XCircle,
  RefreshCw,
  ChevronDown,
} from "lucide-react";

type Step = "idle" | "previewing" | "configuring" | "running";

interface ExcelJobProps {
  initialTemplate?: SchemaTemplate;
  onTemplateClear?: () => void;
}

export function ExcelJob({ initialTemplate, onTemplateClear }: ExcelJobProps) {
  const [step, setStep] = useState<Step>("idle");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [selectedSheet, setSelectedSheet] = useState<string>("");
  const [selectedColumn, setSelectedColumn] = useState<string>("");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Template state
  const [appliedFields, setAppliedFields] = useState<string[] | undefined>();

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (initialTemplate) {
      setAppliedFields(initialTemplate.target_fields);

      if (preview && preview.columns.includes(initialTemplate.column_name)) {
        setSelectedColumn(initialTemplate.column_name);
      }
    }
  }, [initialTemplate, preview]);

  useEffect(() => {
    loadRecentJobs();
  }, []);

  useEffect(() => {
    let intervalId: number;
    if (
      activeJobId &&
      activeJob?.status !== "completed" &&
      activeJob?.status !== "failed" &&
      activeJob?.status !== "cancelled"
    ) {
      intervalId = window.setInterval(async () => {
        try {
          const job = await fetchJob(activeJobId);
          setActiveJob(job);
          if (
            job.status === "completed" ||
            job.status === "failed" ||
            job.status === "cancelled"
          ) {
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

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    if (!file) return;
    setSelectedFile(file);
    setError(null);
    setPreview(null);
    setStep("previewing");
    try {
      const result: PreviewResult = await previewFile(file);
      setPreview(result);
      setSelectedSheet(result.sheets[0] ?? "");
      setSelectedColumn(result.columns[0] ?? "");
      setStep("configuring");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStep("idle");
    }
  };

  const handleSheetChange = async (sheet: string) => {
    if (!selectedFile || !preview || preview.file_type === "csv") return;
    setSelectedSheet(sheet);
    try {
      const result: PreviewResult = await previewFile(selectedFile, sheet);
      setPreview(result);
      setSelectedColumn(result.columns[0] ?? "");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleRunJob = async () => {
    if (!selectedFile) {
      setError("Please select a file first.");
      return;
    }
    setError(null);
    setStep("running");
    try {
      const data = await runExcelJob(
        selectedFile,
        selectedSheet || undefined,
        selectedColumn || undefined,
      );
      setActiveJobId(data.job_id);
      const job = await fetchJob(data.job_id);
      setActiveJob(job);
      loadRecentJobs();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      setStep("configuring");
    }
  };

  const handleCancel = async () => {
    if (!activeJobId) return;
    try {
      await cancelJob(activeJobId);
      const job = await fetchJob(activeJobId);
      setActiveJob(job);
      loadRecentJobs();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleRetry = async () => {
    if (!activeJobId) return;
    try {
      const data = await retryJob(activeJobId);
      setActiveJobId(data.job_id);
      const job = await fetchJob(data.job_id);
      setActiveJob(job);
      setStep("running");
      loadRecentJobs();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleNewFile = () => {
    setStep("idle");
    setSelectedFile(null);
    setPreview(null);
    setSelectedSheet("");
    setSelectedColumn("");
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const renderProgressBar = (job: Job) => {
    if (!job.total_items) return null;
    const processed =
      job.processed_items + job.skipped_items + job.failed_items;
    const percentage = Math.round((processed / job.total_items) * 100);
    return (
      <div className="w-full mt-4">
        <div className="flex justify-between text-xs text-neutral-500 mb-1">
          <span>Progress ({percentage}%)</span>
          <span>
            {processed} / {job.total_items} items
          </span>
        </div>
        <div className="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-2">
          <div
            className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
            style={{ width: `${percentage}%` }}
          />
        </div>
        <div className="flex gap-4 mt-2 text-xs text-neutral-500">
          <span className="text-green-600">
            Processed: {job.processed_items}
          </span>
          <span className="text-yellow-600">Skipped: {job.skipped_items}</span>
          <span className="text-red-600">Failed: {job.failed_items}</span>
        </div>
      </div>
    );
  };

  const renderJobStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "failed":
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      case "cancelled":
        return <XCircle className="h-5 w-5 text-neutral-500" />;
      case "running":
        return <Loader2 className="h-5 w-5 text-indigo-500 animate-spin" />;
      default:
        return <Clock className="h-5 w-5 text-neutral-500" />;
    }
  };

  const isJobActive =
    activeJob?.status === "running" || activeJob?.status === "queued";
  const isJobTerminal =
    activeJob?.status === "completed" ||
    activeJob?.status === "failed" ||
    activeJob?.status === "cancelled";

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <Card title="Batch Excel / CSV Job">
        <div className="space-y-4">
          <p className="text-sm text-neutral-600 dark:text-neutral-300">
            Upload an Excel (.xlsx) or CSV file to process all items using the
            research agent.
          </p>

          {initialTemplate && appliedFields && (
            <div className="mb-6 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-md p-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <LayoutTemplate className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                <p className="text-sm text-indigo-900 dark:text-indigo-200">
                  Using template:{" "}
                  <span className="font-semibold">{initialTemplate.name}</span>{" "}
                  — {appliedFields.length} fields
                </p>
              </div>
              <button
                onClick={() => {
                  setAppliedFields(undefined);

                  if (onTemplateClear) onTemplateClear();
                }}
                className="p-1 text-indigo-500 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-200 transition-colors"
                title="Clear template"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Step 1 — File picker */}
          <div
            className="flex items-center gap-3 p-3 border border-dashed border-neutral-300 dark:border-neutral-600 rounded-md bg-neutral-50 dark:bg-neutral-800 cursor-pointer hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
            onClick={() => step !== "running" && fileInputRef.current?.click()}
          >
            {step === "previewing" ? (
              <Loader2 className="h-5 w-5 text-indigo-500 animate-spin shrink-0" />
            ) : (
              <Upload className="h-5 w-5 text-neutral-400 dark:text-neutral-500 shrink-0" />
            )}
            <span className="text-sm text-neutral-600 dark:text-neutral-300 truncate">
              {selectedFile
                ? selectedFile.name
                : "Click to select an .xlsx or .csv file"}
            </span>
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls,.csv"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>

          {/* Step 2 — Preview / Configure */}
          {(step === "configuring" || step === "running") && preview && (
            <div className="border border-neutral-200 dark:border-neutral-700 rounded-lg overflow-hidden">
              <div className="px-4 py-3 bg-neutral-50 dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
                <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
                  {preview.row_count} rows · {preview.columns.length} columns
                </span>
                {step === "configuring" && (
                  <button
                    onClick={handleNewFile}
                    className="text-xs text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
                  >
                    Change file
                  </button>
                )}
              </div>

              <div className="p-4 space-y-3">
                {/* Sheet selector (xlsx only) */}
                {preview.file_type === "xlsx" && preview.sheets.length > 1 && (
                  <div className="flex items-center gap-3">
                    <label className="text-xs font-medium text-neutral-600 dark:text-neutral-400 w-24 shrink-0">
                      Sheet
                    </label>
                    <div className="relative flex-1">
                      <select
                        value={selectedSheet}
                        onChange={(e) => handleSheetChange(e.target.value)}
                        disabled={step === "running"}
                        className="w-full appearance-none bg-white dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-600 rounded px-3 py-1.5 text-sm text-neutral-800 dark:text-neutral-200 pr-8 disabled:opacity-60"
                      >
                        {preview.sheets.map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                      <ChevronDown className="absolute right-2 top-2 h-4 w-4 text-neutral-400 pointer-events-none" />
                    </div>
                  </div>
                )}

                {/* Column selector */}
                <div className="flex items-center gap-3">
                  <label className="text-xs font-medium text-neutral-600 dark:text-neutral-400 w-24 shrink-0">
                    ID Column
                  </label>
                  <div className="relative flex-1">
                    <select
                      value={selectedColumn}
                      onChange={(e) => setSelectedColumn(e.target.value)}
                      disabled={step === "running"}
                      className="w-full appearance-none bg-white dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-600 rounded px-3 py-1.5 text-sm text-neutral-800 dark:text-neutral-200 pr-8 disabled:opacity-60"
                    >
                      {preview.columns.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-2 top-2 h-4 w-4 text-neutral-400 pointer-events-none" />
                  </div>
                </div>

                {/* Sample table */}
                {preview.sample_rows.length > 0 && (
                  <div className="overflow-x-auto rounded border border-neutral-200 dark:border-neutral-700 mt-1">
                    <table className="min-w-full text-xs">
                      <thead className="bg-neutral-100 dark:bg-neutral-800">
                        <tr>
                          {preview.columns.map((c) => (
                            <th
                              key={c}
                              className="px-3 py-1.5 text-left font-medium text-neutral-600 dark:text-neutral-400 whitespace-nowrap"
                            >
                              {c}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
                        {preview.sample_rows.map((row, i) => (
                          <tr key={i} className="bg-white dark:bg-neutral-900">
                            {preview.columns.map((c) => (
                              <td
                                key={c}
                                className="px-3 py-1.5 text-neutral-700 dark:text-neutral-300 whitespace-nowrap max-w-[160px] truncate"
                              >
                                {row[c] == null ? (
                                  <span className="text-neutral-400 italic">
                                    null
                                  </span>
                                ) : (
                                  String(row[c])
                                )}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Step 3 — Run / Cancel / Retry buttons */}
          <div className="flex gap-3 flex-wrap">
            {(step === "configuring" ||
              (step === "running" && isJobTerminal)) && (
              <button
                onClick={handleRunJob}
                disabled={!selectedFile || isJobActive}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Play className="h-4 w-4 mr-2 fill-current" />
                Run Job
              </button>
            )}

            {step === "running" && isJobActive && (
              <button
                onClick={handleCancel}
                className="inline-flex items-center px-4 py-2 border border-neutral-300 dark:border-neutral-600 text-sm font-medium rounded-md text-neutral-700 dark:text-neutral-300 bg-white dark:bg-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-700"
              >
                <XCircle className="h-4 w-4 mr-2" />
                Cancel
              </button>
            )}

            {step === "running" &&
              (activeJob?.status === "failed" ||
                activeJob?.status === "cancelled") && (
                <button
                  onClick={handleRetry}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700"
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Retry
                </button>
              )}

            {step === "idle" && (
              <button
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                <Upload className="h-4 w-4 mr-2" />
                Select File
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-md text-sm border border-red-200 dark:border-red-800">
            {error}
          </div>
        )}

        {activeJob && step === "running" && (
          <div className="mt-6 p-4 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-neutral-50 dark:bg-neutral-800">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                {renderJobStatusIcon(activeJob.status)}
                <h4 className="font-medium text-neutral-900 dark:text-neutral-100 capitalize">
                  Job {activeJob.status}
                </h4>
              </div>
              {activeJob.status === "completed" && (
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
              <p className="text-sm text-red-600 mt-2">
                {activeJob.error_message}
              </p>
            )}
            {renderProgressBar(activeJob)}
          </div>
        )}
      </Card>

      {recentJobs.length > 0 && (
        <Card title="Recent Jobs">
          <div className="space-y-3">
            {recentJobs.map((job) => (
              <div
                key={job.job_id}
                className="flex items-center justify-between p-3 border border-neutral-200 dark:border-neutral-700 rounded bg-white dark:bg-neutral-900"
              >
                <div className="flex items-center gap-3">
                  {renderJobStatusIcon(job.status)}
                  <div>
                    <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                      {new Date(job.created_at).toLocaleString()}
                    </p>
                    <p className="text-xs text-neutral-500">
                      {job.processed_items +
                        job.skipped_items +
                        job.failed_items}{" "}
                      / {job.total_items} items · {job.status}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  {(job.status === "failed" || job.status === "cancelled") && (
                    <button
                      onClick={async () => {
                        try {
                          const data = await retryJob(job.job_id);
                          setActiveJobId(data.job_id);
                          const newJob = await fetchJob(data.job_id);
                          setActiveJob(newJob);
                          setStep("running");
                          loadRecentJobs();
                        } catch (err) {
                          setError(
                            err instanceof Error ? err.message : String(err),
                          );
                        }
                      }}
                      className="p-2 text-neutral-500 hover:text-indigo-600 transition-colors"
                      title="Retry"
                    >
                      <RefreshCw className="h-4 w-4" />
                    </button>
                  )}
                  {job.status === "completed" && (
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
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
